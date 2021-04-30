import logging
from app.util.db import source

logger = logging.getLogger(__name__)


class LocationDA(object):
    source = source

    @classmethod
    def insert_location(cls, params, commit=True):
        query = ("""
            INSERT INTO location (vendor_formatted_address, country_code_id, admin_area_1,admin_area_2, locality, sub_locality, street_address_1,street_address_2, postal_code, latitude, longitude, map_vendor, map_link, place_id)
            VALUES 
                (%(vendor_formatted_address)s, %(country_code_id)s, %(admin_area_1)s, %(admin_area_2)s, %(locality)s, %(sub_locality)s, %(street_address_1)s, %(street_address_2)s, %(postal_code)s, %(latitude)s, %(longitude)s, %(map_vendor)s, %(map_link)s, %(place_id)s)
            RETURNING id
        """)
        cls.source.execute(query, params)
        location_id = cls.source.get_last_row_id()
        if commit:
            cls.source.commit()
        if location_id:
            return location_id
