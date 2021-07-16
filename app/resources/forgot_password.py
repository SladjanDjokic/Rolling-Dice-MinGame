import logging
import uuid
import falcon
import app.util.json as json

from datetime import datetime, timedelta

from app.config import settings
import app.util.request as request
from app.da.member import MemberDA
from app.exceptions.member import MemberNotFound, ForgotKeyConflict, ForgotPassEmailSystemFailure
from app.config import settings
import app.util.email as sendmail
from app.util.request import build_url_from_request

logger = logging.getLogger(__name__)


class MemberForgotPasswordResource(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.forgot_password'),
                                    "topic": settings.get('kafka.topics.member')
                                    },
                           }

    def on_post(self, req, resp):
        (email) = request.get_json_or_form("email", req=req)
        email = email[0]
        logger.debug('email => {}'.format(email))
        if not email:
            raise falcon.HTTPError("400",
                                    title="Invalid Email",
                                    description="Please Provide Email Address.")
        
        member = MemberDA.get_member_by_email(email)
        if not member:
            raise MemberNotFound(email)

        data = MemberDA.get_password_reset_info_by_email(email)
        if data:
            id = data['id']
            utc_expiration = data["expiration"].replace(tzinfo=None)
            utc_now = datetime.utcnow()
            logger.debug((
                "Expiration Datetime: {} (UTC) is "
                "past current Datetime: {} (UTC)"
            ).format(
                utc_expiration, utc_now))
            if utc_now > utc_expiration:
                #please check it again whether we should delete or not
                result = MemberDA.delete_reset_password_info(id)
            else:
                raise ForgotKeyConflict()

        member_id = member["member_id"]
        forgot_key = uuid.uuid4().hex
        
        expiration_seconds = settings.get("web.forgot_password_expiration")
        expiration_datetime = datetime.utcnow() + timedelta(
            seconds=expiration_seconds
        )
        
        result = MemberDA.create_forgot_password(
            member_id=member_id, email=email, forgot_key=forgot_key,
            expiration=expiration_datetime, commit=True)

        result['expiration'] = result['expiration'].isoformat()

        forgot_url = settings.get(
                "web.member_forgot_password_url"
            ).format(forgot_key)

        logger.debug(f'forgot_url: {forgot_url}')

        forgot_url = build_url_from_request(req, forgot_url)
        logger.debug(f'forgot_url: {forgot_url}')
        result['forgot_url'] = forgot_url
        try:
            self._send_email(
                    email=email,
                    first_name=member['first_name'],
                    forgot_url=forgot_url,
                    forgot_key=forgot_key
                ) #smtp not configured yet
        except sendmail.EmailAuthError:
            logger.exception('Deleting forgot key due to unable \
                             to auth to email system')
            MemberDA.delete_reset_password_info(id)
            raise ForgotPassEmailSystemFailure(email)

        if result:    
            resp.body = json.dumps({
                    "success": True
                })

    def _send_email(self, email, first_name, forgot_url, forgot_key):
        sendmail.send_mail(
            to_email=email,
            subject="AMERA Share Password Reset Request",
            template="forgot-password",
            data={
                "first_name": first_name,
                "forgot_key": forgot_key,
                "forgot_url": forgot_url
            })
