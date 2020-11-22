import app.util.json as json
from app.da.file_sharing import FileStorageDA
from app.da.avatar import AvatarDA
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
from app.util.session import get_session_cookie, validate_session
import logging

logger = logging.getLogger(__name__)


class AvatarResource(object):
    @staticmethod
    def on_put(req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            avatar = req.get_param('avatar')
            avatar_storage_id = FileStorageDA().put_file_to_storage(avatar)
            # avatar_storage_id = FileStorageDA().store_file_to_storage(avatar)

            success = AvatarDA.update_avatar(avatar_storage_id, member_id)

            if success:

                resp.body = json.dumps({
                    "data": AvatarDA.get_avatar_url(member_id),
                    "success": True
                }, default_parser=json.parser)

        except InvalidSessionError as err:
            raise UnauthorizedSession() from err
