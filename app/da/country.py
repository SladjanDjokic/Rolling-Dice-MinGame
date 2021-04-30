from app.util.db import source


class CountryCodeDA(object):
    source = source

    @classmethod
    def get_active_countries(cls):
        country_list = list()
        get_active_countries_query = ("""
            SELECT
                country_code.id AS id, 
                alpha2,
                alpha3,
                name,
                phone,
                currency_code.currency_code,
                currency_code.currency_name,
                currency_code.id as currency_id,
                currency_code.currency_minor_unit,
                domain,
                display_order,
                cell_regexp,
                COALESCE(location_data_labels.admin_area_1, (SELECT admin_area_1 FROM location_data_labels WHERE country_code_id = 840)),
                COALESCE(location_data_labels.admin_area_2, (SELECT admin_area_2 FROM location_data_labels WHERE country_code_id = 840)),
                COALESCE(location_data_labels.locality, (SELECT locality FROM location_data_labels WHERE country_code_id = 840)),
                COALESCE(location_data_labels.sub_locality, (SELECT sub_locality FROM location_data_labels WHERE country_code_id = 840)),
                COALESCE(location_data_labels.street_address_1, (SELECT street_address_1 FROM location_data_labels WHERE country_code_id = 840)),
                COALESCE(location_data_labels.street_address_2, (SELECT street_address_2 FROM location_data_labels WHERE country_code_id = 840)),
                COALESCE(location_data_labels.postal_code, (SELECT postal_code FROM location_data_labels WHERE country_code_id = 840))
            FROM country_code
            LEFT JOIN currency_code ON currency_code_id = currency_code.id
            LEFT JOIN location_data_labels ON location_data_labels.country_code_id = country_code.id
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
                    cell_regexp,
                    admin_area_1,
                    admin_area_2,
                    locality,
                    sub_locality,
                    street_address_1,
                    street_address_2,
                    postal_code
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
                    "cell_regexp": cell_regexp,
                    "admin_area_1_label": admin_area_1,
                    "admin_area_2_label": admin_area_2,
                    "locality_label": locality,
                    "sub_locality_label": sub_locality,
                    "street_address_1_label": street_address_1,
                    "street_address_2_label": street_address_2,
                    "postal_code_label": postal_code
                }
                country_list.append(country)
        return country_list

    @classmethod
    def get_all_country(cls):
        country_list = list()
        get_all_country_query = ("""
            SELECT
                country_code.id AS id, 
                alpha2,
                alpha3,
                name,
                phone,
                currency_code.currency_code,
                currency_code.currency_name,
                currency_code.id as currency_id,
                currency_code.currency_minor_unit,
                domain,
                display_order,
                cell_regexp,
                COALESCE(location_data_labels.admin_area_1, (SELECT admin_area_1 FROM location_data_labels WHERE country_code_id = 840)),
                COALESCE(location_data_labels.admin_area_2, (SELECT admin_area_2 FROM location_data_labels WHERE country_code_id = 840)),
                COALESCE(location_data_labels.locality, (SELECT locality FROM location_data_labels WHERE country_code_id = 840)),
                COALESCE(location_data_labels.sub_locality, (SELECT sub_locality FROM location_data_labels WHERE country_code_id = 840)),
                COALESCE(location_data_labels.street_address_1, (SELECT street_address_1 FROM location_data_labels WHERE country_code_id = 840)),
                COALESCE(location_data_labels.street_address_2, (SELECT street_address_2 FROM location_data_labels WHERE country_code_id = 840)),
                COALESCE(location_data_labels.postal_code, (SELECT postal_code FROM location_data_labels WHERE country_code_id = 840))
            FROM country_code
            LEFT JOIN currency_code ON currency_code_id = currency_code.id
            LEFT JOIN location_data_labels ON location_data_labels.country_code_id = country_code.id
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
                    display_order,
                    cell_regexp,
                    admin_area_1,
                    admin_area_2,
                    locality,
                    sub_locality,
                    street_address_1,
                    street_address_2,
                    postal_code
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
                    "cell_regexp": cell_regexp,
                    "admin_area_1_label": admin_area_1,
                    "admin_area_2_label": admin_area_2,
                    "locality_label": locality,
                    "sub_locality_label": sub_locality,
                    "street_address_1_label": street_address_1,
                    "street_address_2_label": street_address_2,
                    "postal_code_label": postal_code
                }
                country_list.append(country)
        return country_list
