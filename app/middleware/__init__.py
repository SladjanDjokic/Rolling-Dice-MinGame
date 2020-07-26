import logging
import app.util.json as json
from pprint import pformat
from app.config import settings
from app.util.error import HTTPError

logger = logging.getLogger(__name__)


class CrossDomain(object):
    def process_response(self, req, resp, resource, req_succeeded):

        access_control_allow_origin = settings.get(
            "ACCESS_CONTROL_ALLOW_ORIGIN")
        access_control_allow_methods = settings.get(
            "ACCESS_CONTROL_ALLOW_METHODS")
        access_control_allow_credentials = settings.get(
            "ACCESS_CONTROL_ALLOW_CREDENTIALS")
        access_control_allow_headers = settings.get(
            "ACCESS_CONTROL_ALLOW_HEADERS")

        logger.debug("ACCESS_CONTROL_ALLOW_ORIGIN: {}".format(
            access_control_allow_origin))
        logger.debug("ACCESS_CONTROL_ALLOW_METHODS: {}".format(
            access_control_allow_methods))
        logger.debug("ACCESS_CONTROL_ALLOW_CREDENTIALS: {}".format(
            access_control_allow_credentials))
        logger.debug("ACCESS_CONTROL_ALLOW_HEADERS: {}".format(
            access_control_allow_headers))

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
        default_domain = settings.get('web.domain')

        logger.debug("SETTINGS Domain: {}".format(default_domain))
        logger.debug("REQUEST Forwarded Host: {}".format(request_domain))
        logger.debug("REQUEST Host: {}".format(req.host))
        logger.debug("REQUEST Access Route: {}".format(req.access_route))
        logger.debug("REQUEST Netloc: {}".format(req.netloc))
        logger.debug("REQUEST Port: {}".format(req.port))
        logger.debug("ENV: {}".format(pformat(req.env)))

        if access_control_allow_origin == "auto":
            domains = settings.get("web.domains")
            logger.debug("REQUEST_DOMAIN: {}".format(request_domain))
            logger.debug("ALLOWED_DOMAINS: {}".format(pformat(domains)))
            domains = [d for d in domains if d in request_domain]
            logger.debug("DOMAINS FOUND: {}".format(domains))
            if len(domains) == 0:
                access_control_allow_origin = default_domain
            else:
                access_control_allow_origin = request_domain
            logger.debug("OVERRIDE_ACCESS_CONTROL_ALLOW_ORIGIN: {}".format(
                access_control_allow_origin))

        resp.set_header("Access-Control-Allow-Origin",
                        access_control_allow_origin)
        resp.set_header("Access-Control-Allow-Methods",
                        access_control_allow_methods)
        resp.set_header("Access-Control-Allow-Credentials",
                        access_control_allow_credentials)
        resp.set_header("Access-Control-Allow-Headers",
                        access_control_allow_headers)


class JSONTranslator(object):
    def process_request(self, req, resp):
        if req.content_length in (None, 0):
            return

        body = req.stream.read()
        if not body:
            raise HTTPError(400, "A valid JSON document is required.")

        try:
            req.context["doc"] = json.loads(body.decode("utf-8"))

        except (ValueError, UnicodeDecodeError):
            raise HTTPError(400, "Could not decode the request body. The "
                                 "JSON was incorrect or not encoded as "
                                 "UTF-8.")

    def process_response(self, req, resp, resource, req_succeeded):
        if "result" not in req.context:
            return

        resp.body = json.dumps(req.context["result"])
