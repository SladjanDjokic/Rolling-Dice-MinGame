import os
import datetime
from urllib.parse import urlparse, urljoin
# from dateutil.tz import tzlocal
import secrets
import logging
import boto3
from botocore.exceptions import NoCredentialsError  # , ClientError

from app.util.db import source
from app.config import settings
from app.util.filestorage import safe_open, s3fy_filekey
from app.exceptions.file_sharing import FileStorageUploadError

logger = logging.getLogger(__name__)


class FileStorageDA(object):
    source = source
    refile_path = os.path.dirname(os.path.abspath(__file__))

    @classmethod
    def store_file_to_storage(cls, file):
        '''
        We are saving nested "some_folder/some-file.ext" and unnested "some-file.ext" files.
        Since we do this file-by-file - we ignore the file path during disk save, i.e. "some_folder/some-file.ext" => "some-file.ext"
        But we keep that structure in aws
        '''
        file_id = str(int(datetime.datetime.now().timestamp() * 1000))
        # file_name = file_id + "." + file.filename.split(".")[-1]
        (dirname, true_filename) = os.path.split(file.filename)
        file_name = file_id + "-" + true_filename
        local_path = f"{cls.refile_path}/{file_name}"
        storage_key = f"{dirname}/{file_name}"

        logger.debug("Filename: {}".format(file_name))
        logger.debug("Filepath: {}".format(local_path))

        # Use utility to create folder if it doesn't exist'
        temp_file_path = local_path + "~"
        with safe_open(temp_file_path, "wb") as f:
            f.write(file.file.read())
        # file has been fully saved to disk move it into place
        os.rename(temp_file_path, local_path)

        storage_engine = "S3"
        bucket = settings.get("storage.s3.bucket")
        s3_location = settings.get("storage.s3.file_location_host")

        uploaded = cls.upload_to_aws(local_path, bucket, storage_key)

        if not uploaded:
            raise FileStorageUploadError

        # Handle keyed filenames here
        s3_file_location = urljoin(s3_location, storage_key)

        file_id = cls.create_file_storage_entry(
            s3_file_location, storage_engine, "available")

        os.remove(local_path)

        return file_id

    @classmethod
    def upload_to_aws(cls, local_file, bucket, s3_file):
        s3 = cls.aws_s3_client()

        try:
            s3.upload_file(local_file, bucket, s3_file)
            print("Upload Successful")
            return True
        except FileNotFoundError:
            print("The file was not found")
            return False
        except NoCredentialsError:
            print("Credentials not available")
            return False

    @classmethod
    def create_file_storage_entry(cls, file_path, storage_engine, status,
                                  commit=True):
        # TODO: CHANGE THIS LATER TO ENCRYPT IN APP
        query = ("""
            INSERT INTO file_storage_engine
            (storage_engine_id, storage_engine, status)
            VALUES (%s, %s, %s)
            RETURNING id
        """)

        params = (file_path, storage_engine, status, )
        cls.source.execute(query, params)

        logger.debug(
            f"[create_file_storage_entry] COMMIT TRANSACTION: {commit}")
        if commit:
            cls.source.commit()

        id = cls.source.get_last_row_id()
        logger.debug(
            f"[create_file_storage_entry] TRANSACTION IDENTIFIER: {id}")

        return id

    @classmethod
    def create_member_file_entry(cls, file_id, file_name, member_id, status,
                                 file_size_bytes, category=None, iv=None, commit=True):
        # TODO: CHANGE THIS LATER TO ENCRYPT IN APP
        query = ("""
            INSERT INTO member_file
            (file_id, file_name, member_id, status,
             categories, file_ivalue, file_size_bytes)
            VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id
        """)
        params = (file_id, file_name, member_id,
                  status, category, iv, file_size_bytes)
        cls.source.execute(query, params)

        logger.debug(
            f"[create_member_file_entry] COMMIT TRANSACTION: {commit}")
        if commit:
            cls.source.commit()

        id = cls.source.get_last_row_id()
        logger.debug(
            f"[create_member_file_entry] TRANSACTION IDENTIFIER: {id}")

        return id

    @classmethod
    def get_member_file(cls, member, file_id):
        query = ("""
            SELECT
                member_file.file_id as file_id,
                member_file.file_name as file_name,
                member_file.categories as categories,
                member_file.file_size_bytes as file_size_bytes,
                member_file.file_ivalue as file_ivalue,
                file_storage_engine.storage_engine_id as file_link,
                file_storage_engine.storage_engine as storage_engine,
                file_storage_engine.status as status,
                file_storage_engine.create_date as created_date,
                file_storage_engine.update_date as updated_date,
                CASE WHEN
                    (member_file.file_ivalue IS NULL OR member_file.file_ivalue = '')
                    THEN 'unencrypted'
                    ELSE 'encrypted'
                END as file_status
            FROM member_file
            LEFT JOIN file_storage_engine ON file_storage_engine.id = member_file.file_id
            WHERE member_file.member_id = %s AND file_storage_engine.id = %s
        """)
        params = (member["member_id"], file_id, )
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                file_id,
                file_name,
                categories,
                file_size_bytes,
                file_ivalue,
                file_link,
                storage_engine,
                status,
                created_date,
                updated_date,
                file_status,
            ) in cls.source.cursor:
                member_file = {
                    "file_id": file_id,
                    "file_name": file_name,
                    "categories": categories,
                    "file_size_bytes": file_size_bytes,
                    "file_ivalue": file_ivalue,
                    "file_url": file_link,
                    "storage_engine": storage_engine,
                    "status": status,
                    "member": member["first_name"],
                    "created_date": created_date,
                    "updated_date": updated_date,
                    "file_status": file_status
                }
                return member_file
        return None

    @classmethod
    def get_member_files(cls, member):
        query = ("""
                SELECT
                    member_file.file_id as file_id,
                    member_file.file_name as file_name,
                    member_file.categories as categories,
                    member_file.file_size_bytes as file_size_bytes,
                    member_file.file_ivalue as file_ivalue,
                    file_storage_engine.storage_engine_id as file_link,
                    file_storage_engine.storage_engine as storage_engine,
                    file_storage_engine.status as status,
                    file_storage_engine.create_date as created_date,
                    file_storage_engine.update_date as updated_date,
                    CASE WHEN
                        (member_file.file_ivalue IS NULL OR member_file.file_ivalue = '')
                        THEN 'unencrypted'
                        ELSE 'encrypted'
                    END as file_status
                FROM member_file
                LEFT JOIN file_storage_engine ON file_storage_engine.id = member_file.file_id
                WHERE member_file.member_id = %s AND file_storage_engine.status = %s
                ORDER BY file_storage_engine.create_date DESC
            """)
        params = (member["member_id"], "available", )
        cls.source.execute(query, params)
        if cls.source.has_results():
            entry = list()
            for entry_da in cls.source.cursor.fetchall():
                entry_element = {
                    "file_id": entry_da[0],
                    "file_name": entry_da[1],
                    "categories": entry_da[2],
                    "file_size_bytes": entry_da[3],
                    "file_ivalue": entry_da[4],
                    "file_link": entry_da[5],
                    "storage_engine": entry_da[6],
                    "status": entry_da[7],
                    "created_date": entry_da[8],
                    "updated_date": entry_da[9],
                    "file_status": entry_da[10],
                    "member": member["first_name"]
                }
                entry.append(entry_element)
            return entry
        return None

    @classmethod
    def get_file_detail(cls, member, file_id):
        query = ("""
            SELECT
                file_storage_engine.storage_engine_id as file_location,
                file_storage_engine.storage_engine as storage_engine,
                file_storage_engine.status as status,
                file_storage_engine.create_date as created_date,
                file_storage_engine.update_date as updated_date,
                member_file.file_name as file_name,
                member_file.file_size_bytes as file_size_bytes,
                member_file.file_ivalue as file_ivalue,
                member_file.categories as categories
            FROM file_storage_engine
            LEFT JOIN member_file ON file_storage_engine.id = member_file.file_id
            WHERE file_storage_engine.id = %s
            ORDER BY file_storage_engine.create_date DESC
        """)
        params = (file_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                file_location,
                storage_engine,
                status,
                created_date,
                updated_date,
                file_name,
                file_size_bytes,
                file_ivalue,
                categories
            ) in cls.source.cursor:
                file_detail = {
                    "file_id": file_id,
                    "file_location": file_location,
                    "storage_engine": storage_engine,
                    "status": status,
                    "created_date": created_date,
                    "updated_date": updated_date,
                    "file_name": file_name,
                    "file_size_bytes": file_size_bytes,
                    "file_ivalue": file_ivalue,
                    "categories": categories,
                    "member_first_name": member.get("first_name"),
                    "member_last_name": member.get("last_name"),
                    "member_email": member.get("email"),
                    "member_username": member.get("username"),
                }
                return file_detail
        return None

    @classmethod
    def delete_file(cls, file_id, commit=True):
        # delete object from aws
        # query = ("""
        #     SELECT storage_engine_id FROM file_storage_engine WHERE id = %s
        # """)
        # params = (file_id, )
        # cls.source.execute(query, params)
        # if cls.source.has_results():
        #     file_url = None
        #     for (storage_engine_id, ) in cls.source.cursor:
        #         file_url = storage_engine_id
        #     if file_url:
        #         item_key = file_url.replace(f"{settings.get("storage.s3.file_location_host")}/", "")
        #         bucket_name = settings.get("bucket")
        #         delete = cls.remove_aws_object(bucket_name, item_key)

        logger.info(f"Deleting {file_id}")
        query = ("""
            UPDATE file_storage_engine
            SET status = %s, update_date = CURRENT_TIMESTAMP
            WHERE id = %s AND status = %s
        """)

        params = ("deleted", file_id, "available", )
        cls.source.execute(query, params)
        try:
            if commit:
                cls.source.commit()
                return True
        finally:
            return False

    @classmethod
    def store_file_to_static(cls, file_id):
        query = ("""
                    SELECT storage_engine_id as file_url, member_file.file_ivalue as file_ivalue
                    FROM file_storage_engine
                        LEFT OUTER JOIN member_file ON (file_storage_engine.id = member_file.file_id)
                    WHERE file_storage_engine.id = %s
                """)
        params = (file_id, )
        cls.source.execute(query, params)
        bucket_name = settings.get("storage.s3.bucket")
        if cls.source.has_results():
            try:
                file = cls.source.cursor.fetchone()
                file_url = file[0]
                file_ivalue = file[1]
                if not file_ivalue:
                    file_ivalue = ""

                #  url is "https://file-testing.s3.us-east-2.amazonaws.com/folder1/foldder2/file.ext"
                item_key = urlparse(file_url).path

                download = cls.download_aws_object(
                    bucket_name, item_key, file_ivalue)
                if download:
                    return f"{item_key}{file_ivalue}"
            except Exception as e:
                print(e)

    @classmethod
    def rename_file(cls, member, file_id, new_file_name):
        """
            We don't touch the actual file nor its path in storage (for performance reasons), we do only change the displayed filename in member_files table .
        """
        try:
            query = ("""
                        UPDATE member_file
                        SET file_name = %s
                        WHERE file_id = %s
                    """)
            params = (new_file_name, file_id,)
            cls.source.execute(query, params)
            if cls.source.has_results():
                cls.source.commit()
                return True
        except Exception as e:
            logger.debug(e.message)

    @classmethod
    def remove_aws_object(cls, bucket_name, item_key):
        """ Provide bucket name and item key, remove from S3
        """
        s3 = cls.aws_s3_client()
        delete = s3.delete_object(Bucket=bucket_name, Key=item_key)
        return True

    @classmethod
    def copy_aws_object(cls, bucket_name, old_key, new_key):
        """ Will create a copy replacing old_key with new_key
        """
        logging.debug(
            f"Will try to access old key {old_key} and change it to {new_key}")
        try:
            s3 = cls.aws_s3_client()
            s3.copy(CopySource={'Bucket': bucket_name,
                                'Key': old_key}, Bucket=bucket_name, Key=new_key)
            return True
        except Exception as e:
            raise

    @classmethod
    def download_aws_object(cls, bucket_name, item_key, file_ivalue=None):
        """ Provide bucket name and item key, remove from S3
        """
        s3 = cls.aws_s3_client()
        static_path = os.path.join(os.getcwd(), "static")
        if not os.path.exists(static_path):
            os.mkdir(static_path)
        '''
        If file is nested within a folder on s3, its key will look like "folder/another/121212-filename.ext"
        We want to address that when we download, but can't keep that folder structure in static i.e.
        the path to file will be "static/121212-filename.ext"
        '''
        (dirname, filename) = os.path.split(item_key)
        file_path = f"{static_path}/{filename}"
        if file_ivalue:
            file_path = f"{static_path}/{filename}{file_ivalue}"
        key = s3fy_filekey(item_key)
        # logger.debug(
        # f"Obi wan, we will download file from this bucket {bucket_name}, and this item key {key}")
        s3.download_file(bucket_name, key, file_path)
        return True

    @staticmethod
    def aws_s3_client():
        return boto3.client(
            "s3",
            region_name=settings.get("services.aws.region_name"),
            aws_access_key_id=settings.get("services.aws.access_key_id"),
            aws_secret_access_key=settings.get(
                "services.aws.secret_access_key")
        )


class ShareFileDA(object):

    source = source

    @classmethod
    def sharing_file(cls, file_id, member_id, group_id, shared_member_id, commit=True):
        if group_id:
            filter_key = 'group_id'
            filter_value = group_id
        else:
            filter_key = 'shared_member_id'
            filter_value = shared_member_id
        exist = cls.check_shared_exist(
            file_id, member_id, filter_key, filter_value)
        if exist:
            return False
        else:
            query = ("""
                            INSERT INTO shared_file
                            (file_id, shared_unique_key, member_id, {})
                            VALUES (%s, %s, %s, %s)
                        """).format(filter_key)
            shared_unique_key = secrets.token_hex(nbytes=16)
            params = (file_id, shared_unique_key, member_id, filter_value)
            cls.source.execute(query, params)
            if commit:
                cls.source.commit()
            return True

    @classmethod
    def check_shared_exist(cls, file_id, member_id, key, value):
        query = ("""
            SELECT *
            FROM shared_file
            WHERE file_id = %s AND member_id = %s AND {} = %s
        """).format(key)
        params = (file_id, member_id, value)
        cls.source.execute(query, params)
        if cls.source.has_results():
            return True

    @classmethod
    def get_shared_files(cls, member):
        shared_files = list()
        # Shared BY me
        query = ("""
            SELECT
                shared_file.file_id as file_id,
                shared_file.shared_unique_key as shared_key,
                shared_file.member_id as sharer_member_id,
                member_file.file_name as file_name,
                member.first_name as consumer_first_name,
                member.last_name as consumer_last_name,
                CASE WHEN
                    (member_file.file_ivalue IS NULL OR member_file.file_ivalue = '')
                    THEN 'unencrypted'
                    ELSE 'encrypted'
                END as file_status,
                member.email as consumer_email,
                shared_file.create_date as shared_date,
                shared_file.shared_member_id as consumer_member_id,
                member_file.file_size_bytes as file_size_bytes
            FROM shared_file
            LEFT JOIN file_storage_engine ON file_storage_engine.id = shared_file.file_id
            LEFT JOIN member_file ON member_file.file_id = shared_file.file_id
            LEFT JOIN member ON member.id = shared_file.shared_member_id
            WHERE shared_file.member_id = %s AND file_storage_engine.status = %s AND shared_member_id IS NOT NULL
            ORDER BY shared_file.create_date DESC
        """)
        params = (member.get("member_id"), "available", )
        cls.source.execute(query, params)
        if cls.source.has_results():
            for file in cls.source.cursor.fetchall():
                elem = {
                    "file_id": file[0],
                    "shared_key": file[1],
                    "sharer_member_id": file[2],
                    "sharer_first_name": member.get("first_name"),
                    "sharer_last_name": member.get("last_name"),
                    "file_name": file[3],
                    "consumer_first_name": file[4],
                    "consumer_last_name": file[5],
                    "file_status": file[6],
                    "consumer_email": file[7],
                    "shared_date": file[8],
                    "consumer_member_id": file[9],
                    "file_size_bytes": file[10]
                }
                shared_files.append(elem)
        # Shared WITH me
        query = ("""
            SELECT
                shared_file.file_id as file_id,
                shared_file.shared_unique_key as shared_key,
                shared_file.member_id as sharer_member_id,
                member_file.file_name as file_name,
                member.first_name as consumer_first_name,
                member.last_name as consumer_last_name,
                CASE WHEN
                    (member_file.file_ivalue IS NULL OR member_file.file_ivalue = '')
                    THEN 'unencrypted'
                    ELSE 'encrypted'
                END as file_status,
                member.email as shared_member_email,
                shared_file.create_date as shared_date,
                shared_file.shared_member_id as consumer_member_id,
                member_file.file_size_bytes as file_size_bytes
            FROM shared_file
            LEFT JOIN file_storage_engine ON file_storage_engine.id = shared_file.file_id
            LEFT JOIN member_file ON member_file.file_id = shared_file.file_id
            LEFT JOIN member ON member.id = shared_file.member_id
            WHERE shared_file.shared_member_id = %s AND file_storage_engine.status = %s
            ORDER BY shared_file.create_date DESC
        """)
        params = (member.get("member_id"), "available",)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for file in cls.source.cursor.fetchall():
                elem = {
                    "file_id": file[0],
                    "shared_key": file[1],
                    "sharer_member_id": file[2],
                    "sharer_first_name": file[4],
                    "sharer_first_name": file[5],
                    "file_name": file[3],
                    "consumer_first_name": member.get("first_name"),
                    "consumer_last_name": member.get("last_name"),
                    "file_status": file[6],
                    "consumer_email": member.get("email"),
                    "shared_date": file[8],
                    "consumer_member_id": member.get("member_id"),
                    "file_size_bytes": file[10]
                }
                shared_files.append(elem)
        return shared_files

    @classmethod
    def get_group_files(cls, member):
        shared_files = list()
        query = ("""
            SELECT
                shared_file.file_id as file_id,
                shared_file.shared_unique_key as shared_key, 
                member_file.file_name as file_name,
                member_file.file_size_bytes as file_size_bytes,
                CASE WHEN
                    (member_file.file_ivalue IS NULL OR member_file.file_ivalue = '')
                    THEN 'unencrypted'
                    ELSE 'encrypted'
                END as file_status,
                member_group.group_name as group_name,
                member_group.id as group_id,
                shared_file.update_date as updated_date,
                member.last_name as last_name,
                member.first_name as first_name
            FROM shared_file
            LEFT JOIN file_storage_engine ON file_storage_engine.id = shared_file.file_id
            LEFT JOIN member_file ON member_file.file_id = shared_file.file_id
            LEFT JOIN member_group ON member_group.id = shared_file.group_id
            LEFT JOIN member ON member.id = shared_file.member_id
            WHERE shared_file.member_id = %s AND file_storage_engine.status = %s AND group_id IS NOT NULL
            ORDER BY shared_file.create_date DESC
        """)
        params = (member.get("member_id"), "available",)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for file in cls.source.cursor.fetchall():
                elem = {
                    "file_id": file[0],
                    "shared_key": file[1],
                    "file_name": file[2],
                    "file_size_bytes": file[3],
                    "file_status": file[4],
                    "group_name": file[5],
                    "group_id": file[6],
                    "updated_date": file[7],
                    "last_name": file[8],
                    "first_name": file[9],
                }
                shared_files.append(elem)

        query = ("""
            SELECT group_id FROM member_group_membership WHERE member_id = %s
        """)
        params = (member.get('member_id'),)
        cls.source.execute(query, params)
        include_member_group_id_list = list()
        if cls.source.has_results():
            for group_id in cls.source.cursor.fetchall():
                include_member_group_id_list.append(str(group_id[0]))
        include_member_group_id_list = ', '.join(include_member_group_id_list)
        print(include_member_group_id_list)
        query = ("""
            SELECT
                shared_file.file_id as file_id,
                shared_file.shared_unique_key as shared_key,
                member_file.file_name as file_name,
                member_file.file_size_bytes as file_size_bytes,
                  CASE WHEN
                    (member_file.file_ivalue IS NULL OR member_file.file_ivalue = '')
                    THEN 'unencrypted'
                    ELSE 'encrypted'
                END as file_status,
                member_group.group_name as group_name,
                member_group.id as group_id,
                shared_file.update_date as updated_date,
                member.last_name as last_name,
                member.first_name as first_name
            FROM shared_file
            LEFT JOIN file_storage_engine ON file_storage_engine.id = shared_file.file_id
            LEFT JOIN member_file ON member_file.file_id = shared_file.file_id
            LEFT JOIN member_group ON member_group.id = shared_file.group_id
            LEFT JOIN member ON member.id = shared_file.member_id
            WHERE shared_file.group_id in (""" + include_member_group_id_list + """) AND file_storage_engine.status = %s
            ORDER BY shared_file.create_date DESC
        """)
        params = ("available", )
        cls.source.execute(query, params)
        if cls.source.has_results():
            for file in cls.source.cursor.fetchall():
                elem = {
                    "file_id": file[0],
                    "shared_key": file[1],
                    "file_name": file[2],
                    "file_size_bytes": file[3],
                    "file_status": file[4],
                    "group_name": file[5],
                    "group_id": file[6],
                    "updated_date": file[7],
                    "last_name": file[8],
                    "first_name": file[9],
                }
                shared_files.append(elem)
        return shared_files

    @classmethod
    def get_shared_file_detail(cls, member, shared_key):
        query = ("""
            SELECT member_id, shared_member_id, group_id
            FROM shared_file
            WHERE shared_unique_key = %s
        """)
        params = (shared_key,)
        cls.source.execute(query, params)
        filter_params = {}
        if cls.source.has_results():
            for (member_id, shared_member_id, group_id, ) in cls.source.cursor:
                filter_params["member_id"] = member_id
                filter_params["shared_member_id"] = shared_member_id
                filter_params["group_id"] = group_id

        if filter_params.get('shared_member_id'):
            if member["member_id"] == filter_params["member_id"]:
                query = ("""
                    SELECT
                        shared_file.file_id as file_id,
                        shared_file.group_id as group_name,
                        file_storage_engine.storage_engine_id as file_location,
                        member_file.file_name as file_name,
                        member.first_name as shared_member_first_name,
                        member.last_name as shared_member_last_name,
                        member.email as shared_member_email,
                        member.username as shared_member_username,
                        shared_file.create_date as shared_date,
                        shared_file.update_date as updated_date
                    FROM shared_file
                    LEFT JOIN file_storage_engine ON file_storage_engine.id = shared_file.file_id
                    LEFT JOIN member_file ON member_file.file_id = shared_file.file_id
                    LEFT JOIN member ON member.id = shared_file.shared_member_id
                    WHERE shared_file.shared_unique_key = %s
                    ORDER BY shared_file.create_date DESC
                """)
            else:
                query = ("""
                    SELECT
                        shared_file.file_id as file_id,
                        shared_file.group_id as group_name,
                        file_storage_engine.storage_engine_id as file_location,
                        member_file.file_name as file_name,
                        member.first_name as shared_member_first_name,
                        member.last_name as shared_member_last_name,
                        member.email as shared_member_email,
                        member.username as shared_member_username,
                        shared_file.create_date as shared_date,
                        shared_file.update_date as updated_date
                    FROM shared_file
                    LEFT JOIN file_storage_engine ON file_storage_engine.id = shared_file.file_id
                    LEFT JOIN member_file ON member_file.file_id = shared_file.file_id
                    LEFT JOIN member ON member.id = shared_file.member_id
                    WHERE shared_file.shared_unique_key = %s
                    ORDER BY shared_file.create_date DESC
                """)
        elif filter_params.get('group_id'):
            query = ("""
                SELECT
                    shared_file.file_id as file_id,
                    member_group.group_name as group_name,
                    file_storage_engine.storage_engine_id as file_location,
                    member_file.file_name as file_name,
                    member.first_name as shared_member_first_name,
                    member.last_name as shared_member_last_name,
                    member.email as shared_member_email,
                    member.username as shared_member_username,
                    shared_file.create_date as shared_date,
                    shared_file.update_date as updated_date
                FROM shared_file
                LEFT JOIN file_storage_engine ON file_storage_engine.id = shared_file.file_id
                LEFT JOIN member_file ON member_file.file_id = shared_file.file_id
                LEFT JOIN member_group ON shared_file.group_id = member_group.id
                LEFT JOIN member ON member.id = member_group.group_leader_id
                WHERE shared_file.shared_unique_key = %s
                ORDER BY shared_file.create_date DESC
            """)
        params = (shared_key,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                file_id,
                group_name,
                file_location,
                file_name,
                shared_member_first_name,
                shared_member_last_name,
                shared_member_email,
                shared_member_username,
                shared_date,
                updated_date
            ) in cls.source.cursor:
                shared_file_detail = {
                    "shared_key": shared_key,
                    "file_id": file_id,
                    "file_location": file_location,
                    "file_name": file_name,
                    "member_first_name": member.get("first_name"),
                    "member_last_name": member.get("last_name"),
                    "member_email": member.get("email"),
                    "member_username": member.get("username"),
                    "shared_member_first_name": shared_member_first_name,
                    "shared_member_last_name": shared_member_last_name,
                    "shared_member_email": shared_member_email,
                    "shared_member_username": shared_member_username,
                    "shared_date": datetime.datetime.strftime(shared_date, "%Y-%m-%d %H:%M:%S"),
                    "updated_date": datetime.datetime.strftime(updated_date, "%Y-%m-%d %H:%M:%S"),
                }
                if type(group_name) is str:
                    shared_file_detail["group_name"] = group_name
                return shared_file_detail
        return None

    @classmethod
    def remove_sharing(cls, shared_key, commit=True):
        query = ("""
            DELETE FROM shared_file WHERE shared_unique_key = %s
        """)

        params = (shared_key,)
        res = cls.source.execute(query, params)
        if commit:
            cls.source.commit()

        return shared_key

    @classmethod
    def get_shared_file_id(cls, shared_key):
        query = ("""
            SELECT file_id
            FROM shared_file
            WHERE shared_unique_key = %s
        """)
        params = (shared_key,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            shared_file = cls.source.cursor.fetchone()
            return shared_file[0]
