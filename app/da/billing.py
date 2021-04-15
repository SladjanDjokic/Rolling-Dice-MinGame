import logging
from app.util.db import source

logger = logging.getLogger(__name__)


class BillingDA(object):
    source = source

    @classmethod
    def get_currency_list(cls, only_enabled):
        query = (f"""
            SELECT DISTINCT
                currency_code.id as currency_code_id,
                currency_code,
                currency_name,
                currency_minor_unit
            FROM currency_code
            LEFT JOIN country_code ON country_code.currency_code_id = currency_code.id
            {"WHERE country_code.is_enabled = TRUE" if only_enabled else ""}
        """)
        try:
            cls.source.execute(query, None)

            if cls.source.has_results():
                currencies = []
                for (
                    currency_code_id,
                    currency_code,
                    currency_name,
                    currency_minor_unit
                ) in cls.source.cursor:
                    currency = {
                        "currency_code_id": currency_code_id,
                        "currency_code": currency_code,
                        "currency_name": currency_name,
                        "currency_minor_unit": currency_minor_unit
                    }
                    currencies.append(currency)
                return currencies
            else:
                return None
        except Exception as e:
            logger.error(e, exc_info=True)
            return False

    @classmethod
    def get_weekly_billing_fixed_contract(cls, owner_id, start, end):
        query = f'''
            select * from get_weekly_billing_of_fixed_contract({owner_id}, '{start}', '{end}')
        '''

        logger.debug(f"billing-fixed query: {query}")
        
        cls.source.execute(query, None)
        contracts = []
        if cls.source.has_results():
            for (
                id,
                title,
                total_cost,
                paid_this_week,
                total_paid,
                pending,
                this_week_pending,
                milestone_info
            ) in cls.source.cursor:
                contract = {
                    "id": id,
                    "title": title,
                    "total_cost": total_cost,
                    "paid_this_week": paid_this_week,
                    "total_paid": total_paid,
                    "pending": pending,
                    "this_week_pending": this_week_pending,
                    "milestone_info": milestone_info
                }

                contracts.append(contract)

        return contracts

    @classmethod
    def get_weekly_billing_hourly_contract(cls, owner_id, start, end):
        query = f'''
            select * from get_weekly_billing_of_hourly_contract({owner_id}, '{start}', '{end}')
        '''
        
        cls.source.execute(query, None)
        contracts = []
        if cls.source.has_results():
            for (
                id,
                title,
                member_hours
            ) in cls.source.cursor:
                contract = {
                    "id": id,
                    "title": title,
                    "member_hours": member_hours
                }

                contracts.append(contract)

        return contracts
