from app.exceptions.member import MemberNotFound
from app.da.member import MemberDA
from app.exceptions.session import InvalidSession, \
    InvalidSessionError
from app.util.auth import check_session_administrator
import logging

import app.util.json as json
from app import settings

from app.da.session import SessionDA

logger = logging.getLogger(__name__)


class AdminMemberResource(object):

    def __init__(self) -> None:
        self.kafka_data = {
            "DELETE": {
                "uri": {
                    "/admin/member/{member_id:int}/session/{session_id:uuid}": {
                        "event_type": settings.get('kafka.event_types.delete.admin_member_disable_session'),
                        "topic": settings.get('kafka.topics.member')
                    },
                    "/admin/member/{member_id:int}": {
                        "event_type": settings.get('kafka.event_types.delete.admin_member_disable'),
                        "topic": settings.get('kafka.topics.member')
                    },
                }
            },
        }

    @check_session_administrator
    def on_delete_session(self, req, resp, session_id, member_id):

        try:
            # status = 'disabled'
            # id = MemberDA.update_member_status(member_id, status)
            session_id, member_id = SessionDA.disable_session(
                session_id.hex, member_id)

            resp.body = json.dumps({
                "session_id": session_id,
                "member_id": member_id,
                "success": True
            }, default_parser=json.parser)

        except InvalidSessionError as err:
            raise InvalidSession() from err

    @check_session_administrator
    def on_delete_member(self, req, resp, member_id, full=False):

        try:
            status = 'disabled'
            id = MemberDA.update_member_status(member_id, status)
            sessions = SessionDA.disable_online_session(member_id)

            if not id:
                raise MemberNotFound(member_id)

            resp.body = json.dumps({
                "member_id": id,
                "sessions": [s["session_id"] for s in sessions],
                "success": True
            })

        except MemberDataMissing:
            raise MemberDataMissing()
        except Exception as err:
            logger.exception('Unknown error')
            logger.debug(err)
            raise err
