import logging
from datetime import timezone, datetime

import app.util.json as json
import app.util.request as request
from app.util.session import get_session_cookie, validate_session
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
from app.da.member_scheduler_setting import MemberSchedulerSettingDA
from app.exceptions.member_scheduler_setting import SchedulerSettingNotFound, SchedulerSettingSavingFailed
from app.da.member import MemberDA
from app.exceptions.member import MemberNotFound

logger = logging.getLogger(__name__)


class MemberSchedulerSettingResource(object):

    def on_post(self, req, resp):

        [member_id] = request.get_json_or_form("member_id", req=req)
                      
        scheduler_setting = MemberSchedulerSettingDA.get_setting(member_id)

        if not scheduler_setting:
            raise SchedulerSettingNotFound(scheduler_setting)

        resp.body = json.dumps({
            "data": scheduler_setting,
            "success": True
        })
   

class MemberSchedulerSettingUpdateResource(object):
    def on_post(self, req, resp):

        (member_id, date_format, time_format, start_time, time_interval, start_day, drag_method) = request.get_json_or_form(
            "member_id", "date_format", "time_format", "start_time", "time_interval", "start_day", "drag_method", req=req)

        member = MemberDA().get_member(member_id)
        if not member:
            raise MemberNotFound(member_id)

        set_params = {
            "member_id": member_id,
            "date_format": date_format,
            "time_format": time_format,
            "start_time": start_time,
            "time_interval": time_interval,
            "start_day": start_day,
            "drag_method": drag_method           
        }

        id = MemberSchedulerSettingDA().set(**set_params)
        
        if not id:
            raise SchedulerSettingSavingFailed()

        resp.body = json.dumps({
            "data": id,
            "description": "Scheduler setting has been set successfully!",
            "success": True
        })
