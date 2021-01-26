import logging
import falcon
from app.da.member import MemberDA
from app.da.session import SessionDA
from app.exceptions.session import ForbiddenSession, InvalidSessionError, UnauthorizedSession
from app.util.session import get_session_cookie, validate_session


logger = logging.getLogger(__name__)


def validate_token(token):
    return SessionDA.get_session(token)


def get_logged_in_member(request):
    try:
        session_id = get_session_cookie(request)
        session = validate_session(session_id)
        event_host_member_id = session["member_id"]

        member = MemberDA.get_member(event_host_member_id)
        if not member:
            raise InvalidSessionError
        member["amera_avatar_url"] = session["amera_avatar_url"]
        request.context.auth = {
            "user": member,
            "session": session
        }

    except InvalidSessionError as err:
        raise UnauthorizedSession() from err
    return member


def inject_member(func):
    def wrapper(cls, request, response, *args, **kwargs):
        member = get_logged_in_member(request)
        func(cls, request, response, member, *args, **kwargs)
    return wrapper


def check_role_administrator(func):
    def wrapper(cls, request, response, *args, **kwargs):
        try:
            session_id = get_session_cookie(request)
            if not session_id:
                raise InvalidSessionError()
            session = validate_token(session_id)
            if not session:
                raise InvalidSessionError()

            logger.debug(f"Resource Class: {cls}")
            logger.debug(f"User Type: {session['user_type']}")

            if session["user_type"] != 'administrator':
                raise ForbiddenSession()

            request.context.auth = {
                "admin": session
            }
            func(cls, request, response, *args, **kwargs)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err
    return wrapper
