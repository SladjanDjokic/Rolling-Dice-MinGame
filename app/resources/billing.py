import app.util.json as json
import logging
import app.util.request as request
from app.util.auth import check_session
from app.da.billing import BillingDA

logger = logging.getLogger(__name__)

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

    @check_session
    def on_get_weekly_billing(self, req, resp):

        member_id = req.context.auth['session']['member_id']
        try:
            start = req.get_param('start')
            end = req.get_param('end')

            fixed_contracts = BillingDA.get_weekly_billing_fixed_contract(member_id, start, end)
            hourly_contracts = BillingDA.get_weekly_billing_hourly_contract(member_id, start, end)

            resp.body = json.dumps({
                "fixed_contracts": fixed_contracts,
                "hourly_contracts": hourly_contracts,
                "success": True
            }, default_parser=json.parser)

        except Exception as e:
            logger.debug(f"weekly_billing_error: {e}")
            resp.body = json.dumps({
                "success": False,
                "description": 'Failed to get weekly billing'
            }, default_parser=json.parser)