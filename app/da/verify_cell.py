from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import os
import time
from datetime import datetime
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.twofactor.totp import TOTP
from cryptography.hazmat.primitives.twofactor import InvalidToken
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
        account_sid = os.environ["AMERA_API_SERVICES.TWILIO.ACCOUNT_SID"]
        auth_token = os.environ["AMERA_API_SERVICES.TWILIO.AUTH_TOKEN"]
        return Client(account_sid, auth_token)

    @classmethod
    def get_totp(cls):
        key = os.urandom(20)
        timeout = 30
        token_time = time.time()
        potp_length = settings.get("services.twilio.potp_length")
        totp = TOTP(key, 6, SHA1(), timeout, backend=default_backend())
        token = totp.generate(token_time).decode('utf8')
        return (token, token_time)

     
    @classmethod
    def verify_cell_phone(cls, cell, user_token):
        verification_entry = cls.get_verification_entry(cell)
        logger.debug(verification_entry)

        if verification_entry:
            cls.delete_verification_entry(verification_entry["entry_id"])
            return (verification_entry["token"] == user_token)
        return None
            


    @classmethod
    def create_verification_entry(cls, cell):
        (message_sid, token, token_time) = cls.sendSMS(cell)
        ISOtimestamp = datetime.fromtimestamp(token_time).isoformat()

        if message_sid:
            try:
                query = ("""
                    INSERT INTO cell_token
                    (cell_phone, token, time, sms_sid)
                    VALUES (%s, %s, TIMESTAMP %s, %s) 
                """)
                params = (cell, token, ISOtimestamp, message_sid)
                cls.source.execute(query, params)
                cls.source.commit()
                return True
            except Exception as e:
                logger.exception(e)
    
    @classmethod
    def delete_verification_entry(cls, id):
        try: 
            query = ("""
                DELETE FROM cell_token
                WHERE id = %s
            """)
            params = (id,)
            cls.source.execute(query, params)
            cls.source.commit()
        except Exception as e:
            logger.exception(e)


    @classmethod
    def get_verification_entry(cls, cell):
        try: 
            query = ("""SELECT 
                    id as entry_id,
                    token,
                    time
                FROM cell_token
                WHERE cell_phone = %s AND time = (SELECT MAX(time) FROM cell_token)""")
            params = (cell,)
            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                    entry_id, 
                    token, 
                    time
                ) in cls.source.cursor:
                    verification_entry = {
                        "entry_id": entry_id,
                        "token": token,
                        "token_time": time
                    }
                    return verification_entry
            return None
        except Exception as e:
            logger.exception(e)

    

    @classmethod
    def sendSMS(cls, cell):
        client = cls.get_twilio_client()
        (token, token_time) = cls.get_totp()
        try:
            message = client.messages.create(
                to=f"+{cell}",
                from_=os.environ["AMERA_API_SERVICES.TWILIO.SENDER_NUMBER"],
                body="Your AMERA Share verification code is: " + token)
            return (message.sid, token, token_time)
        except TwilioRestException as e:
            logger.exception(e)
        
    


