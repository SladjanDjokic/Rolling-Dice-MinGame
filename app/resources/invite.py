import uuid
import logging
from datetime import timezone, datetime
from dateutil.relativedelta import relativedelta
from urllib.parse import urljoin

import app.util.json as json
import app.util.request as request
import app.util.email as sendmail

from app.config import settings
from app.da.member import MemberDA
from app.da.invite import InviteDA
from app.exceptions.group import InviteExistsError, InviteDataMissingError,\
    InviteKeyMissing, InviteNotFound, InviteExists,\
    InviteExpired, InviteDataMissing, InviteInvalidInviterError,\
    InviteInvalidInviter, InviteEmailSystemFailure
from app.exceptions.member import MemberExists


logger = logging.getLogger(__name__)


class MemberInviteResource(object):

    def on_post(self, req, resp):

        logger.debug("Content-Type: {}".format(req.content_type))
        logger.debug("Accepts: {}".format(req.accept))

        (email, first_name, last_name,
         inviter_member_id) = request.get_json_or_form(
            "email", "first_name", "last_name", "inviter_member_id", req=req
        )

        expiration = datetime.now() + relativedelta(months=+1)

        invite_key = uuid.uuid4().hex
        member = MemberDA.get_member_by_email(email=email)
        if member:
            raise MemberExists(email)

        invite_params = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "inviter_member_id": inviter_member_id,
            "invite_key": invite_key,
            "expiration": expiration
        }
        try:
            invite_id = InviteDA.create_invite(**invite_params)

            register_url = settings.get(
                "web.member_invite_register_url"
            ).format(invite_key)

            register_url = urljoin(request.get_url_base(req), register_url)

            self._send_email(
                email=email,
                first_name=first_name,
                invite_key=invite_key,
                register_url=register_url
            )

            resp.body = json.dumps({
                "invite_id": invite_id,
                "success": True
            })
        except sendmail.EmailAuthError:
            logger.exception('Deleting invite due to unable \
                             to auth to email system')
            InviteDA.delete_invite(invite_key)
            raise InviteEmailSystemFailure(invite_key)
        except InviteExistsError:
            raise InviteExists(email)
        except InviteDataMissingError:
            del invite_params["invite_key"]
            del invite_params["expiration"]
            raise InviteDataMissing(invite_params)
        except InviteInvalidInviterError:
            raise InviteInvalidInviter(inviter_member_id)

    def on_get(self, req, resp, invite_key):
        if not invite_key:
            raise InviteKeyMissing()

        # We store the key in hex format in the database
        invite_key = invite_key.hex

        logger.debug("Invite Key: {}".format(invite_key))
        logger.debug(invite_key)

        invite = InviteDA.get_invite(invite_key)

        logger.debug("Invite: {}".format(invite))

        if not invite:
            raise InviteNotFound(invite_key)

        utc_expiration = invite["expiration"].replace(tzinfo=timezone.utc)
        utc_now = datetime.now(timezone.utc)

        if utc_now > utc_expiration:
            logger.debug((
                "Expiration Datetime: {} (UTC) is "
                "past current Datetime: {} (UTC)"
            ).format(
                utc_expiration, utc_now))
            raise InviteExpired(invite_key)

        resp.body = json.dumps(invite, default_parser=str)

    def _send_email(self, invite_key, email, first_name, register_url):

        sendmail.send_mail(
            to_email=email,
            subject="Welcome to AMERA Share",
            template="welcome",
            data={
                "first_name": first_name,
                "invite_key": invite_key,
                "register_url": register_url
            })
