import copy
import logging
from datetime import datetime, timezone

import falcon
import uuid
from confluent_kafka import Producer

# from app.tasks.main import producer_async
# from app.events.publishers.publisher import producer_async

import gevent

import app.util.json as json
from pprint import pformat
from app.config import settings
from app.events.publishers.publisher import BaseProducer
from app.exceptions.session import UnauthorizedSession, InvalidSessionError
from app.util.error import HTTPError
from app.util.session import get_session_cookie, validate_session
from app.da.activity import ActivityDA

logger = logging.getLogger(__name__)

# Topic route table based on resource and method.
# TODO move this to env file or vyper
# TODO add event type to resource dict as well
topic_routes = {"MemberScheduleEventResource": {"GET": {"event_type": "check_calendar", "topic": "calendar"},
                                                "POST": {"event_type": "create_event", "topic": "calendar"}},
                "MemberLoginResource": {"GET": {"event_type": "login", "topic": "login"},
                                        "POST": {"event_type": "login", "topic": "login"}},

                "MemberForgotPasswordResource": {"GET": {"event_type": "check_calendar", "topic": "calendar"},
                                                 "POST": {"event_type": "create_event", "topic": "calendar"}},

                }


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


class TopicData(object):
    """ Model for topic data for kafka and activity query"""

    def __init__(self):
        self.event_key = ""
        self.headers = {}
        self.req_params = {}
        self.req_url_params = {}
        self.req_data = {}
        self.resp_data = {}
        self.http_status = 0
        self.session_key = ""
        self.session_data = {}
        self.member_id = ""
        self.event_type = ""
        self.status = "started"
        self.create_date = ""


class KafkaProducerMiddleware(object):

    def __init__(self):

        producer_conf = {
            'bootstrap.servers': settings.get('kafka.bootstrap_servers')
        }

        if settings.get('kafka.sasl.username'):
            producer_conf.update({
                'sasl.mechanisms': settings.get('kafka.sasl.mechanisms'),
                'security.protocol': settings.get('kafka.security.protocol'),
                'sasl.username': settings.get('kafka.sasl.username'),
                'sasl.password': settings.get('kafka.sasl.password'),
            })

        self.topic = None
        self.session_id = ""
        self.session_data = ""
        self.member_id = ""
        self.u = ""
        self.topic_data = TopicData()
        self.db_query_data = {}
        self.p = Producer(producer_conf)
        # self.p = Producer({
        #     'bootstrap.servers': 'kafka:9092'
        # })

    def process_request(self, req, resp):

        return

    def process_resource(self, req, resp, resource, params):
        # Topics determined by resource as http method
        r = topic_routes.get(resource.__class__.__name__)
        if r:
            self.topic = r.get(req.method).get('topic')
            self.topic_data.event_type = r.get(req.method).get('event_type')
        if not self.topic:
            # If no specific topic necessary. Send all other data to activity topic for monitoring purposes
            self.topic = "activity"
            self.topic_data.event_type = "activity"

        try:
            session_key = get_session_cookie(req)
            try:
                self.topic_data.session_key = session_key
                self.topic_data.session_data = validate_session(session_key, full=True)
                self.topic_data.member_id = self.topic_data.session_data["member_id"]
            except InvalidSessionError:
                self.topic_data.session_data = {}
                self.topic_data.member_id = None

            body = None
            # TODO Does this get all body types?
            if req.content_type == falcon.MEDIA_JSON:
                body = req.media
            self.u = str(uuid.uuid4())
            self.topic_data.event_key = self.u
            self.topic_data.headers = req.headers
            self.topic_data.req_params = req.params
            self.topic_data.req_url_params = params
            self.topic_data.req_data = body
            self.topic_data.headers = self._sanitize(req.headers)
            self.topic_data.req_params = self._sanitize(req.params)
            self.topic_data.req_url_params = self._sanitize(params)
            self.topic_data.req_data = self._sanitize(body)
            self.topic_data.resp_data = None
            # TODO add query for event from Topic/Resource dict
            self.topic_data.create_date = datetime.now(timezone.utc)

            # Gevent to not block request. Create dict from topic_data model for kafka
            topic_data_dict = vars(self.topic_data)
            #gevent.spawn(self.producer_async(self.topic,
            #                                 [json.dumps(topic_data_dict, default_parser=json.parser)]))

            logger.debug(f"### After kafka {type(self.topic_data.headers)}")
            # Write activity to db - copy topic data to preserve json
            self.db_query_data = copy.deepcopy(topic_data_dict)
            self.db_query_data['headers'] = json.dumps(self.topic_data.headers, default_parser=json.parser)
            self.db_query_data["req_params"] = json.dumps(self.topic_data.req_params, default_parser=json.parser)
            self.db_query_data["req_url_params"] = json.dumps(self.topic_data.req_url_params,
                                                           default_parser=json.parser)
            self.db_query_data["req_data"] = json.dumps(self.topic_data.req_data, default_parser=json.parser)
            self.db_query_data["resp_data"] = json.dumps(self.topic_data.resp_data, default_parser=json.parser)
            self.db_query_data["session_data"] = json.dumps(self.topic_data.session_data,
                                                            default_parser=json.parser)


            logger.debug(f"### After JSON DUMP QUERY {type(self.topic_data.headers)}")

            logger.debug("### REQUEST")
            ActivityDA.insert_activity(**self.db_query_data)
        except Exception as e:
            logger.error(e, exc_info=True)

        return

    def process_response(self, req, resp, resource, req_succeeded):
        try:
            if not self.topic:
                self.topic = "activity"
            self.topic_data.http_status = resp.status

            # Capture invalid sessions so we can still log it
            # send none for session and member
            try:
                self.topic_data.session_data = validate_session(self.session_id)
            except InvalidSessionError:
                self.topic_data.session_data = {}
                self.topic_data.member_id = None

            self.topic_data.status = "ended"
            body = json.loads(resp.body)
            body = None
            try:
                body = json.loads(resp.body)
            except Exception as e:
                # Response is non json, do nothing
                pass

            self.topic_data.resp_data = body
            self.topic_data.create_date = datetime.now(timezone.utc)

            # Gevent kafka producer
            logger.debug("### Kafka")
            logger.debug(vars(self.topic_data))
            #gevent.spawn(self.producer_async(self.topic, [json.dumps(vars(self.topic_data),
            #                                                         default_parser=json.parser)]))

            # convert dicts to json for db query
            self.db_query_data['resp_data'] = json.dumps(self.topic_data.resp_data,
                                                         default_parser=json.parser)
            logger.debug("### Response")
            ActivityDA.insert_activity(**self.db_query_data)
            # gevent.spawn(ActivityDA.insert_activity(**self.topic_data))

        except Exception as e:
            logger.error(e, exc_info=True)

        return

    def producer_async(self, topic, data_source):
        # create_topic(self.topic)
        for data in data_source:
            # Poll will trigger the callback self.deliver_report which indicates if the message has
            # successfully been delivered. Not sure if this means a consumer has read it or its been successfully
            # been delivered to a client
            self.p.poll(0)

            # Asynchronously produce a message, the delivery report callback
            # will be triggered from poll() above, or flush() below, when the message has
            # been successfully delivered or failed permanently.
            try:
                self.p.produce(topic, value=data.encode('utf-8'), callback=self.delivery_report)
            except Exception as exc:
                logger.exception(exc, exc_info=True)

        # Wait for any outstanding messages to be delivered and delivery report
        # callbacks to be triggered.
        self.p.flush()

    @staticmethod
    def _sanitize(data):
        if not data:
            return data

        data = data.copy()  # Copying to not modify the original data for the resources
        for key in data.keys():
            if 'password' in key:
                data[key] = '**********'
        return data

    @staticmethod
    def delivery_report(err, msg):
        """ Called once for each message produced to indicate delivery result.
            Triggered by poll() or flush(). """
        if err is not None:
            logger.debug('Message delivery failed: {}'.format(err))
        else:
            logger.debug('Message delivered to {} [{}] {}'.format(msg.topic(), msg.partition(), msg.value()))
