from app.util.auth import check_session
import os
import falcon
import app.util.json as json
import mimetypes
from app.config import settings
from app.da.file_sharing import FileStorageDA
from app.da.avatar import AvatarDA
from app.exceptions.avatar import MemberAvatarNotFound, MemberAvatarNotFoundError
import logging

logger = logging.getLogger(__name__)


class MemberAvatarResource(object):

    @classmethod
    def on_get(cls, req, resp, member_id):
        try:
            file_path = AvatarDA.get_avatar_url(member_id)
            logger.debug(f"File Path: {file_path}")

            if not file_path or file_path.strip() == '':
                raise MemberAvatarNotFoundError()

            s3_location = settings.get("storage.s3.file_location_host")
            file_path = file_path.replace(f'{s3_location}/', '')
            logger.debug(f"S3 File Key: {file_path}")
            logger.debug(f"File Basename: {file_path}")

            s3_object = FileStorageDA().stream_s3_file(file_path)
            file_type = s3_object["ContentType"]
            logger.debug(f"S3 File Type: {file_type}")

            if not cls.__valid_image_file_type(file_type):
                file_type = mimetypes.MimeTypes().guess_type(file_path)[0]
                logger.debug(f"Guess File Type: {file_type}")

            file_length = s3_object["ContentLength"]
            logger.debug(f"File Content Length: {file_length}")

            resp.status = falcon.HTTP_200
            resp.stream = s3_object["Body"]
            resp.content_type = file_type
            resp.content_length = file_length
        except MemberAvatarNotFoundError as err:
            raise MemberAvatarNotFound(member_id=member_id) from err

    @classmethod
    def on_put(cls, req, resp, member_id):
        avatar = req.get_param("avatar")
        mime = req.get_param("mime")
        avatar_storage_id = FileStorageDA().put_file_to_storage(
            file=avatar, mime_type=mime, member_id=member_id)

        success = AvatarDA.update_avatar(avatar_storage_id, member_id)

        if success:

            resp.body = json.dumps({
                "data": AvatarDA.get_avatar_url(member_id),
                "success": True
            }, default_parser=json.parser)

    @classmethod
    @check_session
    def on_put_deprecated(cls, req, resp):
        cls.on_put(req, resp, req.context.auth["session"]["member_id"])

    @staticmethod
    def __valid_image_file_type(content_type):
        invalid_types = ["binary/octet-stream"]

        if not content_type or \
                content_type in invalid_types or \
                'image/' not in content_type:
            return False
        return True
