from app.da.member import MemberDA
from app.da.session import SessionDA
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
from app.util.session import get_session_cookie, validate_session


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
    except InvalidSessionError as err:
        raise UnauthorizedSession() from err
    return member


def inject_member(func):
    def wrapper(cls, request, response, *args, **kwargs):
        member = get_logged_in_member(request)
        func(cls, request, response, member, *args, **kwargs)
    return wrapper
