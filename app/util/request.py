import logging
from falcon import uri

logger = logging.getLogger(__name__)


# This is a utility function, possibly a hack to support web forms
# And support JSON Api's
# does not support extra parameters to `get_param`
def get_json_or_form(*params, req):
    results = []

    logger.debug("Comparing Content-Type: {}".format(req.content_type))

    if "form-data" in req.content_type:
        # This will parse the content-type of multipart/form-data
        # but it will not parse application/x-www-form-urlencoded
        logger.debug("Using Request.get_param for form-data")
        func = req.get_param
    elif "x-www-form-urlencoded" in req.content_type:
        # This will parse the content-type of application/x-www-form-urlencoded
        # but it will not parse form-data or any other content-type
        # this has to be done manually as is until version 3 of Falcon
        logger.debug("Using Request.stream.read and parsing for form-urlencoded")
        data = req.stream.read(req.content_length or 0)
        data = uri.parse_query_string(uri.decode(data.decode("utf-8")))
        func = data.get
    else:
        logger.debug("Using Request.media.get")
        func = req.media.get

    for param in params:
        results.append(func(param))

    return results


def get_url_base(req):
    scheme = 'https'
    if req.forwarded_scheme:
        scheme = req.forwarded_scheme

    host = req.host
    return '{}://{}'.format(scheme, host)
