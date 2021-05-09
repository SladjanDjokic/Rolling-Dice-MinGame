import os
import uuid
import datetime
import mimetypes
from operator import itemgetter

from urllib.parse import urlparse, urljoin
# from dateutil.tz import tzlocal
import secrets
import logging
import boto3
from botocore.exceptions import NoCredentialsError, ClientError  # , ClientError

from app.util.db import source
from app.util.filestorage import amerize_url
from app.config import settings
from app.util.filestorage import safe_open, s3fy_filekey
from app.da.password import PasswordDA
import app.util.password as password
from app.exceptions.file_sharing import FileStorageUploadError

logger = logging.getLogger(__name__)


class FileStorageDA(object):
    source = source
    refile_path = os.path.dirname(os.path.abspath(__file__))

    '''
        This new method will ignore filepaths and instead will stack files under member_id folders i.e.
        "/1/filenamex.ext"
    '''
    @classmethod
    def put_file_to_storage(cls, file, file_size_bytes=None, mime_type=None, member_id=None):
        s3_location = settings.get("storage.s3.file_location_host")
        uniquestr = str(uuid.uuid4())[:8]
        (dirname, true_filename) = os.path.split(file.filename)
        s3_key = f"{member_id}/{uniquestr}_{true_filename}" if member_id else f"{uniquestr}_{true_filename}"
        # logger.debug('file type', type(file),
        #  'type file.file', type(file.file))

        # https://github.com/yohanboniface/falcon-multipart#dealing-with-files
        # filename: the filename, if given
        # value: the file content in bytes
        # type: the content-type, or None if not specified
        # disposition: content-disposition, or None if not specified
        logger.debug(f"Filename: {file.filename}")
        # logger.debug(f"Value: {file.value}")
        logger.debug(f"Type: {file.type}")
        logger.debug(f"Disposition: {file.disposition}")
        logger.debug(f"File Size Bytes: {file_size_bytes}")
        logger.debug(file.file)
        logger.debug(file.file.fileno)

        if not file_size_bytes:
            file_size_bytes = os.fstat(file.file.fileno()).st_size

        mime_types = [
            file.type,
            mimetypes.MimeTypes().guess_type(file.filename)[0]
        ]

        logger.debug(f"Mime Types Part 1: {mime_types}")

        uploaded = cls.stream_to_aws(file.file, s3_key)
        storage_url = urljoin(s3_location, s3_key)

        mime_types.append(uploaded["ContentType"])

        logger.debug(f"Mime Types Part 2: {mime_types}")

        mime_types = [mime for mime in mime_types if mime]
        mime_type = next(iter(mime_types or []), None)

        logger.debug(f"Type: {mime_type}")
        logger.debug(f"Size: {file_size_bytes}")


        file_id = cls.create_file_storage_entry(
            storage_url, 's3', "available", file_size_bytes, mime_type)
        return file_id

    @classmethod
    def put_file_content_to_storage(cls, file, file_name, file_size_bytes, mime_type, member_id=None, is_unique=False):
        s3_location = settings.get("storage.s3.file_location_host")
        uniquestr = str(uuid.uuid4())[:8]
        (dirname, true_filename) = os.path.split(file_name)

        if is_unique:
            s3_key = true_filename
        else:
            s3_key = f"{member_id}/{uniquestr}_{true_filename}" if member_id else f"{uniquestr}_{true_filename}"

        uploaded = cls.stream_to_aws(file, s3_key)
        storage_url = urljoin(s3_location, s3_key)

        file_id = cls.create_file_storage_entry(
            storage_url, 's3', "available", file_size_bytes, mime_type)
        return file_id

    @classmethod
    def stream_to_aws(cls, file, key):
        try:
            s3 = cls.aws_s3_client()
            bucket = settings.get("storage.s3.bucket")
            upload = s3.upload_fileobj(file, bucket, key)
            exists = cls.check_if_key_exists(key)
            if exists:
                logger.debug("Upload Successful, Yoda")
                return exists
            else:
                raise FileStorageUploadError
                logger.debug("Key doesnt exist, Yoda")
                return False
        except FileNotFoundError:
            print("The file was not found")
            return False
        except NoCredentialsError:
            print("Credentials not available")
            return False

    @classmethod
    def put_favicon(cls, site_url=''):
        response = password.get_largest_favicon(site_url)
        logger.debug(f"response_here:{response.url}")
        logger.debug(f"response_headers: {response.headers}")
        if response is None:
            return None
        uniquestr = str(uuid.uuid4())[:8]
        true_filename = os.path.split(response.url)[1]
        logger.debug(f"True Filename: {true_filename}")
        s3_key = f"favicon_{uniquestr}_{true_filename}"
        logger.debug(f"S3 Key: {s3_key}")

        s3 = cls.aws_s3_client()
        bucket = settings.get("storage.s3.bucket")

        s3_response = s3.upload_fileobj(response.raw, bucket, s3_key)
        s3_location = settings.get("storage.s3.file_location_host")
        storage_url = urljoin(s3_location, s3_key)

        logger.debug(s3_response)

        mime_type = mimetypes.MimeTypes().guess_type(true_filename)[0]
        file_size_bytes = len(response.content)

        file_id = cls.create_file_storage_entry(
            storage_url, 's3', "available", file_size_bytes, mime_type)
        return file_id

    @classmethod
    def favicon_stream_s3_file(cls, password):
        logger.debug(f'Password Favicon: {password}')

        try:
            file_path = urlparse(password["storage_engine_id"]).path
            file_path = file_path[1:]
            s3_resp = cls.stream_s3_file(file_path)
            return s3_resp
        except Exception as e:
            pass
        try:
            icon = cls.put_favicon(password["website"])
            cls.delete_file(password["icon"])
            PasswordDA.update_password_favicon(password["id"], icon)

            password = PasswordDA.get_password(password["id"])

            file_path = urlparse(password["storage_engine_id"]).path
            file_path = file_path[1:]
            s3_resp = cls.stream_s3_file(file_path)

            return s3_resp
        except Exception as e2:
            raise e2

    @classmethod
    def upload_to_aws(cls, local_file, bucket, s3_file):
        s3 = cls.aws_s3_client()

        try:
            s3.upload_file(local_file, bucket, s3_file)
            exists = cls.check_if_key_exists(s3_file)
            if exists:
                logger.debug("Upload Successful, Yoda")
                return True
            else:
                return False
        except FileNotFoundError:
            print("The file was not found")
            return False
        except NoCredentialsError:
            print("Credentials not available")
            return False

    @classmethod
    def check_if_key_exists(cls, key):
        bucket = settings.get("storage.s3.bucket")
        s3 = cls.aws_s3_client()
        try:
            return s3.head_object(Bucket=bucket, Key=key)
        except ClientError:
            return False

    @classmethod
    def create_file_storage_entry(cls, file_path, storage_engine, status, file_size_bytes, mime_type,
                                  commit=True):
        # TODO: CHANGE THIS LATER TO ENCRYPT IN APP
        query = ("""
            INSERT INTO file_storage_engine
            (storage_engine_id, storage_engine, status, file_size_bytes, mime_type)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """)

        params = (file_path, storage_engine, status,
                  file_size_bytes, mime_type)
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
        # FIXME: change to size from fs_engine
        query = ("""
            SELECT
                member_file.id as member_file_id,
                member_file.file_id as file_id,
                member_file.file_name as file_name,
                member_file.categories as categories,
                member_file.file_size_bytes as file_size_bytes,
                member_file.file_ivalue as file_ivalue,
                file_storage_engine.storage_engine_id as file_link,
                file_storage_engine.storage_engine as storage_engine,
                file_storage_engine.mime_type as mime_type,
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
                id,
                file_id,
                file_name,
                categories,
                file_size_bytes,
                file_ivalue,
                file_link,
                storage_engine,
                mime_type,
                status,
                created_date,
                updated_date,
                file_status,
            ) in cls.source.cursor:
                member_file = {
                    "member_file_id": id,
                    "file_id": file_id,
                    "file_name": file_name,
                    "categories": categories,
                    "file_size_bytes": file_size_bytes,
                    "file_ivalue": file_ivalue,
                    "file_url": amerize_url(file_link),
                    "storage_engine": storage_engine,
                    "mime_type": mime_type,
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
    def get_file_storage_by_storage_engine_id(cls, storage_engine_id):
        query = ("""
            SELECT
                file_storage_engine.id as file_id,
                file_storage_engine.storage_engine_id as file_location,
                file_storage_engine.storage_engine as storage_engine,
                file_storage_engine.status as status,
                file_storage_engine.create_date as created_date,
                file_storage_engine.update_date as updated_date,
                file_storage_engine.mime_type as mime_type,
                file_storage_engine.file_size_bytes as file_size_bytes
            FROM file_storage_engine
            WHERE file_storage_engine.storage_engine_id = %s
        """)
        params = (storage_engine_id,)
        cls.source.execute(query, params)

        result = None
        if cls.source.has_results():
            (
                file_id,
                file_location,
                storage_engine,
                status,
                created_date,
                updated_date,
                mime_type,
                file_size_bytes
            ) = cls.source.cursor.fetchone()
            result = {
                "file_id": file_id,
                "file_location": file_location,
                "storage_engine": storage_engine,
                "status": status,
                "created_date": created_date,
                "updated_date": updated_date,
                "mime_type": mime_type,
                "file_size_bytes": file_size_bytes
            }
        
        return result

    @classmethod
    def get_file_detail_by_storage_engine_id(cls, member, storage_engine_id):
        query = ("""
            SELECT
                file_storage_engine.id as file_id,
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
            WHERE file_storage_engine.storage_engine_id = %s
            ORDER BY file_storage_engine.create_date DESC
        """)
        params = (storage_engine_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                file_id,
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

                #  url is "https://file-testing.s3.us-east-2.amazonaws.com/folder1/foldder2/file.ext"
                item_key = urlparse(file_url).path

                download = cls.download_aws_object(
                    bucket_name, item_key, file_ivalue)
                if download:
                    return f"{item_key}{file_ivalue}"
            except Exception as e:
                print(e)

    @classmethod
    def rename_file(cls, file_id, new_file_name):
        """
            We don't touch the actual file nor its path in storage (for performance reasons), we do only change the displayed filename in member_files table .
        """
        try:
            query = ("""
                        UPDATE member_file
                        SET file_name = %s
                        WHERE id = %s
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

    @classmethod
    def stream_s3_file(cls, s3_file_path):
        s3 = cls.aws_s3_client()
        bucket = settings.get("storage.s3.bucket")

        try:
            s3_response = s3.get_object(
                Bucket=bucket, Key=s3_file_path)
            return s3_response
        except Exception as e:
            raise e

    @classmethod
    def get_download_url_for_object(cls, file_key, bucket=None):
        if not bucket:
            bucket = settings.get("storage.s3.bucket")
        logger.debug(f"GET DOWNLOAD URL PARAMETERS:\n{file_key}\n{bucket}")
        s3 = cls.aws_s3_client()
        # Generate the URL to get 'key-name' from 'bucket-name'
        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': bucket,
                'Key': file_key
            }
        )
        return url

    @classmethod
    def get_storage_engine_id_from_key(cls, file_key):
        s3_location = settings.get("storage.s3.file_location_host")
        storage_url = urljoin(s3_location, file_key)
        return storage_url


class FileTreeDA(object):
    source = source
    refile_path = os.path.dirname(os.path.abspath(__file__))

    @classmethod
    def create_file_tree_entry(cls, tree_id, parent_id, member_file_id, display_name):
        query = ("""
            INSERT into file_tree_item (file_tree_id, parent_id, member_file_id, display_name)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """)
        params = (tree_id, parent_id, member_file_id, display_name)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[create_file_tree_entry] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def create_member_file_entry(cls, file_id, file_name, member_id, status,
                                 file_size_bytes, category=None, iv=None, commit=True):
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
    def get_member_file_by_file_id(cls, member_id, file_id):
        query = ("""
            SELECT
                member_file.id,
                member_file.file_id,
                member_file.file_name,
                member_file.status,
                member_file.member_id,
                member_file.categories,
                member_file.file_ivalue,
                member_file.file_size_bytes
            FROM member_file
            WHERE member_file.member_id = %s AND member_file.file_id = %s
        """)
        params = (member_id, file_id,)
        cls.source.execute(query, params)

        result = None
        if cls.source.has_results():
            (
                id,
                file_id,
                file_name,
                status,
                member_id,
                categories,
                file_ivalue,
                file_size_bytes
            ) = cls.source.cursor.fetchone()
            result = {
                "id": id,
                "file_id": file_id,
                "file_name": file_name,
                "status": status,
                "member_id": member_id,
                "categories": categories,
                "file_ivalue": file_ivalue,
                "file_size_bytes": file_size_bytes
            }
        
        return result

    @classmethod
    def get_tree(cls, member, tree_type):
        '''
            We expect only the root node to have parent_id of NULL
            The two queries are the same except this part
            LEFT JOIN file_tree_item ON >>>>> member.main_file_tree <<<<< = file_tree_item.file_tree_id
        '''
        main_tree_query = ("""
            WITH RECURSIVE tree AS (
                SELECT
                    file_tree_item.id,
                    parent_id,
                    member_file_id,
                    display_name,
                    file_tree_item.update_date as node_update_date,
                    file_tree_item.create_date as node_create_date,
                    0 AS level
                FROM member
                LEFT JOIN file_tree_item ON member.main_file_tree = file_tree_item.file_tree_id
                LEFT JOIN member_file ON file_tree_item.member_file_id = member_file.id
                WHERE member.id = %s AND parent_id is null
                UNION ALL
            SELECT ft.id, ft.parent_id, ft.member_file_id, ft.display_name, ft.update_date as  node_update_date, ft.create_date as node_create_date, tree.level + 1 AS level
                FROM file_tree_item ft
                JOIN tree ON ft.parent_id = tree.id
            )
            SELECT
                tree.id,
                tree.parent_id,
                tree.display_name,
                member_file.id as file_id,
                member_file.file_name as file_name,
                member_file.file_ivalue as iv,
                member_file.file_size_bytes as size,
                -- find all INDIVIDUALS  with whom I shared a node
                (
                    SELECT json_agg(shares) as shared_with_individuals
                    FROM (
                        SELECT
                          file_share.id as share_id,
                          file_share.create_date as shared_date,
                          member.id as consumer_id,
                          member.email as consumer_email,
                          member.first_name as consumer_first_name,
                          member.last_name as consumer_last_name,
                          member.company_name as consumer_company_name,
                          job_title.name as job_title,
                          department.name as department
                        FROM file_share
                        LEFT JOIN file_tree_item ON file_share.target_node = file_tree_item.id
                        LEFT JOIN member ON file_tree_item.file_tree_id = member.main_file_tree
                        LEFT JOIN job_title ON member.job_title_id = job_title.id
                        LEFT JOIN department ON member.department_id = department.id
                        WHERE original_node = tree.id AND member.id IS NOT NULL
                    ) AS shares
                ),
                -- find all groups I shared with
                (
                    SELECT json_agg(shares) as shared_with_groups
                    FROM (
                        SELECT
                          file_share.id as share_id,
                          file_share.create_date as shared_date,
                          member_group.id as group_id,
                          member_group.group_name as group_name,
                          member_group.exchange_option as exchange_option,
                          member_group.group_leader_id as leader_id,
                          member.first_name as leader_first_name,
                          member.last_name as leader_last_name,
                          member.company_name as leader_company,
                          job_title.name as job_title,
                          department.name as department
                        FROM file_share
                        LEFT JOIN file_tree_item ON file_share.target_node = file_tree_item.id
                        LEFT JOIN member_group ON file_tree_item.file_tree_id = member_group.main_file_tree
                        LEFT JOIN member ON member_group.group_leader_id = member.id
                        LEFT JOIN job_title ON member.job_title_id = job_title.id
                        LEFT JOIN department ON member.department_id = department.id
                        WHERE original_node = tree.id AND member_group.id IS NOT NULL
                    ) AS shares
                ),
                -- find information on the file that was shared with me
                (
                    SELECT row_to_json(shares) as shared_by_individuals
                    FROM
                    (
                        SELECT
                          file_share.id as share_id,
                          file_share.create_date as shared_date,
                          member.id as sharer_id,
                          member.email as sharer_email,
                          member.first_name as sharer_first_name,
                          member.last_name as sharer_last_name,
                          member.company_name as sharer_company_name,
                          job_title.name as job_title,
                          department.name as department
                        FROM file_share
                        LEFT JOIN file_tree_item ON file_share.original_node = file_tree_item.id
                        LEFT JOIN member ON file_tree_item.file_tree_id = member.main_file_tree
                        LEFT JOIN job_title ON member.job_title_id = job_title.id
                        LEFT JOIN department ON member.department_id = department.id
                        WHERE target_node = tree.id
                    ) AS shares
                ),
                file_storage_engine.update_date as modDate,
                file_storage_engine.storage_engine_id as fs_url,
                file_storage_engine.create_date as create_date,
                tree.node_update_date as node_modDate,
                tree.node_create_date as node_createDate,
                member_file.member_id as create_member_id
            FROM tree
            LEFT JOIN member_file ON tree.member_file_id =member_file.id
            LEFT JOIN file_storage_engine ON member_file.file_id = file_storage_engine.ID
            ORDER BY level, display_name
        """)
        bin_tree_query = ("""
            WITH RECURSIVE tree AS (
                SELECT
                    file_tree_item.id,
                    parent_id,
                    member_file_id,
                    display_name,
                    file_tree_item.update_date as node_update_date,
                    file_tree_item.create_date as node_create_date,
                    0 AS level
                FROM member
                LEFT JOIN file_tree_item ON member.bin_file_tree = file_tree_item.file_tree_id
                LEFT JOIN member_file ON file_tree_item.member_file_id = member_file.id
                WHERE member.id = %s AND parent_id is null
                UNION ALL
            SELECT ft.id, ft.parent_id, ft.member_file_id, ft.display_name, ft.update_date as node_update_date, ft.create_date as node_create_date, tree.level + 1 AS level
                FROM file_tree_item ft
                JOIN tree ON ft.parent_id = tree.id
            )
            SELECT
                tree.id,
                tree.parent_id,
                tree.display_name,
                member_file.id as file_id,
                member_file.file_name as file_name,
                member_file.file_ivalue as iv,
                member_file.file_size_bytes as size,
                -- find all INDIVIDUALS  with whom I shared a node
                (
                    SELECT json_agg(shares) as shared_with_individuals
                    FROM (
                        SELECT
                          file_share.id as share_id,
                          file_share.create_date as shared_date,
                          member.id as consumer_id,
                          member.email as consumer_email,
                          member.first_name as consumer_first_name,
                          member.last_name as consumer_last_name,
                          member.company_name as consumer_company_name,
                          job_title.name as job_title,
                          department.name as department
                        FROM file_share
                        LEFT JOIN file_tree_item ON file_share.target_node = file_tree_item.id
                        LEFT JOIN member ON file_tree_item.file_tree_id = member.main_file_tree
                        LEFT JOIN job_title ON member.job_title_id = job_title.id
                        LEFT JOIN department ON member.department_id = department.id
                        WHERE original_node = tree.id AND member.id IS NOT NULL
                    ) AS shares
                ),
                -- find all groups I shared with
                (
                    SELECT json_agg(shares) as shared_with_groups
                    FROM (
                        SELECT
                          file_share.id as share_id,
                          file_share.create_date as shared_date,
                          member_group.id as group_id,
                          member_group.group_name as group_name,
                          member_group.exchange_option as exchange_option,
                          member_group.group_leader_id as leader_id,
                          member.first_name as leader_first_name,
                          member.last_name as leader_last_name,
                          member.company_name as leader_company,
                          job_title.name as job_title,
                          department.name as department
                        FROM file_share
                        LEFT JOIN file_tree_item ON file_share.target_node = file_tree_item.id
                        LEFT JOIN member_group ON file_tree_item.file_tree_id = member_group.main_file_tree
                        LEFT JOIN member ON member_group.group_leader_id = member.id
                        LEFT JOIN job_title ON member.job_title_id = job_title.id
                        LEFT JOIN department ON member.department_id = department.id
                        WHERE original_node = tree.id AND member_group.id IS NOT NULL
                    ) AS shares
                ),
                -- find information on the file that was shared with me
                (
                    SELECT row_to_json(shares) as shared_by_individuals
                    FROM
                    (
                        SELECT
                          file_share.id as share_id,
                          file_share.create_date as shared_date,
                          member.id as shared_id,
                          member.email as sharer_email,
                          member.first_name as sharer_first_name,
                          member.last_name as sharer_last_name,
                          member.company_name as sharer_company_name,
                          job_title.name as job_title,
                          department.name as department
                        FROM file_share
                        LEFT JOIN file_tree_item ON file_share.original_node = file_tree_item.id
                        LEFT JOIN member ON file_tree_item.file_tree_id = member.main_file_tree
                        LEFT JOIN job_title ON member.job_title_id = job_title.id
                        LEFT JOIN department ON member.department_id = department.id
                        WHERE target_node = tree.id
                    ) AS shares
                ),
                file_storage_engine.update_date as modDate,
                file_storage_engine.storage_engine_id as fs_url,
                file_storage_engine.create_date as create_date,
                tree.node_update_date as node_modDate,
                tree.node_create_date as node_createDate,
                member_file.member_id as create_member_id
            FROM tree
            LEFT JOIN member_file ON tree.member_file_id =member_file.id
            LEFT JOIN file_storage_engine ON member_file.file_id = file_storage_engine.id
            ORDER BY level, display_name
        """)

        query = main_tree_query if tree_type == 'main' else bin_tree_query
        cls.source.execute(query, (member,))
        if cls.source.has_results():
            entry = list()
            for entry_da in cls.source.cursor.fetchall():

                node_id = entry_da[0]
                parent_id = entry_da[1]
                display_name = entry_da[2]
                file_id = entry_da[3]
                file_name = entry_da[4]
                iv = entry_da[5]
                size = entry_da[6]
                shared_with_members = entry_da[7]
                shared_with_groups = entry_da[8]
                shared_with_me = entry_da[9]
                mod_date = entry_da[10]
                amera_url = amerize_url(entry_da[11]) if file_id else None
                create_date = entry_da[12]
                node_modDate = entry_da[13]
                node_createDate = entry_da[14]
                create_member = entry_da[15]

                entry_element = {
                    "id": entry_da[0],
                    "file_id": file_id,  # this points to member_file
                    "parentId": parent_id,  # parent_id
                    # we check if this is a directory
                    "isDir": True if file_id == None else False,
                    # display_name
                    "name": display_name if file_id == None else file_name,
                    "isEncrypted": False if iv == None else True,
                    "sharedWithMembers":  shared_with_members,
                    "sharedWithGroups":  shared_with_groups,
                    "sharedWithMe": shared_with_me,
                    "size": size,
                    "modDate": node_modDate if file_id == None else mod_date,
                    "amera_file_url": amera_url,
                    "create_date": node_createDate if file_id == None else create_date,
                    "create_member": create_member
                }
                entry.append(entry_element)
            return entry
        return None

    @classmethod
    def create_group_tree(cls, tree_type):
        query = ("""
            INSERT into file_tree (type)
            VALUES (%s)
            RETURNING id
        """)
        params = (tree_type)
        logger.debug(f'params: {params}')
        cls.source.execute(query, [params])
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[create_group_tree] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def bind_group_tree_with(cls, member_group_id, main_file_tree_id, bin_file_tree_id):
        logger.debug(
            f'bind_group_tree_with group_id {member_group_id} with file_tree_id {main_file_tree_id} {bin_file_tree_id}')
        query = ("""
            UPDATE member_group
            SET main_file_tree = %s,
                bin_file_tree = %s
            WHERE id = %s
            RETURNING id
        """)
        params = (main_file_tree_id, bin_file_tree_id, member_group_id)
        logger.debug(f'params: {params}')
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[bind_group_tree_with] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def create_group_tree_root_folder(cls, file_tree_id, folder_name):
        query = ("""
            INSERT into file_tree_item (file_tree_id, is_tree_root, display_name)
            VALUES (%s, true, %s)
            RETURNING id
        """)
        params = (file_tree_id, folder_name)
        logger.debug(f'params: {params}')
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[create_group_tree_root_folder] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def get_group_tree(cls, groupId, tree_type):
        main_tree_query = ("""
         WITH RECURSIVE tree AS (
                SELECT
                    file_tree_item.id,
                    parent_id,
                    member_file_id,
                    display_name,
                    file_tree_item.update_date as node_update_date,
                    file_tree_item.create_date as node_create_date,
                    0 AS level
                FROM member_group
                LEFT JOIN file_tree_item ON member_group.main_file_tree = file_tree_item.file_tree_id
                LEFT JOIN member_file ON file_tree_item.member_file_id = member_file.id
                WHERE member_group.id = %s AND parent_id is null
                UNION ALL
            SELECT ft.id, ft.parent_id, ft.member_file_id, ft.display_name, ft.update_date as  node_update_date, ft.create_date as node_create_date, tree.level + 1 AS level
                FROM file_tree_item ft
                JOIN tree ON ft.parent_id = tree.id
            )
            SELECT
                tree.id,
                tree.parent_id,
                tree.display_name,
                member_file.id as file_id,
                member_file.file_name as file_name,
                member_file.file_ivalue as iv,
                member_file.file_size_bytes as size,
                -- find information on the file that was shared with me
                (
                    SELECT row_to_json(shares) as shared_by_individuals
                    FROM
                    (
                        SELECT
                          file_share.id as share_id,
                          file_share.create_date as shared_date,
                          member.id as sharer_id,
                          member.email as sharer_email,
                          member.first_name as sharer_first_name,
                          member.last_name as sharer_last_name,
                          member.company_name as sharer_company_name,
                          job_title.name as job_title,
                          department.name as department
                        FROM file_share
                        LEFT JOIN file_tree_item ON file_share.original_node = file_tree_item.id
                        LEFT JOIN member ON file_tree_item.file_tree_id = member.main_file_tree
                        LEFT JOIN job_title ON member.job_title_id = job_title.id
                        LEFT JOIN department ON member.department_id = department.id
                        WHERE target_node = tree.id
                    ) AS shares
                ),
                file_storage_engine.update_date as modDate,
                file_storage_engine.storage_engine_id as fs_url,
                file_storage_engine.create_date as create_date,
                tree.node_update_date as node_modDate,
                tree.node_create_date as node_createDate,
                member_file.member_id as create_member_id
            FROM tree
            LEFT JOIN member_file ON tree.member_file_id =member_file.id
            LEFT JOIN file_storage_engine ON member_file.file_id = file_storage_engine.ID
            ORDER BY level, display_name
        """)

        bin_tree_query = ("""
         WITH RECURSIVE tree AS (
                SELECT
                    file_tree_item.id,
                    parent_id,
                    member_file_id,
                    display_name,
                    file_tree_item.update_date as node_update_date,
                    file_tree_item.create_date as node_create_date,
                    0 AS level
                FROM member_group
                LEFT JOIN file_tree_item ON member_group.bin_file_tree = file_tree_item.file_tree_id
                LEFT JOIN member_file ON file_tree_item.member_file_id = member_file.id
                WHERE member_group.id = %s AND parent_id is null
                UNION ALL
            SELECT ft.id, ft.parent_id, ft.member_file_id, ft.display_name, ft.update_date as  node_update_date, ft.create_date as node_create_date, tree.level + 1 AS level
                FROM file_tree_item ft
                JOIN tree ON ft.parent_id = tree.id
            )
            SELECT
                tree.id,
                tree.parent_id,
                tree.display_name,
                member_file.id as file_id,
                member_file.file_name as file_name,
                member_file.file_ivalue as iv,
                member_file.file_size_bytes as size,
                -- find information on the file that was shared with me
                (
                    SELECT row_to_json(shares) as shared_by_individuals
                    FROM
                    (
                        SELECT
                          file_share.id as share_id,
                          file_share.create_date as shared_date,
                          member.id as sharer_id,
                          member.email as sharer_email,
                          member.first_name as sharer_first_name,
                          member.last_name as sharer_last_name,
                          member.company_name as sharer_company_name,
                          job_title.name as job_title,
                          department.name as department
                        FROM file_share
                        LEFT JOIN file_tree_item ON file_share.original_node = file_tree_item.id
                        LEFT JOIN member ON file_tree_item.file_tree_id = member.main_file_tree
                        LEFT JOIN job_title ON member.job_title_id = job_title.id
                        LEFT JOIN department ON member.department_id = department.id
                        WHERE target_node = tree.id
                    ) AS shares
                ),
                file_storage_engine.update_date as modDate,
                file_storage_engine.storage_engine_id as fs_url,
                file_storage_engine.create_date as create_date,
                tree.node_update_date as node_modDate,
                tree.node_create_date as node_createDate,
                member_file.member_id as create_member_id
            FROM tree
            LEFT JOIN member_file ON tree.member_file_id =member_file.id
            LEFT JOIN file_storage_engine ON member_file.file_id = file_storage_engine.ID
            ORDER BY level, display_name
        """)

        query = main_tree_query if tree_type == 'main' else bin_tree_query
        cls.source.execute(query, (groupId,))
        if cls.source.has_results():
            entry = list()
            for entry_da in cls.source.cursor.fetchall():

                node_id = entry_da[0]
                parent_id = entry_da[1]
                display_name = entry_da[2]
                file_id = entry_da[3]
                file_name = entry_da[4]
                iv = entry_da[5]
                size = entry_da[6]
                shared_with_group = entry_da[7]
                mod_date = entry_da[8]
                amera_url = amerize_url(entry_da[9]) if file_id else None
                create_date = entry_da[10]
                node_modDate = entry_da[11]
                node_createDate = entry_da[12]
                create_member = entry_da[13]

                entry_element = {
                    "id": entry_da[0],
                    "file_id": file_id,  # this points to member_file
                    "parentId": parent_id,  # parent_id
                    # we check if this is a directory
                    "isDir": True if file_id == None else False,
                    # display_name
                    "name": display_name if file_id == None else file_name,
                    "isEncrypted": False if iv == None else True,
                    "sharedWithMe": shared_with_group,
                    "size": size,
                    "modDate": node_modDate if file_id == None else mod_date,
                    "amera_file_url": amera_url,
                    "create_date": node_createDate if file_id == None else create_date,
                    "create_member": create_member
                }
                entry.append(entry_element)
            return entry
        return None

    @classmethod
    def get_tree_id(cls, target_id, target_type, tree_type):
        member_main_tree_query = ("""
            SELECT main_file_tree FROM member WHERE id=%s
        """)
        member_bin_tree_query = ("""
            SELECT bin_file_tree FROM member WHERE id=%s
        """)
        group_main_tree_query = ("""
            SELECT main_file_tree FROM member_group WHERE id=%s
        """)
        group_bin_tree_query = ("""
            SELECT bin_file_tree FROM member_group WHERE id=%s
        """)

        if target_type == 'group':
            query = group_main_tree_query if tree_type == 'main' else group_bin_tree_query
        elif target_type == 'member':
            query = member_main_tree_query if tree_type == 'main' else member_bin_tree_query

        cls.source.execute(query, (target_id,))
        (tree_id,) = cls.source.cursor.fetchone()
        return tree_id

    @classmethod
    def get_tree_root_id(cls, tree_id):
        query = ("""
            SELECT id FROM file_tree_item
            WHERE is_tree_root = TRUE AND file_tree_id = %s
        """)
        params = (tree_id,)
        cls.source.execute(query, params)
        (root_id,) = cls.source.cursor.fetchone()
        return root_id

    @classmethod
    def create_tree(cls, tree_type, target_type, is_return_item_id=False):
        '''
            We use to create empty trees (having only root folders) when member is created
            tree id is returned to be written in member table
        '''
        query = ("""
            WITH rows AS (
                INSERT INTO file_tree (type) VALUES (%s) RETURNING id
            )

            INSERT INTO file_tree_item (file_tree_id, is_tree_root, display_name)
                SELECT
                    id,
                    TRUE,
                    %s
                FROM rows
                RETURNING file_tree_id, id
        """)
        if tree_type == 'main':
            if target_type == 'member':
                node_name = 'My files'
            elif target_type == 'group':
                node_name = 'Group Files'
        elif tree_type == 'bin':
            node_name = 'Trash'
        params = (tree_type, node_name)
        cls.source.execute(query, params)
        (tree_id, file_tree_id) = cls.source.cursor.fetchone()
        cls.source.commit()

        if is_return_item_id:
            return tree_id, file_tree_id
        return tree_id

    @classmethod
    def delete_branch(cls, branch_root_id, bin_tree_id):
        '''
            Takes a branch recursively and moves it to bin tree
            The parent_id of branch_root item is set to Bin root
        '''
        query = ("""
             WITH RECURSIVE tree AS (
                SELECT
                    file_tree_item.id,
                    parent_id,
                    0 AS level
                FROM file_tree_item
                WHERE id = %s
                UNION ALL
            SELECT ft.id, ft.parent_id, tree.level + 1 AS level
                FROM file_tree_item ft
                JOIN tree ON ft.parent_id = tree.id
            )
            UPDATE file_tree_item
                SET file_tree_id = %s
                WHERE id IN (SELECT id FROM tree ORDER BY level);

            UPDATE file_tree_item
            --     this is the bin root
                SET parent_id = sq.bin_root_id
                FROM (SELECT id AS bin_root_id
                    FROM file_tree_item WHERE parent_id IS NULL AND file_tree_id=%s) as sq
                WHERE id=%s;
        """)
        params = (branch_root_id, bin_tree_id, bin_tree_id, branch_root_id)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def restore_branch(cls, branch_root_id, main_tree_id):
        '''
            Restores a branch from bin to main tree
        '''
        query = ("""
            WITH RECURSIVE tree AS (
                SELECT
                    file_tree_item.id,
                    parent_id,
                    0 AS level
                FROM file_tree_item
                WHERE id = %s
                UNION ALL
            SELECT ft.id, ft.parent_id, tree.level + 1 AS level
                FROM file_tree_item ft
                JOIN tree ON ft.parent_id = tree.id
            )
            UPDATE file_tree_item
                SET file_tree_id = %s
                WHERE id IN (SELECT id FROM tree ORDER BY level);

            UPDATE file_tree_item
            --     this is the main root
                SET parent_id = sq.main_root_id
                FROM (SELECT id AS main_root_id
                    FROM file_tree_item WHERE parent_id IS NULL AND file_tree_id=%s) as sq
                WHERE id=%s;
        """)
        params = (branch_root_id, main_tree_id, main_tree_id, branch_root_id)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def delete_branch_forever(cls, branch_root_id):
        '''Deletes member_file entries and file_tree_item entries'''
        query = ("""
             WITH RECURSIVE tree AS (
                SELECT
                    file_tree_item.id,
                    parent_id,
                     member_file_id,
                    0 AS level
                FROM file_tree_item
                WHERE id = %s
                UNION ALL
            SELECT ft.id, ft.parent_id, ft.member_file_id, tree.level + 1 AS level
                FROM file_tree_item ft
                JOIN tree ON ft.parent_id = tree.id
            )

            DELETE FROM member_file
            WHERE id IN (SELECT member_file_id FROM tree);

            DELETE FROM file_tree_item
            WHERE id=%s
        """)
        params = (branch_root_id, branch_root_id)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def modify_branch(cls, branch_root_id, display_name, parent_id):
        ''' Changes name and/or location of a branch'''
        query = ('''
            UPDATE file_tree_item
            SET
                display_name = %s,
                parent_id = %s
            WHERE id = %s
        ''')
        params = (display_name, parent_id, branch_root_id)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def share_branch(cls, member_id, target_tree_id, branch_root_id):
        ''' creates a new branch in target tree id by copying each child

        '''
        get_branch_query = ('''
            WITH RECURSIVE tree AS (
                SELECT
                    file_tree_item.id as original_node_id,
                    parent_id as original_parent_id,
                    member_file_id,
                    display_name,
                    0 AS level
                FROM member
                LEFT JOIN file_tree_item ON member.main_file_tree = file_tree_item.file_tree_id
                LEFT JOIN member_file ON file_tree_item.member_file_id = member_file.id
                WHERE member.id = %s AND file_tree_item.id = %s
                UNION ALL
            SELECT ft.id, ft.parent_id, ft.member_file_id, ft.display_name, tree.level + 1 AS level
                FROM file_tree_item ft
                JOIN tree ON ft.parent_id = tree.original_node_id
            )
            SELECT * FROM tree
        ''')
        get_branch_params = (member_id, branch_root_id)
        cls.source.execute(get_branch_query, get_branch_params)
        if cls.source.has_results():

            original_nodes = list()
            for entry_da in cls.source.cursor.fetchall():
                original_node_id = entry_da[0]
                original_parent_id = entry_da[1]
                member_file_id = entry_da[2]
                display_name = entry_da[3]
                level = entry_da[4]

                entry_element = {
                    "original_node_id": original_node_id,
                    "original_parent_id": original_parent_id,
                    "member_file_id": member_file_id,
                    "display_name": display_name,
                    "level": level
                }
                original_nodes.append(entry_element)
            # TODO: Check if all of this can be done in by a single query
            '''
                Now we iterate over level starting from 0 to create new nodes in target tree.
                After each step
            '''
            # This will look like {original_node_id: target_node_id, ...}
            original_target_node_xref = dict()

            for node in original_nodes:
                original_node_id, original_parent_id, member_file_id, display_name, level = itemgetter(
                    "original_node_id", "original_parent_id", "member_file_id", "display_name", "level")(node)
                if level == 0:
                    tree_root_id = cls.get_tree_root_id(target_tree_id)
                    target_node_id = cls.create_file_tree_entry(
                        target_tree_id, tree_root_id, member_file_id, display_name)
                    cls.create_share_entry(original_node_id, target_node_id)
                    original_target_node_xref[original_node_id] = target_node_id
                else:
                    new_parent_id = original_target_node_xref[original_parent_id]
                    target_node_id = cls.create_file_tree_entry(
                        target_tree_id, new_parent_id, member_file_id, display_name)
                    cls.create_share_entry(original_node_id, target_node_id)
                    original_target_node_xref[original_node_id] = target_node_id

            # return original_target_node_xref

    @classmethod
    def create_share_entry(cls, original_node_id, target_node_id):
        query = ('''
            INSERT INTO file_share (original_node, target_node) VALUES (%s,%s)
        ''')
        params = (original_node_id, target_node_id,)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def unshare_node(cls, share_id):
        ''' This will automatically delete file_shares entry due to ON DELETE CASCADE constraint'''
        query = ('''
            DELETE FROM file_tree_item
            WHERE id IN (SELECT target_node FROM file_share WHERE id = %s)
        ''')
        params = (share_id,)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def copy_member_file(cls, member_file_id, new_member_id):
        query = ('''
            WITH file_record as (
                SELECT *
                FROM member_file
                WHERE id = %s
            )

            INSERT INTO member_file (file_id, file_name, status, member_id, categories, file_ivalue, file_size_bytes)
            SELECT
                file_id,
                file_name,
                status,
                %s,
                categories,
                file_ivalue,
                file_size_bytes
            FROM file_record
            RETURNING id
        ''')
        params = (member_file_id, new_member_id)
        cls.source.execute(query, params)
        cls.source.commit()
        (member_file_id,) = cls.source.cursor.fetchone()
        return member_file_id

    @classmethod
    def claim_shared_branch(cls, member_id, target_tree_id, branch_root_id, current_folder_id):
        get_branch_query = ('''
             WITH RECURSIVE tree AS (
                SELECT
                    file_tree_item.id as original_node_id,
                    parent_id as original_parent_id,
                    member_file_id,
                    display_name,
                    0 AS level
                FROM member
                LEFT JOIN file_tree_item ON member.main_file_tree = file_tree_item.file_tree_id
                LEFT JOIN member_file ON file_tree_item.member_file_id = member_file.id
                WHERE member.id = %s AND file_tree_item.id = %s
                UNION ALL
            SELECT ft.id, ft.parent_id, ft.member_file_id, ft.display_name, tree.level + 1 AS level
                FROM file_tree_item ft
                JOIN tree ON ft.parent_id = tree.original_node_id
            )
            SELECT * FROM tree
        ''')
        get_branch_params = (member_id, branch_root_id)
        cls.source.execute(get_branch_query, get_branch_params)

        if cls.source.has_results():
            original_nodes = list()
            for entry_da in cls.source.cursor.fetchall():
                original_node_id = entry_da[0]
                original_parent_id = entry_da[1]
                member_file_id = entry_da[2]
                display_name = entry_da[3]
                level = entry_da[4]

                entry_element = {
                    "original_node_id": original_node_id,
                    "original_parent_id": original_parent_id,
                    "member_file_id": member_file_id,
                    "display_name": display_name,
                    "level": level
                }
                original_nodes.append(entry_element)
            # TODO: Check if all of this can be done in by a single query
            '''
                Now we iterate over level starting from 0 to create new nodes in target tree.
                After each step
            '''
            # This will look like {original_node_id: target_node_id, ...}
            original_target_node_xref = dict()

            for node in original_nodes:
                original_node_id, original_parent_id, member_file_id, display_name, level = itemgetter(
                    "original_node_id", "original_parent_id", "member_file_id", "display_name", "level")(node)

                if member_file_id:
                    new_member_file_id = cls.copy_member_file(
                        member_file_id, member_id)
                else:
                    new_member_file_id = None

                if level == 0:
                    target_node_id = cls.create_file_tree_entry(
                        target_tree_id, current_folder_id, new_member_file_id, display_name)
                    original_target_node_xref[original_node_id] = target_node_id
                else:
                    new_parent_id = original_target_node_xref[original_parent_id]
                    target_node_id = cls.create_file_tree_entry(
                        target_tree_id, new_parent_id, new_member_file_id, display_name)
                    original_target_node_xref[original_node_id] = target_node_id

            # return original_target_node_xref


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
                    "sharer_last_name": file[5],
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
    def get_group_list(cls, member_id):
        query = ("""
            SELECT member_group.id AS group_id,
                member_group.group_leader_id AS group_leader_id,
                member_group.group_name AS group_name,
                member_group.create_date AS create_date,
                member_group.update_date AS update_date,
                count(DISTINCT file_tree_item.id) AS total_files
            FROM member_group
                LEFT OUTER JOIN file_tree ON (file_tree.id = member_group.main_file_tree)
                LEFT OUTER JOIN (
                  SELECT id, file_tree_id
                  FROM file_tree_item
                  WHERE file_tree_item.member_file_id is NOT NULL
                ) as file_tree_item ON (file_tree_item.file_tree_id = file_tree.id)
                LEFT OUTER JOIN member_group_membership ON (
                    member_group_membership.group_id = member_group.id
                )
            WHERE (
                    member_group.group_leader_id = %s
                    OR member_group_membership.member_id = %s
                )
                AND member_group.status = 'active'
                AND file_storage_engine.status = 'available'
            GROUP BY member_group.id,
                member_group.group_leader_id,
                member_group.group_name,
                member_group.create_date,
                member_group.update_date
            ORDER BY member_group.group_name ASC
        """)
        params = (member_id, member_id)
        group_list = list()
        try:
            cls.source.execute(query, params)
            if cls.source.has_results():
                for elem in cls.source.cursor.fetchall():
                    group = {
                        "group_id": elem[0],
                        "group_name": elem[2],
                        "group_create_date": elem[3],
                        "group_update_date": elem[4]
                    }
                    group_list.append(group)
            return group_list
        except Exception as e:
            return None

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

    @classmethod
    def get_all_file_share_invitations_by_member_id(cls, member_id):
        files = list()

        try:
            query = f"""
                SELECT
                    file_share.id,
                    file_share.create_date,
                    member_file.file_name,
                    file.storage_engine_id as file_url,
                    create_user.id as create_user_id,
                    create_user.first_name,
                    create_user.last_name,
                    create_user.email,
                    file_storage_engine.storage_engine_id
                FROM member
                INNER JOIN file_tree on member.main_file_tree = file_tree.id
                INNER JOIN file_tree_item on file_tree.id = file_tree_item.file_tree_id
                INNER JOIN file_share on file_share.target_node = file_tree_item.id
                INNER JOIN member_file on member_file.id = file_tree_item.member_file_id
                INNER JOIN member create_user ON member_file.member_id = create_user.id
                LEFT JOIN member_profile ON create_user.id = member_profile.member_id
                LEFT JOIN file_storage_engine on file_storage_engine.id = member_profile.profile_picture_storage_id
                LEFT JOIN file_storage_engine file on file.id = member_file.file_id
                WHERE
                    member.id = %s
                ORDER BY file_share.create_date DESC
                LIMIT 25
            """

            params = (member_id,)

            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                        id,
                        create_date,
                        file_name,
                        file_url,
                        create_user_id,
                        first_name,
                        last_name,
                        email,
                        storage_engine_id
                ) in cls.source.cursor:
                    file = {
                        "id": id,
                        "create_date": create_date,
                        "file_name": file_name,
                        "file_url": amerize_url(file_url),
                        "create_user_id": create_user_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "amera_avatar_url": amerize_url(storage_engine_id),
                        "invitation_type": "drive_share"
                    }
                    files.append(file)

            return files
        except Exception as e:
            logger.error(e, exc_info=True)
            return None