import logging
from app.util.db import source

logger = logging.getLogger(__name__)


class LocationDA(object):
    source = source

    @classmethod
    def insert_location(cls, country_code_id, admin_area_1=None, admin_area_2=None, locality=None, sub_locality=None, street_address_1=None, street_address_2=None, postal_code=None, latitude=None, longitude=None, map_vendor=None, map_link=None, place_id=None, vendor_formatted_address=None, raw_response=None, location_profile_picture_id=None, name=None, commit=True):
        query = ("""
            INSERT INTO location (
                vendor_formatted_address,
                country_code_id,
                admin_area_1,admin_area_2,
                locality,
                sub_locality,
                street_address_1,street_address_2,
                postal_code,
                latitude,
                longitude,
                map_vendor,
                map_link,
                place_id,
                raw_response,
                location_profile_picture_id,
                name)
            VALUES (
                %(vendor_formatted_address)s,
                %(country_code_id)s,
                %(admin_area_1)s,
                %(admin_area_2)s,
                %(locality)s,
                %(sub_locality)s,
                %(street_address_1)s,
                %(street_address_2)s,
                %(postal_code)s,
                %(latitude)s,
                %(longitude)s,
                %(map_vendor)s,
                %(map_link)s,
                %(place_id)s,
                %(raw_response)s,
                %(location_profile_picture_id)s,
                %(name)s
            )
            RETURNING id
        """)
        params = {
            "vendor_formatted_address": vendor_formatted_address,
            "country_code_id": country_code_id,
            "admin_area_1": admin_area_1,
            "admin_area_2": admin_area_2,
            "locality": locality,
            "sub_locality": sub_locality,
            "street_address_1": street_address_1,
            "street_address_2": street_address_2,
            "postal_code": postal_code,
            "latitude": latitude,
            "longitude": longitude,
            "map_vendor": map_vendor,
            "map_link": map_link,
            "place_id": place_id,
            "raw_response": raw_response,
            "location_profile_picture_id": location_profile_picture_id,
            "name": name,
        }
        cls.source.execute(query, params)
        location_id = cls.source.get_last_row_id()
        if commit:
            cls.source.commit()
        if location_id:
            return location_id

    @classmethod
    def update_location(cls, location_id, country_code_id, admin_area_1=None, admin_area_2=None, locality=None, sub_locality=None, street_address_1=None, street_address_2=None, postal_code=None, latitude=None, longitude=None, map_vendor=None, map_link=None, place_id=None, vendor_formatted_address=None, raw_response=None, location_profile_picture_id=None, commit=True):
        query = ("""
            UPDATE location
            SET country_code_id = %s,
                admin_area_1 = %s,
                admin_area_2 = %s,
                locality = %s,
                sub_locality =%s,
                street_address_1 =%s,
                street_address_2 =%s,
                postal_code=%s,
                latitude=%s,
                longitude=%s,
                map_vendor=%s,
                map_link=%s,
                place_id=%s,
                vendor_formatted_address=%s,
                raw_response=%s,
                location_profile_picture_id=%s
            WHERE id = %s
            RETURNING id
        """)
        params = (country_code_id, admin_area_1, admin_area_2, locality, sub_locality, street_address_1, street_address_2, postal_code,
                  latitude, longitude, map_vendor, map_link, place_id, vendor_formatted_address, raw_response, location_profile_picture_id, location_id)

        cls.source.execute(query, params)
        location_id = cls.source.get_last_row_id()
        if commit:
            cls.source.commit()
        if location_id:
            return location_id

    @classmethod
    def get_location_by_place_id(cls, place_id):
        query = ("""
            SELECT
                location.id,
                location.country_code_id,
                location.admin_area_1,
                location.admin_area_2,
                location.locality,
                location.sub_locality,
                location.street_address_1,
                location.street_address_2,
                location.postal_code,
                location.vendor_formatted_address,
                location.latitude,
                location.longitude,
                location.map_vendor,
                location.map_link,
                location.place_id,
                location.create_date,
                location.update_date,
                location.location_profile_picture_id,
                file_storage_engine.storage_engine_id,
                location.name
            FROM location
            LEFT JOIN file_storage_engine ON location.location_profile_picture_id = file_storage_engine.id
            WHERE location.place_id = %s
        """)
        params = (place_id,)
        cls.source.execute(query, params)

        result = None
        if cls.source.has_results():
            (
                id,
                country_code_id,
                admin_area_1,
                admin_area_2,
                locality,
                sub_locality,
                street_address_1,
                street_address_2,
                postal_code,
                vendor_formatted_address,
                latitude,
                longitude,
                map_vendor,
                map_link,
                place_id,
                create_date,
                update_date,
                location_profile_picture_id,
                storage_engine_id,
                name
            ) = cls.source.cursor.fetchone()
            result = {
                "id": id,
                "country_code_id": country_code_id,
                "admin_area_1": admin_area_1,
                "admin_area_2": admin_area_2,
                "locality": locality,
                "sub_locality": sub_locality,
                "street_address_1": street_address_1,
                "street_address_2": street_address_2,
                "postal_code": postal_code,
                "vendor_formatted_address": vendor_formatted_address,
                "latitude": latitude,
                "longitude": longitude,
                "map_vendor": map_vendor,
                "map_link": map_link,
                "place_id": place_id,
                "create_date": create_date,
                "update_date": update_date,
                "location_profile_picture_id": location_profile_picture_id,
                "storage_engine_id": storage_engine_id,
                "name": name
            }

        return result
