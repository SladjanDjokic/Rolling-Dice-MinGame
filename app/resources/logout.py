from app.util.session import invalidate_session_cookie
from falcon.status_codes import HTTP_200
from app.util.auth import check_session
from app import settings
from app.da.session import SessionDA
from app.exceptions.session import ForbiddenSession, InvalidSession, \
    InvalidSessionError
from falcon import HTTP_OK


post_event_type = settings.get('kafka.event_types.post.member_logout')
get_event_type = settings.get('kafka.event_types.post.member_logout')


class MemberLogoutResource(object):

    def __init__(self):
        self.kafka_data = {
            "POST": {
                "event_type": post_event_type,
                "topic": settings.get('kafka.topics.auth')
            },
            "GET": {
                "event_type": get_event_type,
                "topic": settings.get('kafka.topics.auth')
            }
        }

    auth = {
        'exempt_methods': ['POST']
    }

    @check_session
    def on_post(self, req, resp, member_id, session_id):
        self._logout(req, resp, member_id, session_id)

    @check_session
    def on_get(self, req, resp, member_id, session_id):
        self._logout(req, resp, member_id, session_id)

    @staticmethod
    def _logout(req, resp, member_id=None, session_id=None):
        if not member_id or not session_id:
            raise ForbiddenSession()

        if member_id != req.context.auth['session']['member_id']:
            raise ForbiddenSession()

        if session_id.hex != req.context.auth['session']['session_id']:
            raise ForbiddenSession()

        try:
            SessionDA.disable_session(
                session_id.hex,
                member_id
            )
            invalidate_session_cookie(req, resp)
        except InvalidSessionError as err:
            raise InvalidSession from err

        resp.body = None
        resp.status = HTTP_OK
