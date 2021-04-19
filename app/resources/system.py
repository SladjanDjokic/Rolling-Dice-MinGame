import uuid
import logging
import falcon
from datetime import timezone, datetime
from dateutil.relativedelta import relativedelta
from urllib.parse import urljoin

import app.util.json as json
import app.util.request as request
import app.util.email as sendmail
from app.util.session import get_session_cookie, validate_session

from app.config import settings
from app.da.invite import InviteDA
from app.da.session import SessionDA
from app.da.activity import ActivityDA
from app.da.member import MemberDA

logger = logging.getLogger(__name__)


class SystemActivityResource(object):
    def __init__(self, resource):
        self.resource = resource

    def on_get(self, req, resp):
        get_all = req.get_param_as_bool('get_all')
        session_id = get_session_cookie(req)
        session = validate_session(session_id)

        logger.debug(f"User Type: {session['user_type']}")
        logger.debug(f"Resource: {self.resource}")

        if get_all and session["user_type"] != 'administrator':
            raise falcon.HTTPForbidden(description="Not enough permissions")

        search_key = req.get_param('search_key') or ''
        page_size = req.get_param_as_int('page_size')
        page_number = req.get_param_as_int('page_number')
        sort_params = req.get_param('sort')
        member_id = session["member_id"]

        if self.resource == "invites":
            get_func = InviteDA.get_invites
        elif self.resource == "threats":
            get_func = SessionDA.get_threats
        elif self.resource == "behaviour":
            member_id = req.get_param('member_id')
            if member_id == 'undefined':
                member_id = None
            get_func = ActivityDA().get_user_global_behaviour
        else:
            get_func = SessionDA.get_sessions
        
        result = get_func(search_key, page_size, page_number, sort_params, get_all, member_id)
        
        resp.body = json.dumps({
            'activities': result['activities'],
            'count': result['count'],
            'success': True
        }, default_parser=json.parser)

class SystemActivityUsersResource(object):
    def on_get(self, req, resp):
        get_all = req.get_param_as_bool('get_all')
        member_id = req.get_param('member_id')
        session_id = get_session_cookie(req)
        session = validate_session(session_id)

        logger.debug(f"User Type: {session['user_type']}")

        if get_all and session["user_type"] != 'administrator':
            raise falcon.HTTPForbidden(description="Not enough permissions")
        
        result = ActivityDA().get_recent_activity_users(get_all)
        
        resp.body = json.dumps({
            'users': result,
            'success': True
        }, default_parser=json.parser)


class SystemMemberResource(object):
    def on_get(self, req, resp):
        try:
            get_all = req.get_param_as_bool('get_all')
            session_id = get_session_cookie(req)
            session = validate_session(session_id)

            logger.debug(f"User Type: {session['user_type']}")

            if get_all and session["user_type"] != 'administrator':
                raise falcon.HTTPForbidden(description="Not enough permissions")

            search_key = req.get_param('search_key') or ''
            page_size = req.get_param_as_int('page_size')
            page_number = req.get_param_as_int('page_number')
            sort_params = req.get_param('sort')
            member_id = session["member_id"]

            result = MemberDA.get_members(member_id, search_key, page_size, page_number, sort_params, all_members=True)
            
            resp.body = json.dumps({
                "data": result,
                "description": "Successfully loaded.",
                "success": True
            }, default_parser=json.parser)

        except Exception as e:
            resp.body = json.dumps({
                "data": {},
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)