from twilio.rest import Client, TwilioException
from app.config import settings
import logging
logger = logging.getLogger(__name__)


class VerifyCell(object):

    @classmethod
    def init_client(cls):
        account_sid = settings.get("services.twilio.twilio_sid")
        auth_token = settings.get("services.twilio.twilio_auth_token")
        return Client(account_sid, auth_token)

    @classmethod
    def create_verification_service(cls, friendly_name):

        client = cls.init_client()
        service = client.verify.service.create(
            friendly_name="AMERA verification",
            lookup_enabled=True
            skip_sms_to_landlines=True,
            code_length=4
        )

        return service.sid

    @classmethod
    def get_twilio_verify_client():

    @classmethod
    def check_if_verification_service_exists(cls, service_sid):
        cls.init_client()
        services = client.verify.services.list()

    # @classmethod
    # def fetch_verification_service(cls, service_sid):
    #     cls.init_client()
    #     service = client.verify.services(service_sid).fetch()
