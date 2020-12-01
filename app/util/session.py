import logging
from datetime import datetime, timedelta
from pprint import pformat
from urllib.parse import urlparse

from app.da.session import SessionDA
from app.config import settings
from app.exceptions.session import InvalidSessionError


logger = logging.getLogger(__name__)


def set_session_cookie(req, resp, session_id, expiration_datetime=None):
    expiration_seconds = settings.get("web.session_expiratioN")
    if not expiration_datetime:
        expiration_datetime = datetime.now() + timedelta(seconds=expiration_seconds)  # noqa: E501


    # This section here overrides the `access-control-allow-origin`
    # to be dynamic, this means that if the requests come from any
    # domains defined in web.domains, then we allow the origin
    # TODO: Remove this logic
    # request_domain is the domain being used by the original requester
    # we use forwarded_host because these API calls will be proxied in by
    # a load balancer like AWS ELB or NGINX, thus we need to know how
    # this is being requested as:
    #  (e.g. https://ameraiot.com/api/valid-session)
    request_domain = req.env.get('HTTP_ORIGIN', req.forwarded_host)

    # default_domain is the domain as configured in the [web] part of the
    # this domain is the expected domain the application will run in
    # where SSL is terminated, before requests are proxied
    # to the application
    default_domain = settings.get('web.cookie_domain')

    logger.debug(f"SETTINGS Domain: {default_domain}")
    logger.debug(f"REQUEST Forwarded Host: {request_domain}")
    logger.debug(f"REQUEST Host: {req.host}")
    logger.debug(f"REQUEST Access Route: {req.access_route}")
    logger.debug(f"REQUEST Netloc: {req.netloc}")
    logger.debug(f"REQUEST Port: {req.port}")
    # logger.debug(f"ENV: {pformat(req.env)}")

    domains = settings.get("web.domains")
    logger.debug(f"REQUEST_DOMAIN: {request_domain}")
    logger.debug(f"ALLOWED_DOMAINS: {pformat(domains)}")
    domains = next((d for d in domains if d in request_domain), None)
    logger.debug(f"DOMAINS FOUND: {domains}")
    cookie_domain = default_domain
    if domains:
        cookie_domain = domains

    if cookie_domain == "localhost":
        cookie_domain = ""


    logger.debug(f"COOKIE_DOMAIN: {cookie_domain}")
    # TODO: This needs to be more secure
    resp.set_cookie(settings.get("web.cookie_name"), session_id,
                    secure=settings.get("web.cookie_secure"),
                    max_age=expiration_seconds,
                    expires=expiration_datetime,
                    path=settings.get("web.cookie_path"),
                    domain=f"{cookie_domain}")



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
