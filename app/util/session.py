from datetime import datetime, timedelta

from app.da.session import SessionDA
from app.config import settings
from app.exceptions.session import InvalidSessionError


def set_session_cookie(resp, session_id, expiration_datetime=None):
    expiration_seconds = settings.get("web.session_expiratioN")
    if not expiration_datetime:
        expiration_datetime = datetime.now() + timedelta(seconds=expiration_seconds)  # noqa: E501

    # TODO: This needs to be more secure
    resp.set_cookie(settings.get("web.cookie_name"), session_id,
                    secure=settings.get("web.cookie_secure"),
                    max_age=expiration_seconds,
                    expires=expiration_datetime,
                    path=settings.get("web.cookie_path"),
                    domain=settings.get("web.cookie_domain"))


def get_session_cookie(req):
    cookies = req.cookies
    return cookies.get(settings.get("web.cookie_name"))


def validate_session(session_id):

    if not session_id:
        raise InvalidSessionError()

    session = SessionDA.get_session(session_id)
    if not session:
        raise InvalidSessionError()

    return session
