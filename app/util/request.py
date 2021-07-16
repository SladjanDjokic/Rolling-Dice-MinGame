import logging
import socket
from pprint import pformat
from urllib.parse import urlunsplit, urljoin, urlsplit
from falcon import uri
from app.config import settings


logger = logging.getLogger(__name__)


# This is a utility function, possibly a hack to support web forms
# And support JSON API's
# does not support extra parameters to `get_param`
def get_json_or_form(*params, req):
    results = []

    logger.debug("Comparing Content-Type: {}".format(req.content_type))
    func = lambda x: x
    if req.content_type and "form-data" in req.content_type:
        # This will parse the content-type of multipart/form-data
        # but it will not parse application/x-www-form-urlencoded
        logger.debug("Using Request.get_param for form-data")
        func = req.get_param
    elif req.content_type and "x-www-form-urlencoded" in req.content_type:
        # This will parse the content-type of application/x-www-form-urlencoded
        # but it will not parse form-data or any other content-type
        # this has to be done manually as is until version 3 of Falcon
        logger.debug("Using Request.stream.read and parsing for form-urlencoded")
        data = req.stream.read(req.content_length or 0)
        data = uri.parse_query_string(uri.decode(data.decode("utf-8")))
        func = data.get
    elif req.media and req.media.get:
        logger.debug("Using Request.media.get")
        func = req.media.get

    for param in params:
        results.append(func(param))

    return results


def get_request_host(req):
    host = req.host
    if host == 'localhost':
        host = req.env.get(
            'HTTP_ORIGIN', req.env.get(
                'HTTP_X_FORWARDED_HOST_ORIGINAL',
                req.forwarded_host or req.host))
    # else:
    #     try:
    #         request_host = _get_request_domain(req)[1][1]
    #         if request_host:
    #             host = request_host
    #     except:
    #         logger.debug(f'_get_request_domain unexpected response')
    #         logger.debug(_get_request_domain(req))

    return host


def get_request_scheme(req):
    scheme = 'https'
    if req.forwarded_scheme:
        scheme = req.forwarded_scheme

    # try:
    #     request_scheme = _get_request_domain(req)[1][0]
    #     if request_scheme:
    #         scheme = request_scheme
    # except:
    #     logger.debug(f'_get_request_domain unexpected response')
    #     logger.debug(_get_request_domain(req))

    return scheme


def build_url_from_request(req, path="", query="", fragment=""):
    parts = (
        get_request_scheme(req),
        get_request_host(req),
        path,
        query,
        fragment
    )
    logger.debug(f'URL Parts: {parts}')
    return urlunsplit(parts)

def get_url_base(req):
    scheme = get_request_scheme(req)
    host = get_request_host(req)
    return '{}://{}'.format(scheme, host)


def get_request_client_data(req):
    # https://falcon.readthedocs.io/en/stable/api/request_and_response.html#falcon.Request.access_route
    # access_route gives us a list of values based on the number
    # of hops the request took to get to our application
    # This is done by analyzing:
    # - Forwarded
    # - X-Forwarded-For
    # - X-Real-IP
    logger.debug(f"Headers:")
    logger.debug(req.headers)
    logger.debug(f"Access Route: {req.access_route}")
    logger.debug(f"Remote Addr: {req.remote_addr}")
    logger.debug(f"Forwarded header: {req.forwarded}")

    access_route = iter(req.access_route)

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For
    # We know that the very first value of access_route is the actual client IP
    # any further IP are proxies, we only care about the outer most proxy
    client_ip = next(access_route, "")
    gateway_ip = next(access_route, "")

    # If we do not have a Client IP, we have no access routes
    # Therefore, access_route should default to `remote_addr`
    # in the event that it doesn't, we will force it here to both the client and gateway
    if not client_ip:
        client_ip = req.remote_addr
        gateway_ip = req.remote_addr

    # Let's get DNS information
    client_name = None
    try:
        client_name = next(iter(socket.gethostbyaddr(client_ip)))
    except socket.herror:
        pass
    except TypeError:
        pass
    except Exception:
        pass

    gateway_name = None
    try:
        gateway_name = next(iter(socket.gethostbyaddr(gateway_ip)))
    except socket.herror:
        pass
    except TypeError:
        pass
    except Exception:
        pass

    # Let's get server information
    server_name1 = socket.gethostname()
    server_ip1 = socket.gethostbyname(server_name1)
    server_name2 = socket.getfqdn()
    server_ip2 = socket.gethostbyname(server_name2)

    # https://falcon.readthedocs.io/en/stable/api/request_and_response.html#falcon.Request.forwarded_uri
    # We are going to use a variety of mechanisms to retrieve the original
    # requested URL
    logger.debug(f'Request: {pformat(req.env)}')
    logger.debug(f"URI: {req.uri}")
    logger.debug(f"URL: {req.url}")
    logger.debug(f"Forwarded: {req.forwarded_uri}")
    logger.debug(f"Relative: {req.relative_uri}")
    logger.debug(f"Prefix: {req.prefix}")
    logger.debug(f"Forwarded Prefix: {req.forwarded_prefix}")

    original_url = req.forwarded_uri or req.url
    query_string = req.query_string

    return client_ip, gateway_ip, original_url, query_string,\
        client_name, gateway_name, server_name1, server_ip1,\
        server_name2, server_ip2

def _get_request_domain(req):
    request_domain = req.env.get('HTTP_ORIGIN', req.forwarded_host)
    return request_domain, urlsplit(request_domain)


def _get_register_url(req, invite_key):
    request_domain = _get_request_domain(req)[0]
    register_domain = request_domain
    logger.debug(f"REGISTER DOMAIN: {register_domain}")

    register_url = "/registration/{}".format(invite_key)
    register_url = urljoin(register_domain, register_url)
    return register_url
