import app.util.json as json
import app.util.request as request
from app.da.verify_cell import VerifyCellDA
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
        logger.debug('cell', cell)
        success = VerifyCellDA().create_verification_entry(cell)
        totp_length = settings.get("services.twilio.totp_length")
        totp_lifetime_seconds = settings.get("services.twilio.totp_lifetime_seconds")
        if success:
            resp.body = json.dumps({"success": True, "totp_digits_count": totp_length, "totp_lifetime_seconds": totp_lifetime_seconds})
        else:
            resp.body = json.dumps(
                {"success": False, "description": "Something went wrong"})

    def on_put(self, req, resp):
        # provide cell and token, compare with stored
        (cell, token) = request.get_json_or_form(
            "cell", "token", req=req)
        # logger.debug('cell', cell, type(cell)),
        result = VerifyCellDA().verify_cell_phone(cell, token)

        resp.body = json.dumps({"result": result})

        # if is_matches:
        #     resp.body = json.dumps({"success": True})
        # else:
        #     resp.body = json.dumps(
        #         {"success": False, "description": "Something went wrong"})