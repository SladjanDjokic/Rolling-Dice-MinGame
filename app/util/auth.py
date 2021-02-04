import logging
import falcon
from app.da.member import MemberDA
from app.da.session import SessionDA
from app.exceptions.session import ForbiddenSession, ForbiddenSessionError, InvalidSessionError, UnauthorizedSession
from app.util.session import get_session_cookie, validate_session


logger = logging.getLogger(__name__)


def validate_token(token):
    return SessionDA.get_session(token)


def validate_session_request(request):
    session_id = get_session_cookie(request)
    if not session_id:
        raise InvalidSessionError()
    session = validate_token(session_id)
    if not session:
        raise InvalidSessionError()

    request.context.auth = {
        "session": session
    }

    return session


def validate_session_administrator(request):
    session = validate_session_request(request)

    logger.debug(f"Resource Class: {cls}")
    logger.debug(f"User Type: {session['user_type']}")

    if session["user_type"] != 'administrator':
        raise ForbiddenSessionError()

    request.context.auth = {
        "admin": session
    }

    return session


def get_session_member_data(request):
    session = validate_session_request(request)
    member = MemberDA.get_member(session['member_id'])

    member["amera_avatar_url"] = session["amera_avatar_url"]
    request.context.auth = {
        "user": member,
        "session": session
    }

    return member


def check_session(func):
    def wrapper(cls, request, response, *args, **kwargs):
        try:
            validate_session_request(request)
            func(cls, request, response, *args, **kwargs)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err
        except ForbiddenSessionError as err:
            raise ForbiddenSession() from err
    return wrapper


def check_session_administrator(func):
    def wrapper(cls, request, response, *args, **kwargs):
        try:
            validate_session_administrator(request)
            func(cls, request, response, *args, **kwargs)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err
        except ForbiddenSessionError as err:
            raise ForbiddenSession() from err
    return wrapper


def inject_member(func):
    def wrapper(cls, request, response, *args, **kwargs):
        try:
            member = get_session_member_data(request)
            func(cls, request, response, member, *args, **kwargs)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err
        except ForbiddenSessionError as err:
            raise ForbiddenSession() from err
    return wrapper
