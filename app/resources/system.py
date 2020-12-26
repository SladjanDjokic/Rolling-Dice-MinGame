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

logger = logging.getLogger(__name__)


class SystemActivityResource(object):
    def __init__(self, resource):
        self.resource = resource

    def on_get(self, req, resp):
        get_all = req.get_param_as_bool('get_all')
        session_id = get_session_cookie(req)
        session = validate_session(session_id)

        if get_all and session["user_type"] is 'administrator':
            raise falcon.HTTPForbidden(description="Not enough permissions")

        search_key = req.get_param('search_key') or ''
        page_size = req.get_param_as_int('page_size')
        page_number = req.get_param_as_int('page_number')

        sort_params = req.get_param('sort')

        get_func = SessionDA.get_sessions if self.resource is "sessions" else InviteDA.get_invites

        result = get_func(search_key, page_size, page_number, sort_params, get_all, session["member_id"])

        resp.body = json.dumps({
            'activities': result['activities'],
            'count': result['count'],
            'success': True
        }, default_parser=json.parser)
