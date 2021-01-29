from app.util.auth import inject_member
import os
import falcon
import app.util.json as json
import mimetypes
from app import settings
from app.da.file_sharing import FileStorageDA
from app.da.avatar import AvatarDA
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
from app.util.session import get_session_cookie, validate_session
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class MemberAvatarResource(object):

    @classmethod
    def on_get(cls, req, resp, member_id):
        file_path = AvatarDA.get_avatar_url(member_id)
        file_path = os.path.basename(file_path)
        type = mimetypes.MimeTypes().guess_type(file_path)[0]
        s3_resp = FileStorageDA().stream_s3_file(file_path)
        resp.content_type = type
        resp.status = falcon.HTTP_200
        resp.body = s3_resp['Body'].read()

    @classmethod
    def on_put(cls, req, resp, member_id):
        avatar = req.get_param('avatar')
        avatar_storage_id = FileStorageDA().put_file_to_storage(avatar)

        success = AvatarDA.update_avatar(avatar_storage_id, member_id)

        if success:

            resp.body = json.dumps({
                "data": AvatarDA.get_avatar_url(member_id),
                "success": True
            }, default_parser=json.parser)

    @classmethod
    @inject_member
    def on_put_deprecated(cls, req, resp, member):
        cls.on_put(req, resp, req.context.auth['session']['member_id'])
