from app.util.auth import check_session
import logging
import falcon
import app.util.json as json

import app.util.request as request
from app import settings
from app.util.session import get_session_cookie, validate_session
from app.da.member import MemberDA
from app.da.session import SessionDA
from app.exceptions.member import MemberNotFound, MemberDisabled, PasswordsConflict
from app.exceptions.session import SessionExistsError

logger = logging.getLogger(__name__)


class MemberChangePasswordResource(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.member_change_password'),
                                    "topic": settings.get('kafka.topics.member')
                                    },
                           }

    @check_session
    def on_post(self, req, resp):
        (current_password, new_password) = request.get_json_or_form(
            "currentPassword", "newPassword", req=req)

        if not current_password or not new_password:
            raise falcon.HTTPError("400",
                                    title="Invalid Password",
                                    description="Please Provide Information.")

        if new_password == current_password:
            raise PasswordsConflict()

        member_id = req.context.auth["session"]["member_id"]

        member = MemberDA.get_member(member_id)
        if not member:
            raise MemberNotFound(member_id)

        username = member.get('username')
        member = SessionDA.auth(username, current_password)
        if not member:
            raise MemberNotFound(username)

        if member['status'] == 'disabled':
            raise MemberDisabled()

        member_id = member['id']
        MemberDA.update_member_password(member_id, new_password)

        resp.body = json.dumps({
          "success": True
        })
