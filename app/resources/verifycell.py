# Recovered for compatibility

import app.util.json as json
import app.util.request as request
from app.da.verification import VerificationDA
from app.config import settings
from app.util.auth import check_session, check_session_pass
import falcon
import logging

logger = logging.getLogger(__name__)


class VerifyCell(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.send_verification_code'),
                                    "topic": settings.get('kafka.topics.auth')
                                    },
                           "PUT": {"event_type": settings.get('kafka.event_types.post.verify_sms_code'),
                                    "topic": settings.get('kafka.topics.auth')
                                    }
                           }

    auth = {
        'exempt_methods': ["POST", "PUT"]
    }

    def on_post(self, req, resp):
        # Init sms sending to cell, save cell and token to db
        [cell] = request.get_json_or_form("cell", req=req)
        # logger.debug('cell', cell)
        success = VerificationDA().create_verification_entry("cell", cell)
        totp_length = settings.get("services.twilio.totp_length")
        totp_lifetime_seconds = settings.get(
            "services.twilio.totp_lifetime_seconds")
        if success:
            resp.body = json.dumps(
                {"success": True, "totp_digits_count": totp_length, "totp_lifetime_seconds": totp_lifetime_seconds})
        else:
            resp.body = json.dumps(
                {"success": False, "description": "Something went wrong"})

    def on_put(self, req, resp):
        # provide cell and token, compare with stored
        (cell, token) = request.get_json_or_form(
            "cell", "token", req=req)
        # logger.debug('cell', cell, type(cell)),
        result = VerificationDA().verify_contact("cell", cell, token)

        resp.body = json.dumps({"result": result})

    @check_session
    def on_post_outgoing(self, req, resp):
        member_id = req.context.auth['session']['member_id']
        username = req.context.auth['session']['username']
        try:
            (contact_id, phone_number) = request.get_json_or_form(
                "contact_id", "phone_number", req=req)
            
            callback_uri = settings.get('services.twilio.outgoing_caller_callback_url')
            callback_url = request.build_url_from_request(
                req,
                f"{callback_uri}/{contact_id}"
            )
            # callback_url = f"{callback_uri}/{contact_id}"
            logger.debug(f"phoneNumber--: {phone_number}")
            # callback_url = f"https://0503a4d6cbad.ngrok.io/twilio"
            logger.debug(f"code generation callback: {callback_url}")
            validation_request = VerificationDA.add_outgoing_caller(member_id, username, contact_id, phone_number, callback_url)
            
            resp.body = json.dumps({
                "success": True,
                "validation_code": validation_request.validation_code,
                "description": "Post was created successfully",
            }, default_parser=json.parser)
        except Exception as err:
            logger.exception(f"code generation issue {err}")
            raise err
            # resp.body = json.dumps({
            #     "success": False,
            #     "description": err
            # })

    # @check_session_pass
    def on_post_verified(self, req, resp, contact_id):
        try:
            # if 'exception' in req.context.auth:
            #     member_id = None
            # else:
            #     member_id = req.context.auth['session']['member_id']

            (outgoing_caller_id_sid) = request.get_json_or_form(
                "outgoing_caller_id_sid", req=req)

            # data = json.load(req.stream)


            logger.debug(f"response from: {req.headers} ")
            resp.body = json.dumps({
                "success": True,
                "description": "Post was created successfully",
            }, default_parser=json.parser)
            resp.status = falcon.HTTP_201
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            # logger.exception(err)
            # raise err