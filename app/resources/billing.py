import app.util.json as json
import logging
import app.util.request as request
from app.util.auth import check_session
from app.da.billing import BillingDA


class BillingResource(object):

    @check_session
    def on_get_currency(self, req, resp):
        only_enabled = req.get_param_as_bool('only_enabled', default=True)

        currency_list = BillingDA.get_currency_list(only_enabled)

        if currency_list:
            resp.body = json.dumps({
                "data": currency_list,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "success": False,
                "description": 'Failed to get currency list'
            }, default_parser=json.parser)
