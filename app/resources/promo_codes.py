import app.util.json as json
import app.util.request as request
from app.da.promo_codes import PromoCodesDA
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class PromoCodes(object):
    auth = {
        'exempt_methods': ["POST"]
    }

    def on_post(self, req, resp):
        (promo_input,) = request.get_json_or_form("promoCode", req=req)
        logger.debug('Will check this promo', promo_input)

        found_code = PromoCodesDA().check_promo_code(promo_input)

        if found_code:
            resp.body = json.dumps({
                "success": True,
                "description": found_code["description"],
                "promo_code_id": found_code["promo_code_id"]
            })
        else:
            resp.body = json.dumps({
                "success": False
            })

        #  Check if this promo code exists & is not expired
