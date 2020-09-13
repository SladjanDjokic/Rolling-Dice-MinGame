import app.util.json as json
import app.util.request as request
from app.da.promo_codes import PromoCodesDA
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class PromoCodes(object):
    auth = {
        'exempt_methods': ["GET"]
    }

    def on_get(self, req, resp):
        promo_input = req.get_params("promoCode")

        #  Check if this promo code exists & is not expired
