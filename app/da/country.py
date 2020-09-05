from app.util.db import source


class CountryCodeDA(object):
    source = source

    @classmethod
    def get_all_country(cls):
        country_list = list()
        get_all_country_query = ("""
            SELECT
                id,
                alpha2,
                alpha3,
                name,
                phone,
                currency_code,
                currency_name,
                currency_id,
                currency_minor_unit,
                domain,
                display_order
            FROM country_code
            ORDER BY id ASC
        """)
        get_all_country_params = (None, )
        cls.source.execute(get_all_country_query, get_all_country_params)
        if cls.source.has_results():
            for (
                    id,
                    alpha2,
                    alpha3,
                    name,
                    phone,
                    currency_code,
                    currency_name,
                    currency_id,
                    currency_minor_unit,
                    domain,
                    display_order
            ) in cls.source.cursor:
                country = {
                    "id": id,
                    "alpha2": alpha2,
                    "alpha3": alpha3,
                    "name": name,
                    "phone": phone,
                    "currency_code": currency_code,
                    "currency_name": currency_name,
                    "currency_id": currency_id,
                    "currency_minor_unit": currency_minor_unit,
                    "domain": domain,
                    "display_order": display_order
                }
                country_list.append(country)
        return country_list
