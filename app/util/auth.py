from app.da.member import MemberDA
from app.da.session import SessionDA
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
from app.util.session import get_session_cookie, validate_session


def validate_token(token):
    return SessionDA.get_session(token)


def inject_member(func):
    def wrapper(cls, request, response, *args, **kwargs):
        try:
            session_id = get_session_cookie(request)
            session = validate_session(session_id)
            event_host_member_id = session["member_id"]

            member = MemberDA.get_member(event_host_member_id)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

        func(cls, request, response, member, *args, **kwargs)
    return wrapper
