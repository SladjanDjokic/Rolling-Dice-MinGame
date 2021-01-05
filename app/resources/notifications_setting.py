import logging
import json
import falcon
import app.util.request as request
from app.util.session import get_session_cookie, validate_session

from app.da.member import MemberNotificationsSettingDA

logger = logging.getLogger(__name__)

class MemberNotificationsSetting(object):
    @staticmethod
    def on_put(req, resp):
        (notifications_setting) = request.get_json_or_form("notifications_setting", req=req)

        session_id = get_session_cookie(req)
        session = validate_session(session_id)
        member_id = session["member_id"]
        
        try:
            notifications_setting = json.dumps(notifications_setting[0])
            result = MemberNotificationsSettingDA.update_notifications_setting(member_id, notifications_setting)
            if result:
                resp.body = json.dumps({
                    "message": "notifications setting updated.",
                    "success": True
                })
            else:
                resp.body = json.dumps({
                    "message": "failed to update notifications setting.",
                    "success": False
                })
        except:
            logger.exception('Failed to update member notifications setting.')
            resp.status = falcon.HTTP_500

    @staticmethod
    def on_get(req, resp):
        session_id = get_session_cookie(req)
        session = validate_session(session_id)
        member_id = session["member_id"]
        
        try:
            result = MemberNotificationsSettingDA.get_notifications_setting(member_id, )
            if result:
                resp.body = json.dumps({
                    "data": result,
                    "message": "Got Notifications Setting.",
                    "success": True
                })
            else:
                 resp.body = json.dumps({
                    "data": {},
                    "message": "Failed to get Notifications Setting.",
                    "success": False
                })
        except:
            logger.exception('Failed to get member notifications setting.')
            resp.status = falcon.HTTP_500
