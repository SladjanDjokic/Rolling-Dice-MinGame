import logging

import app.util.json as json
import app.util.request as request
from app import settings
from app.util.session import get_session_cookie, validate_session
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
from app.da.member_schedule_holiday import MemberScheduleHolidayDA
from app.da.member import MemberDA

logger = logging.getLogger(__name__)


class MemberScheduleHolidayResource(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.holiday_scheduled'),
                                    "topic": settings.get('kafka.topics.calendar')
                                    }
                           }

    @staticmethod
    def on_get(req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            holiday_creator_member_id = session["member_id"]

            search_time_start = req.get_param('search_time_start')
            search_time_end = req.get_param('search_time_end')

            schedule_holidays = MemberScheduleHolidayDA.get_holidays(holiday_creator_member_id, search_time_start,
                                                                     search_time_end)

            resp.body = json.dumps({
                "data": schedule_holidays,
                "success": True
            })

        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

    @staticmethod
    def on_post(req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            holiday_creator_member_id = session["member_id"]
            (holiday_name, holiday_type, holiday_recurrence) = request.get_json_or_form(
                "holiday_name", "holiday_type", "holiday_recurrence", req=req)

            member = MemberDA().get_member(holiday_creator_member_id)
            if not member:
                resp.body = json.dumps({
                    "message": "Member does not exist",
                    "status": "warning",
                    "success": False
                })
                return

            set_params = {
                "holiday_creator_member_id": holiday_creator_member_id,
                "holiday_name": holiday_name,
                "holiday_type": holiday_type,
                "holiday_recurrence": holiday_recurrence
            }

            holiday_id = MemberScheduleHolidayDA().add(**set_params)

            if not holiday_id:
                resp.body = json.dumps({
                    "message": "Holiday adding failed",
                    "status": "warning",
                    "success": False
                })
                return

            resp.body = json.dumps({
                "data": holiday_id,
                "description": "Holiday has been scheduled successfully!",
                "success": True
            })
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err
