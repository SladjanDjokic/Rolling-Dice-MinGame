# Recovered for compatibility

import app.util.json as json
import app.util.request as request
from app.da.verification import VerificationDA
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class VerifyCell(object):
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
