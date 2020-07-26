import os
import datetime
from dateutil.tz import tzlocal
import secrets
import logging
import boto3
from botocore.exceptions import NoCredentialsError, ClientError

from app.util.db import source
from app.config import settings

logger = logging.getLogger(__name__)


class FileStorageDA(object):
    source = source
    refile_path = os.path.dirname(os.path.abspath(__file__))

    @classmethod
    def store_file_to_storage(cls, file):
        file_id = str(int(datetime.datetime.now().timestamp() * 1000))
        # file_name = file_id + "." + file.filename.split(".")[-1]
        file_name = file_id + "-" + file.filename
        file_path = cls.refile_path + "/" + file_name

        logger.debug("Filename: {}".format(file_name))
        logger.debug("Filepath: {}".format(file_path))

        temp_file_path = file_path + "~"
        with open(temp_file_path, "wb") as f:
            f.write(file.file.read())
        # file has been fully saved to disk move it into place
        os.rename(temp_file_path, file_path)

        storage_engine = "S3"
        bucket = settings.get("storage.s3.bucket")
        s3_location = settings.get("storage.s3.file_location_host")

        uploaded = cls.upload_to_aws(file_path, bucket, file_name)
        if uploaded:
            s3_location = f"{s3_location}/{file_name}"
            file_id = cls.create_file_storage_entry(
                s3_location, storage_engine, "available")
            os.remove(file_path)
            return file_id
        else:
            return None

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
    def create_file_storage_entry(cls, file_path, storage_engine, status, commit=True):
        # TODO: CHANGE THIS LATER TO ENCRYPT IN APP
        query = ("""
            INSERT INTO file_storage_engine
            (storage_engine_id, storage_engine, status)
            VALUES (%s, %s, %s)
        """)
        params = (file_path, storage_engine, status, )
        cls.source.execute(query, params)

        if commit:
            cls.source.commit()

        # get id just committed
        query = ("""
            SELECT currval(pg_get_serial_sequence('file_storage_engine','id'))
        """)
        cls.source.execute(query, ("", ))
        file_id = cls.source.cursor.fetchall()
        return file_id[0][0]

    @classmethod
    def create_member_file_entry(cls, file_id, file_name, member_id, status, iv=None, commit=True):
        # TODO: CHANGE THIS LATER TO ENCRYPT IN APP
        query = ("""
            INSERT INTO member_file
            (file_id, file_name, member_id, status, categories, file_ivalue)
            VALUES (%s, %s, %s, %s, '', %s)
        """)
        params = (file_id, file_name, member_id, status,iv)
        cls.source.execute(query, params)

        if commit:
            cls.source.commit()

        return True

    @classmethod
    def get_member_file(cls, member, file_id):
        query = ("""
            SELECT
                member_file.file_id as file_id,
                member_file.file_name as file_name,
                member_file.categories as categories,
                file_storage_engine.storage_engine_id as file_link,
                file_storage_engine.storage_engine as storage_engine,
                file_storage_engine.status as status,
                file_storage_engine.create_date as create_date,
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
                file_link,
                storage_engine,
                status,
                create_date,
                file_status,
            ) in cls.source.cursor:
                member_file = {
                    "file_id": file_id,
                    "file_name": file_name,
                    "categories": categories,
                    "file_url": file_link,
                    "storage_engine": storage_engine,
                    "status": status,
                    "member": member["first_name"],
                    "create_date": datetime.datetime.strftime(create_date, "%Y-%m-%d %H:%M:%S"),
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
                    CASE WHEN 
                        (member_file.file_ivalue IS NULL OR member_file.file_ivalue = '')
                        THEN 'unencrypted'
                        ELSE 'encrypted'
                    END as file_status,
                    file_storage_engine.storage_engine as storage_engine,
                    file_storage_engine.status as status,
                    file_storage_engine.create_date as create_date
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
                    "file_status": entry_da[3],
                    "storage_engine": entry_da[4],
                    "status": entry_da[5],
                    "member": member["first_name"],
                    "create_date": datetime.datetime.strftime(entry_da[6], "%Y-%m-%d %H:%M:%S")
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
                categories,
            ) in cls.source.cursor:
                file_detail = {
                    "file_id": file_id,
                    "file_location": file_location,
                    "storage_engine": storage_engine,
                    "status": status,
                    "created_date": datetime.datetime.strftime(created_date, "%Y-%m-%d %H:%M:%S"),
                    "updated_date": datetime.datetime.strftime(updated_date, "%Y-%m-%d %H:%M:%S"),
                    "file_name": file_name,
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

        current_time_with_timezone = datetime.datetime.now(tzlocal()).isoformat().replace("T", " ")
        query = ("""
            UPDATE file_storage_engine
            SET status = %s, update_date = %s
            WHERE id = %s AND status = %s
        """)

        params = ("deleted", current_time_with_timezone, file_id, "available", )
        res = cls.source.execute(query, params)
        try:
            if commit:
                cls.source.commit()
                return True
        except Exception as e:
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
                item_key = file_url.split("/")[3]
                download = cls.download_aws_object(
                    bucket_name, item_key, file_ivalue)
                if download:
                    return f"{item_key}{file_ivalue}"
            except Exception as e:
                print(e)

    @classmethod
    def remove_aws_object(cls, bucket_name, item_key):
        """ Provide bucket name and item key, remove from S3
        """
        s3 = cls.aws_s3_client()
        delete = s3.delete_object(Bucket=bucket_name, Key=item_key)
        return True

    @classmethod
    def download_aws_object(cls, bucket_name, item_key, file_ivalue=None):
        """ Provide bucket name and item key, remove from S3
        """
        s3 = cls.aws_s3_client()
        static_path = os.path.join(os.getcwd(), "static")
        if not os.path.exists(static_path):
            os.mkdir(static_path)

        file_path = f"{static_path}/{item_key}"
        if file_ivalue:
            file_path = f"{static_path}/{item_key}{file_ivalue}"
        s3.download_file(bucket_name, item_key, item_key)
        os.replace(item_key, file_path)
        return True

    @staticmethod
    def aws_s3_client():
        return boto3.client(
            "s3",
            region_name=settings.get("services.aws.region_name"),
            aws_access_key_id=settings.get("services.aws.access_key_id"),
            aws_secret_access_key=settings.get("services.aws.secret_access_key")
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
        exist = cls.check_shared_exist(file_id, member_id, filter_key, filter_value)
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
        query = ("""
            SELECT
                shared_file.file_id as file_id,
                shared_file.shared_unique_key as shared_key,
                member_file.file_name as file_name,
                member.first_name as shared_member_first_name,
                member.last_name as shared_member_last_name,
                CASE WHEN 
                    (member_file.file_ivalue IS NULL OR member_file.file_ivalue = '') 
                    THEN 'unencrypted'
                    ELSE 'encrypted'
                END as file_status,
                member.email as shared_member_email,
                shared_file.create_date as shared_date
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
                    "file_name": file[2],
                    "member": member.get("first_name"),
                    "shared_member": file[3],
                    "shared_member_email": file[6],
                    "shared_date": file[7]
                }
                shared_files.append(elem)
        query = ("""
            SELECT
                shared_file.file_id as file_id,
                shared_file.shared_unique_key as shared_key,
                
                member_file.file_name as file_name,
                member.first_name as shared_member_first_name,
                member.last_name as shared_member_last_name,
                member.email as shared_member_email,
                shared_file.create_date as shared_date
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
                    "file_name": file[2],
                    "member": member.get("first_name"),
                    "shared_member": file[3],
                    "shared_member_email": file[5],
                    "shared_date": file[6]
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
                member_group.group_name as group_name,
                member_group.id as group_id,
                shared_file.create_date as shared_date
            FROM shared_file
            LEFT JOIN file_storage_engine ON file_storage_engine.id = shared_file.file_id
            LEFT JOIN member_file ON member_file.file_id = shared_file.file_id
            LEFT JOIN member_group ON member_group.id = shared_file.group_id
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
                    "group_name": file[3],
                    "group_id": file[4],
                    "shared_date": file[5]
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
                member_group.group_name as group_name,
                member_group.id as group_id,
                shared_file.create_date as shared_date
            FROM shared_file
            LEFT JOIN file_storage_engine ON file_storage_engine.id = shared_file.file_id
            LEFT JOIN member_file ON member_file.file_id = shared_file.file_id
            LEFT JOIN member_group ON member_group.id = shared_file.group_id
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
                    "group_name": file[3],
                    "group_id": file[4],
                    "shared_date": file[5]
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
