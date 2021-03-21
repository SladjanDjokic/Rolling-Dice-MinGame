from app.config import settings
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from app.util.crypto import get_totp

import logging
logger = logging.getLogger(__name__)


class BaseTwilioClient:

    def __init__(self):
        self.account_sid = settings.get('services.twilio.account_sid')
        self.auth_token = settings.get('services.twilio.auth_token')
        self.client = Client(self.account_sid, self.auth_token)

    def send_sms(self, cell, message):
        # TODO Need to expand this to handle various messages
        try:
            message = self.client.messages.create(
                to=f"+{cell}",
                from_=settings.get('services.twilio.sender_number'),
                body=message)
            return message.sid
        except TwilioRestException as e:
            logger.exception(e)
