import logging
import os

from requests.models import HTTPError
import falcon
import requests
from requests.exceptions import RequestException

import app.util.json as json
from urllib.parse import urljoin, urlencode, urlparse
from pprint import pformat

from app import settings
from app.da import MemberDA
from app.da.member_external_account import ExternalAccountDA
from app.da.project import ProjectDA
from app.util import request
from app.util.auth import check_session
from app.exceptions.session import InvalidSessionError
from app.da.bug_report import BugReportDA
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse

logger = logging.getLogger(__name__)
# Cache to hold state between redirects
STATE_CACHE = {}



class TwilioResource:

    @check_session
    def on_get_token(self, req, resp):

        try:
            member_id = req.context.auth['session']['member_id']
            # Create access token with credentials
            identity = f"customer{member_id}"
            account_sid = settings.get("services.twilio.account_sid")
            api_key = settings.get("services.twilio.api_key")
            secret = settings.get("services.twilio.api_secret")
            outgoing_application_sid = settings.get("services.twilio.twiml_application_sid")

            access_token = AccessToken(account_sid, api_key, secret, identity=identity)
            
            # Create a Voice grant and add to token
            voice_grant = VoiceGrant(
                outgoing_application_sid=outgoing_application_sid
            )

            access_token.add_grant(voice_grant)
            token = access_token.to_jwt()

            decoded_token_utf8 = token.decode('utf-8')
            decoded_token = token.decode()

            # logger.debug(f"account_sid: {account_sid} -- api_key: {api_key} -- secret: {secret} -- outgoing_application_sid: {outgoing_application_sid} \
            #     -- decoded_token_utf8: {decoded_token_utf8} -- decoded_token: {decoded_token}")

            resp.body = json.dumps({
                "success": True,
                "token": decoded_token,
                "description": "Token was created successfully"
            }, default_parser=json.parser)

        except Exception as e:
            logger.debug(f"twilio_token_issue: {e}")
            resp.body = json.dumps({
                "success": False,
                "description": "Something went wrong!"
            }, default_parser=json.parser)

    def on_post_voice(self, req, resp):

        try:

            # """Returns TwiML instructions to Twilio's POST requests"""

            (from_number, to_number, ) = request.get_json_or_form(
            "from", "to", req=req)
            response = VoiceResponse()
            dial = response.dial(caller_id=from_number)

            # logger.debug(f"phoneNumber: {phone_number}")
            dial.number(to_number)

            logger.debug(f"TwiML instructions {str(response)}")
            resp.body = str(response)
            resp.content_type="application/xml; charset=utf-8'"

        except Exception as e:
            logger.debug(f"twilio_call: {e}")
            resp.body = json.dumps({
                "success": False,
                "description": "Something went wrong!"
            }, default_parser=json.parser)

    # def on_post_voice_status(self, req, resp):
    #     try:
    #         # """Returns TwiML instructions to Twilio's POST requests"""
    #         # response = VoiceResponse()
    #         # dial = response.dial(caller_id='PNee898b2d9572412b82d93f8eda2cacd7')
    #         # phone_number = request.get_json_or_form(
    #         #     "phoneNumber", req=req)


    #         # logger.debug(f"phoneNumber: {phone_number}")
    #         # dial.number(phone_number)

    #         # resp.body = str(response)
    #         # resp.content_type="application/xml; charset=utf-8'"

    #     except Exception as e:
    #         logger.debug(f"twilio_call: {e}")
    #         resp.body = json.dumps({
    #             "success": False,
    #             "description": "Something went wrong!"
    #         }, default_parser=json.parser)
