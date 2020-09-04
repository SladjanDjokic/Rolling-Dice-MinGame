from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import os
import time
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.twofactor.totp import TOTP
from cryptography.hazmat.primitives.hashes import SHA1
from app.config import settings
from app.util.db import source
from app.exceptions.data import DuplicateKeyError, DataMissingError, RelationshipReferenceError
import logging
logger = logging.getLogger(__name__)


class VerifyCellDA(object):
    source = source

    @classmethod
    def get_twilio_client(cls):
        account_sid = "ACe118114ed2feef31f332e87ed83b1bf3"
        auth_token = "f3f60ddb3f832a9f925afcf16aa00492"
        # account_sid = settings.get("services.twilio.twilio_sid")
        # auth_token = settings.get("services.twilio.twilio_auth_token")
        return Client(account_sid, auth_token)

    @classmethod
    def get_totp(cls):
        key = os.urandom(20)
        timeout = 30
        totp = TOTP(key, 8, SHA1(), timeout, backend=default_backend())
        return totp.generate(time.time()).decode('utf8')

    @classmethod
    def create_verification_entry(cls, cell):
        (message_sid, totp_code) = cls.sendSMS(cell)

        if message_sid:
            try:
                query = ("""
                    INSERT INTO cell_token
                    (cell_phone, token, sms_sid)
                    VALUES (%s, %s, %s) 
                """)
                params = (cell, totp_code, message_sid)
                cls.source.execute(query, params)
                cls.source.commit()
                return True
            except Exception as e:
                logger.exception(e)

    @classmethod
    def sendSMS(cls, cell):
        client = cls.get_twilio_client()
        totp_code = cls.get_totp()
        try:
            message = client.messages.create(
                to=cell,
                from_="+18173831103",
                body="Your AMERA Share verification code is: " + totp_code)
            return (message.sid, totp_code)
        except TwilioException as e:
            logger.exception(e)
        

    # @classmethod
    # def get_sent_token(cls, cell):
    #     try:
    #         query = ("""
    #             SELECT 
    #                 id, 
    #                 token
    #             FROM cell_token
    #             WHERE cell_phone = %s
    #         """)
    #         params = (cell)
    #     except: 

    # @classmethod
    # def compare(cls, cell, token):

