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
