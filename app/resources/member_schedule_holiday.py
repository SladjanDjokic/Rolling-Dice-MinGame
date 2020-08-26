import logging
from datetime import timezone, datetime

import app.util.json as json
import app.util.request as request
from app.util.session import get_session_cookie, validate_session
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
from app.da.member_schedule_holiday import MemberScheduleHolidayDA
from app.da.member import MemberDA
from app.exceptions.member import MemberNotFound

logger = logging.getLogger(__name__)


class MemberScheduleHolidayResource(object):

    def on_post(self, req, resp):

        [holiday_creator_member_id] = request.get_json_or_form("holiday_creator_member_id", req=req)

        [search_time_start] = request.get_json_or_form("search_time_start", req=req)
        [search_time_end] = request.get_json_or_form("search_time_end", req=req)
                      
        schedule_holidays = MemberScheduleHolidayDA.get_holidays(holiday_creator_member_id, search_time_start, search_time_end)

        resp.body = json.dumps({
            "data": schedule_holidays,
            "success": True
        })
   

class MemberScheduleHolidayAddResource(object):
    def on_post(self, req, resp):

        (holiday_creator_member_id, holiday_name, holiday_type, holiday_recurrence) = request.get_json_or_form(
            "holiday_creator_member_id", "holiday_name", "holiday_type", "holiday_recurrence", req=req)

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

        id = MemberScheduleHolidayDA().add(**set_params)
        
        if not id:
            resp.body = json.dumps({
                "message": "Holiday adding failed",
                "status": "warning",
                "success": False
            })
            return

        resp.body = json.dumps({
            "data": id,
            "description": "Holiday has been scheduled successfully!",
            "success": True
        })
