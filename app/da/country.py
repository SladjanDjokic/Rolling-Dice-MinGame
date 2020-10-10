from app.util.db import source


class CountryCodeDA(object):
    source = source

    @classmethod
    def get_active_countries(cls):
        country_list = list()
        get_active_countries_query = ("""
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
                display_order,
                cell_regexp
            FROM country_code
            WHERE country_code.is_enabled = TRUE
            ORDER BY id ASC
        """)
        get_active_countries_params = (None, )
        cls.source.execute(get_active_countries_query,
                           get_active_countries_params)
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
                    display_order,
                    cell_regexp
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
                    "display_order": display_order,
                    "cell_regexp": cell_regexp
                }
                country_list.append(country)
        return country_list

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
