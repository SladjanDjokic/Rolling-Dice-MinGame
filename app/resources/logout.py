from app.util.auth import inject_member
import uuid
import falcon
import app.util.json as json
import app.util.request as request
from app import settings
from app.da.session import SessionDA
from app.exceptions.session import ForbiddenSession, SessionExistsError


class MemberLogoutResource(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.member_logout'),
                                    "topic": settings.get('kafka.topics.auth')
                                    }
                           }

    auth = {
        'exempt_methods': ['POST']
    }

    @inject_member
    def on_post(self, req, resp, member):

        (member_id, session_id) = request.get_json_or_form(
            "member_id", "session_id", req=req)

        if not member_id or not session_id:
            raise ForbiddenSession()

        if member_id != member['member_id']:
            raise ForbiddenSession()

        if session_id != req.context.auth['session']['session_id']:
            raise ForbiddenSession()

        while True:
            try:
                SessionDA.disable_session(
                    session_id,
                    member['member_id']
                )
                break
            except SessionExistsError:
                continue

        resp.body = json.dumps({
        })

    def on_get(self, req, resp):
        resp.body = json.dumps({
        })
