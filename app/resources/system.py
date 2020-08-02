import uuid
import logging
from datetime import timezone, datetime
from dateutil.relativedelta import relativedelta
from urllib.parse import urljoin

import app.util.json as json
import app.util.request as request
import app.util.email as sendmail

from app.config import settings
from app.da.invite import InviteDA
from app.da.session import SessionDA

logger = logging.getLogger(__name__)

class SystemActivitySessionResource(object):

    def on_get(self, req, resp):

        invite = req.get_param_as_bool('invite')

        search_key = req.get_param('search_key')
        page_size = req.get_param_as_int('page_size')
        page_number = req.get_param_as_int('page_number')

        if search_key is None:
            search_key = ''

        result = SessionDA.get_sessions(search_key, page_size, page_number)

        resp.body = json.dumps({
            'activities': result['activities'],
            'count': result['count'],
            'success': True
        }, default_parser=json.parser)

class SystemActivityInviteResource(object):

    def on_get(self, req, resp):

        search_key = req.get_param('search_key')
        page_size = req.get_param_as_int('page_size')
        page_number = req.get_param_as_int('page_number')

        if search_key is None:
            search_key = ''

        result = InviteDA.get_invites(search_key, page_size, page_number)

        resp.body = json.dumps({
            'activities': result['activities'],
            'count': result['count'],
            'success': True
        }, default_parser=json.parser)
