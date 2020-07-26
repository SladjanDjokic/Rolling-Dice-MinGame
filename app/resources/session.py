import logging
import app.util.json as json
from app.util.session import get_session_cookie, validate_session
from app.exceptions.session import InvalidSessionError, UnauthorizedSession

logger = logging.getLogger(__name__)

class SessionResource(object):

    # This call needs to only be allowed from the web presentation layer
    def on_get(self, req, resp, session_id):

        try:
            session = validate_session(session_id)
            resp.set_header('X-Auth-Session', session_id)
            resp.body = json.dumps(session, default_parser=json.parser)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err


class ValidateSessionResource(object):

    auth = {
        'exempt_methods': ['GET']
    }

    def on_get(self, req, resp):

        logger.debug('Request Cookies: {}'.format(req.cookies))

        session_id = get_session_cookie(req)

        logger.debug('Session ID: {}'.format(session_id))

        try:
            session = validate_session(session_id)
            resp.set_header('X-Auth-Session', session_id)
            resp.body = json.dumps(session, default_parser=json.parser)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err
