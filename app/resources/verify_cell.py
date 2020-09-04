import app.util.json as json
import app.util.request as request
from app.da.verify_cell import VerifyCellDA
import logging

logger = logging.getLogger(__name__)


class VerifyCell(object):
   
    # auth = {
    #     'exempt_methods': ["POST"]
    # }

    def on_post(self, req, resp):
        # Init sms sending to cell, save cell and token to db
        (cell) = request.get_json_or_form("cell", req=req)
        logger.debug('cell', cell)
        success = VerifyCellDA().create_verification_entry()

        if success:
            resp.body = json.dumps({"success": True})
        else:
            resp.body = json.dumps(
                {"success": False, "description": "Something went wrong"})

    def on_put(self, req, resp):
        # provide cell and token, compare with stored
        (cell, token) = request.get_json_or_form(
            "cell", "token", req=req)

        is_matches = VerifyCellDA().compare(cell, token)
