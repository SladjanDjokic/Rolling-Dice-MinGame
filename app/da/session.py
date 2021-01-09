import logging
import traceback
import datetime
import app.util.json as json

from app.util.db import source
from app.exceptions.data import DuplicateKeyError
from app.exceptions.session import SessionExistsError
from app.util.filestorage import amerize_url

logger = logging.getLogger(__name__)


class SessionDA(object):
    source = source

    @classmethod
    def auth(cls, username, password):
        # TODO: CHANGE THIS LATER TO ENCRYPT IN APP
        query = ("""
        SELECT
            id,
            email,
            first_name,
            last_name,
            username,
            status,
            main_file_tree,
            bin_file_tree
        FROM member
        WHERE lower(username) = %s AND password = crypt(%s, password)
        """)

        params = (username.lower(), password)
        cls.source.execute(query, params)
        if cls.source.has_results():
            (id,
             email,
             first_name,
             last_name,
             username,
             status,
             main_file_tree,
             bin_tree_tree) = cls.source.cursor.fetchone()

            member = {
                "id": id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
                "status": status,
                "main_file_tree": main_file_tree,
                "bin_file_tree": bin_tree_tree
            }

            return member

        return None

    @classmethod
    def create_session(cls, member, session_id, expiration_date,
                       remote_ip_address, gateway_ip_address, original_url,
                       original_arguments, remote_ip_name, gateway_ip_name,
                       server_name, server_ip, ip_info, commit=True):

        # try:
        #     query = ("""
        #     DELETE FROM
        #         member_session
        #     WHERE
        #         expiration_date < current_timestamp
        #     """)
        #     cls.source.execute(query, [])
        #     cls.source.commit()
        # except Exception as err:
        #     cls.source.rollback()
        #     track = traceback.format_exc()
        #     logger.debug("Error clearing session table: ")
        #     logger.debug(err)
        #     logger.debug(track)
        #     pass

        query = ("""
        INSERT INTO
            member_session
        (
            -- Required
            session_id,
            member_id,
            email,
            first_name,
            last_name,
            username,
            expiration_date,
            remote_ip_address,
            gateway_ip_address,
            original_url,
            original_arguments,
            -- Not Required
            remote_name,
            remote_continent_code,
            gateway_name,
            gateway_country_code_id,
            remote_country_name,
            remote_country_code_2,
            remote_country_code_3,
            remote_country_code_id,
            remote_country_phone,
            remote_region_name,
            remote_region_code,
            remote_city_name,
            remote_postal_code,
            remote_latitude,
            remote_longitude,
            remote_timezone_name,
            remote_timezone_utc_offset,
            remote_language_id,
            server_ip_address,
            server_name,
            server_country_code_id,
            organization_name,
            organization_domain,
            organization_asn,
            organization_type,
            organization_route,
            carrier_name,
            carrier_mcc,
            carrier_mnc,
            user_agent,
            user_device,
            user_device_type,
            user_device_name,
            user_os,
            user_os_type,
            user_os_version,
            user_browser,
            user_browser_type,
            user_browser_version,
            ipregistry_response
        )
        VALUES (
            -- Required
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            -- Not Required
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s
        )
        """)

        # AES_ENCRYPT(%s, UNHEX(SHA2(%s)))
        # settings.get('MEMBER_KEY')
        params = (
            session_id,
            member.get("id"),
            member.get("email"),
            member.get("first_name"),
            member.get("last_name"),
            member.get("username"),
            expiration_date,
            ip_info.get('ip', remote_ip_address),
            gateway_ip_address,
            original_url,
            original_arguments,
            ip_info.get('hostname', remote_ip_name),
            ip_info.get('location').get("remote_continent_code"),
            gateway_ip_name,
            ip_info.get("gateway_country_code_id"),
            ip_info.get('location').get('country').get('name'),  # remote_country_name
            ip_info.get('location').get('country').get('code'),  # remote_country_code_2,
            None,  # remote_country_code_3,
            ip_info.get('location').get('country').get('area'),  # remote_country_code_id,
            ip_info.get('location').get('country').get('calling_code'),  # remote_country_phone,
            ip_info.get('location').get('region').get('name'),  # remote_region_name,
            ip_info.get('location').get('region').get('code'),  # remote_region_code,
            ip_info.get('location').get('city'),  # remote_city_name,
            ip_info.get('location').get('postal'),  # remote_postal_code,
            ip_info.get('location').get('latitude'),  # remote_latitude,
            ip_info.get('location').get('longitude'),  # remote_longitude,
            ip_info.get('time_zone').get('name'),  # remote_timezone_name,
            ip_info.get('time_zone').get('offset'),  # remote_timezone_utc_offset,
            None,  # ip_info.get('location').get('language').get('code'),  # remote_language_id,
            server_ip,  # server_ip_address,
            server_name,  # server_name,
            None,  # server_country_code_id,
            ip_info.get('connection').get('organization'),  # organization_name
            ip_info.get('connection').get('domain'),  # organization_domain,
            ip_info.get('connection').get('asn'),  # organization_asn,
            ip_info.get('connection').get('type'),  # organization_type,
            ip_info.get('connection').get('route'),  # organization_route,
            ip_info.get('carrier').get('name'),  # carrier_name,
            ip_info.get('carrier').get('mcc'),  # carrier_mcc,
            ip_info.get('carrier').get('mnc'),  # carrier_mnc,
            ip_info.get('user_agent').get('header'),  # user_agent,
            ip_info.get('user_agent').get('device').get('brand'),  # user_device,
            ip_info.get('user_agent').get('device').get('type'),  # user_device_type,
            ip_info.get('user_agent').get('device').get('name'),  # user_device_name,
            ip_info.get('user_agent').get('os').get('name'),  # user_os,
            ip_info.get('user_agent').get('os').get('type'),  # user_os_type,
            ip_info.get('user_agent').get('os').get('version'),  # user_os_version,
            ip_info.get('user_agent').get('name'),  # user_browser,
            ip_info.get('user_agent').get('type'),  # user_browser_type,
            ip_info.get('user_agent').get('version'),  # user_browser_version,
            json.dumps(ip_info)  # ipregistry_response
        )

        try:
            cls.source.execute(query, params)

            if commit:
                cls.source.commit()

            return session_id
        except DuplicateKeyError as err:
            raise SessionExistsError from err

    @classmethod
    def get_session(cls, session_id):
        query = ("""
        SELECT
            member_session.session_id as session_id,
            member_session.member_id as member_id,
            member_session.email as email,
            member_session.create_date as create_date,
            member_session.update_date as update_date,
            member_session.expiration_date as expiration_date,
            member_session.username as username,
            member_session.status as status,
            member_session.first_name as first_name,
            member_session.last_name as last_name,
            member.middle_name as middle_name,
            member.company_name as company,
            job_title.name as title,
            member_contact.phone_number as cell_phone,
            member_location.street as street,
            member_location.city as city,
            member_location.state as state,
            member_location.province as province,
            member_location.postal as postal,
            member_location.country as country,
            file_storage_engine.storage_engine_id as s3_avatar_url,
            member.user_type as user_type

        FROM member_session
        LEFT JOIN member ON member_session.member_id = member.id
        LEFT JOIN member_location ON member_session.member_id = member_location.member_id
        LEFT JOIN member_contact ON member_session.member_id = member_contact.member_id
        LEFT OUTER JOIN job_title ON member.job_title_id = job_title.id
        LEFT OUTER JOIN member_profile ON member_session.member_id = member_profile.member_id
        LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
        WHERE member_session.session_id = %s AND member_session.expiration_date >= current_timestamp AND member_session.status = 'online'
        """)

        params = (session_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            (
                session_id,
                member_id,
                email,
                create_date,
                update_date,
                expiration_date,
                username,
                status,
                first_name,
                last_name,
                middle_name,
                company,
                title,
                cell_phone,
                street,
                city,
                state,
                province,
                postal,
                country,
                s3_avatar_url,
                user_type
            ) = cls.source.cursor.fetchone()

            session = {
                "session_id": session_id,
                "member_id": member_id,
                "email": email,
                "create_date": create_date,
                "update_date": update_date,
                "expiration_date": expiration_date,
                "username": username,
                "status": status,
                "first_name": first_name,
                "last_name": last_name,
                "middle_name": middle_name,
                "company": company,
                "title": title,
                "cell_phone": cell_phone,
                "street": street,
                "city": city,
                "state": state,
                "province": province,
                "postal": postal,
                "country": country,
                "amera_avatar_url": amerize_url(s3_avatar_url),
                "user_type": user_type
            }

            return session

        return None

    @classmethod
    def get_full_session(cls, session_id):
        query = ("""
        SELECT
            member_session.session_id as session_id,
            member_session.member_id as member_id,
            member_session.email as email,
            member_session.create_date as create_date,
            member_session.update_date as update_date,
            member_session.expiration_date as expiration_date,
            member_session.username as username,
            member_session.status as status,
            member_session.first_name as first_name,
            member_session.last_name as last_name,
            member.middle_name as middle_name,
            member.company_name as company,
            job_title.name as title,
            json_agg(DISTINCT member_location.*) AS location_information,
            json_agg(DISTINCT member_contact_2.*) AS contact_information,
            json_agg(DISTINCT country_code.*) AS country_code,
            file_storage_engine.storage_engine_id as s3_avatar_url,
            member.user_type as user_type,
            member_session.remote_ip_address,
            member_session.gateway_ip_address,
            member_session.original_url,
            member_session.original_arguments,
            member_session.remote_name,
            member_session.remote_continent_code,
            member_session.gateway_name,
            member_session.gateway_country_code_id,
            member_session.remote_country_name,
            member_session.remote_country_code_2,
            member_session.remote_country_code_3,
            member_session.remote_country_code_id,
            member_session.remote_country_phone,
            member_session.remote_region_name,
            member_session.remote_region_code,
            member_session.remote_city_name,
            member_session.remote_postal_code,
            member_session.remote_latitude,
            member_session.remote_longitude,
            member_session.remote_timezone_name,
            member_session.remote_timezone_utc_offset,
            member_session.remote_language_id,
            member_session.server_ip_address,
            member_session.server_name,
            member_session.server_country_code_id,
            member_session.organization_name,
            member_session.organization_domain,
            member_session.organization_asn,
            member_session.organization_type,
            member_session.organization_route,
            member_session.carrier_name,
            member_session.carrier_mcc,
            member_session.carrier_mnc,
            member_session.user_agent,
            member_session.user_device,
            member_session.user_device_type,
            member_session.user_device_name,
            member_session.user_os,
            member_session.user_os_type,
            member_session.user_os_version,
            member_session.user_browser,
            member_session.user_browser_type,
            member_session.user_browser_version,
            member_session.ipregistry_response
        FROM member_session
        LEFT JOIN member ON member_session.member_id = member.id
        LEFT OUTER JOIN member_location ON member_location.member_id = member.id
        LEFT OUTER JOIN member_contact_2 ON member_contact_2.member_id = member.id
        LEFT OUTER JOIN country_code ON member_contact_2.device_country = country_code.id
        LEFT OUTER JOIN job_title ON job_title.id = member.job_title_id
        LEFT OUTER JOIN member_profile ON member.id = member_profile.member_id
        LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
        WHERE member_session.session_id = %s AND member_session.expiration_date >= current_timestamp AND member_session.status = 'online'
        GROUP BY
            member_session.session_id,
            member_session.member_id,
            member_session.email,
            member_session.create_date,
            member_session.update_date,
            member_session.expiration_date,
            member_session.username,
            member_session.status,
            member_session.first_name,
            member_session.last_name,
            member.middle_name,
            member.company_name,
            job_title.name,
            file_storage_engine.storage_engine_id,
            member.user_type,
            member_session.remote_ip_address,
            member_session.gateway_ip_address,
            member_session.original_url,
            member_session.original_arguments,
            member_session.remote_name,
            member_session.remote_continent_code,
            member_session.gateway_name,
            member_session.gateway_country_code_id,
            member_session.remote_country_name,
            member_session.remote_country_code_2,
            member_session.remote_country_code_3,
            member_session.remote_country_code_id,
            member_session.remote_country_phone,
            member_session.remote_region_name,
            member_session.remote_region_code,
            member_session.remote_city_name,
            member_session.remote_postal_code,
            member_session.remote_latitude,
            member_session.remote_longitude,
            member_session.remote_timezone_name,
            member_session.remote_timezone_utc_offset,
            member_session.remote_language_id,
            member_session.server_ip_address,
            member_session.server_name,
            member_session.server_country_code_id,
            member_session.organization_name,
            member_session.organization_domain,
            member_session.organization_asn,
            member_session.organization_type,
            member_session.organization_route,
            member_session.carrier_name,
            member_session.carrier_mcc,
            member_session.carrier_mnc,
            member_session.user_agent,
            member_session.user_device,
            member_session.user_device_type,
            member_session.user_device_name,
            member_session.user_os,
            member_session.user_os_type,
            member_session.user_os_version,
            member_session.user_browser,
            member_session.user_browser_type,
            member_session.user_browser_version,
            member_session.ipregistry_response
        """)

        params = (session_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            (
                session_id,
                member_id,
                email,
                create_date,
                update_date,
                expiration_date,
                username,
                status,
                first_name,
                last_name,
                middle_name,
                company,
                title,
                location_information,
                contact_information,
                country_code,
                s3_avatar_url,
                user_type,
                remote_ip_address,
                gateway_ip_address,
                original_url,
                original_arguments,
                remote_name,
                remote_continent_code,
                gateway_name,
                gateway_country_code_id,
                remote_country_name,
                remote_country_code_2,
                remote_country_code_3,
                remote_country_code_id,
                remote_country_phone,
                remote_region_name,
                remote_region_code,
                remote_city_name,
                remote_postal_code,
                remote_latitude,
                remote_longitude,
                remote_timezone_name,
                remote_timezone_utc_offset,
                remote_language_id,
                server_ip_address,
                server_name,
                server_country_code_id,
                organization_name,
                organization_domain,
                organization_asn,
                organization_type,
                organization_route,
                carrier_name,
                carrier_mcc,
                carrier_mnc,
                user_agent,
                user_device,
                user_device_type,
                user_device_name,
                user_os,
                user_os_type,
                user_os_version,
                user_browser,
                user_browser_type,
                user_browser_version,
                ipregistry_response
            ) = cls.source.cursor.fetchone()

            session = {
                "session_id": session_id,
                "member_id": member_id,
                "email": email,
                "create_date": create_date,
                "update_date": update_date,
                "expiration_date": expiration_date,
                "username": username,
                "status": status,
                "first_name": first_name,
                "last_name": last_name,
                "middle_name": middle_name,
                "company": company,
                "title": title,
                "location_information": location_information,
                "contact_information": contact_information,
                "country_code": country_code,
                "amera_avatar_url": amerize_url(s3_avatar_url),
                "user_type": user_type,
                "remote_ip_address": remote_ip_address,
                "gateway_ip_address": gateway_ip_address,
                "original_url": original_url,
                "original_arguments": original_arguments,
                "remote_name": remote_name,
                "remote_continent_code": remote_continent_code,
                "gateway_name": gateway_name,
                "gateway_country_code_id": gateway_country_code_id,
                "remote_country_name": remote_country_name,
                "remote_country_code_2": remote_country_code_2,
                "remote_country_code_3": remote_country_code_3,
                "remote_country_code_id": remote_country_code_id,
                "remote_country_phone": remote_country_phone,
                "remote_region_name": remote_region_name,
                "remote_region_code": remote_region_code,
                "remote_city_name": remote_city_name,
                "remote_postal_code": remote_postal_code,
                "remote_latitude": remote_latitude,
                "remote_longitude": remote_longitude,
                "remote_timezone_name": remote_timezone_name,
                "remote_timezone_utc_offset": remote_timezone_utc_offset,
                "remote_language_id": remote_language_id,
                "server_ip_address": server_ip_address,
                "server_name": server_name,
                "server_country_code_id": server_country_code_id,
                "organization_name": organization_name,
                "organization_domain": organization_domain,
                "organization_asn": organization_asn,
                "organization_type": organization_type,
                "organization_route": organization_route,
                "carrier_name": carrier_name,
                "carrier_mcc": carrier_mcc,
                "carrier_mnc": carrier_mnc,
                "user_agent": user_agent,
                "user_device": user_device,
                "user_device_type": user_device_type,
                "user_device_name": user_device_name,
                "user_os": user_os,
                "user_os_type": user_os_type,
                "user_os_version": user_os_version,
                "user_browser": user_browser,
                "user_browser_type": user_browser_type,
                "user_browser_version": user_browser_version,
                "ipregistry_response": ipregistry_response
            }

            return session

        return None

    @classmethod
    def delete_session(cls, session_id):
        query = ("""
        UPDATE member_session SET status = 'disconnected' WHERE session_id = %s
        """)

        params = (session_id,)
        cls.source.execute(query, params)
        cls.source.commit()

        return None

    @classmethod
    def get_sessions(cls, search_key, page_size=None, page_number=None, sort_params='', get_all=False, member_id=None):
        sort_columns_string = 'first_name ASC, last_name ASC'
        if sort_params:
            session_dict = {
                'session_id': 'member_session.session_id',
                'email': 'member_session.email',
                'username': 'member_session.username',
                'first_name': 'member_session.first_name',
                'last_name': 'member_session.last_name',
                'status': 'status',
                'create_date': 'member_session.create_date',
                'update_date': 'member_session.update_date',
                'expiration_date': 'member_session.expiration_date',
                'company_name': 'member.company_name',
                'ip_address': ' member_session.remote_ip_address',
                'city': 'member_session.remote_city_name',
                'device': 'member_session.user_device_name',
                'region': 'member_session.remote_region_name',
                'country': 'member_session.remote_country_name',
                'user_os': 'member_session.user_os',
                'organization_name': 'member_session.organization_name',
                'user_browser': 'member_session.user_browser',
                'remote_postal_code': 'member_session.remote_postal_code',
                'remote_timezone_name': 'member_session.remote_timezone_name',
            }
            sort_columns_string = formatSortingParams(
                sort_params, session_dict) or sort_columns_string

        query = (f"""
            SELECT
                session_id,
                member_session.email,
                member_session.username,
                member_session.first_name,
                member_session.last_name,
                CASE
                    WHEN
                        jsonb_extract_path(ipregistry_response, 'security') -> 'is_threat' = 'true'
                    THEN 'Threat'
                    ELSE 'Normal' END AS status,
                member_session.create_date,
                member_session.update_date,
                member_session.expiration_date,
                member_session.member_id,
                member_session.remote_ip_address,
                member_session.user_device_name,
                member_session.remote_city_name,
                member.company_name,
                member_session.remote_region_name,
                member_session.remote_country_name,
                member_session.user_os,
                member_session.organization_name,
                member_session.organization_type,
                member_session.user_browser,
                member_session.user_browser_version,
                member_session.remote_postal_code,
                member_session.remote_timezone_name,
                member_session.remote_country_code_2,
                member_session.remote_region_code
            FROM member_session
                LEFT JOIN member on member_session.member_id = member.id
            WHERE
                {f"member_session.member_id = {member_id} AND " if not get_all else ""}
                ( member.username LIKE %s
                OR member.first_name LIKE %s
                OR member.last_name LIKE %s
                OR member.email LIKE %s )
            ORDER BY {sort_columns_string}
            """)

        countQuery = f"""
            SELECT
                COUNT(*)
            FROM member_session
            WHERE
                {f"member_id = {member_id} AND" if not get_all else ""}
                ( username LIKE %s
                OR first_name LIKE %s
                OR last_name LIKE %s
                OR email LIKE %s )
            """

        like_search_key = """%{}%""".format(search_key)
        params = tuple(4 * [like_search_key])
        cls.source.execute(countQuery, params)

        count = 0
        if cls.source.has_results():
            (count,) = cls.source.cursor.fetchone()

        if page_size and page_number:
            query += """LIMIT %s OFFSET %s"""
            offset = 0
            if page_number > 0:
                offset = page_number * page_size
            params = params + (page_size, offset)

        sessions = []

        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                    session_id,
                    email,
                    username,
                    first_name,
                    last_name,
                    status,
                    create_date,
                    update_date,
                    expiration_date,
                    member_id,
                    remote_ip_address,
                    user_device,
                    remote_city_name,
                    company_name,
                    remote_region_name,
                    remote_country_name,
                    user_os,
                    organization_name,
                    organization_type,
                    user_browser,
                    user_browser_version,
                    remote_postal_code,
                    remote_timezone_name,
                    remote_country_code_2,
                    remote_region_code,
            ) in cls.source.cursor:
                session = {
                    "session_id": session_id,
                    "email": email,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "status": status,
                    "create_date": create_date,
                    "update_date": update_date,
                    "expiration_date": expiration_date,
                    "member_id": member_id,
                    'ip_address': remote_ip_address,
                    'device': user_device,
                    'city': remote_city_name,
                    "company_name": company_name,
                    "region": remote_region_name,
                    "country": remote_country_name,
                    "user_os": user_os,
                    "organization_name": organization_name,
                    "organization_type": organization_type,
                    "user_browser": user_browser,
                    "user_browser_version": user_browser_version,
                    "remote_postal_code": remote_postal_code,
                    "remote_timezone_name": remote_timezone_name,
                    "country_code": remote_country_code_2,
                    "region_code": remote_region_code,
                }

                sessions.append(session)

        return {"activities": sessions, "count": count}

    @classmethod
    def get_threats(cls, search_key, page_size=None, page_number=None, sort_params='', get_all=False, member_id=None):
        sort_columns_string = 'first_name ASC, last_name ASC'
        if sort_params:
            session_dict = {
                'session_id': 'member_session.session_id',
                'email': 'member_session.email',
                'username': 'member_session.username',
                'first_name': 'member_session.first_name',
                'last_name': 'member_session.last_name',
                'create_date': 'member_session.create_date',
                'update_date': 'member_session.update_date',
                'expiration_date': 'member_session.expiration_date',
                'company_name': 'member.company_name',
                'ip_address': ' member_session.remote_ip_address',
                'city': 'member_session.remote_city_name',
                'device': 'member_session.user_device_name',
                'region': 'member_session.remote_region_name',
                'country': 'member_session.remote_country_name',
                'user_os': 'member_session.user_os',
                'organization_name': 'member_session.organization_name',
                'user_browser': 'member_session.user_browser',
                'remote_postal_code': 'member_session.remote_postal_code',
                'remote_timezone_name': 'member_session.remote_timezone_name',
            }
            sort_columns_string = formatSortingParams(
                sort_params, session_dict) or sort_columns_string

        query = (f"""
            SELECT
                session_id,
                member_session.email,
                member_session.username,
                member_session.first_name,
                member_session.last_name,
                member_session.create_date,
                member_session.update_date,
                member_session.expiration_date,
                member_session.member_id,
                member_session.remote_ip_address,
                member_session.user_device_name,
                member_session.remote_city_name,
                member.company_name,
                member_session.remote_region_name,
                member_session.remote_country_name,
                member_session.user_os,
                member_session.organization_name,
                member_session.organization_type,
                member_session.user_browser,
                member_session.user_browser_version,
                member_session.remote_postal_code,
                member_session.remote_timezone_name,
                member_session.remote_country_code_2,
                member_session.remote_region_code
            FROM member_session
                LEFT JOIN member on member_session.member_id = member.id
            WHERE
                (
                    {f"member_session.member_id = {member_id} AND " if not get_all else ""}
                    jsonb_extract_path(ipregistry_response, 'security') -> 'is_threat' = 'true' AND
                    (
                        member.username LIKE %s
                        OR
                        member.first_name LIKE %s
                        OR
                        member.last_name LIKE %s
                        OR
                        member.email LIKE %s
                    )
                )
            ORDER BY {sort_columns_string}
            """)

        countQuery = f"""
            SELECT
                COUNT(*)
            FROM member_session
            WHERE
                {f"member_id = {member_id} AND" if not get_all else ""}
                ( username LIKE %s
                OR first_name LIKE %s
                OR last_name LIKE %s
                OR email LIKE %s )
            """

        like_search_key = """%{}%""".format(search_key)
        params = tuple(4 * [like_search_key])
        cls.source.execute(countQuery, params)

        count = 0
        if cls.source.has_results():
            (count,) = cls.source.cursor.fetchone()

        if page_size and page_number:
            query += """LIMIT %s OFFSET %s"""
            offset = 0
            if page_number > 0:
                offset = page_number * page_size
            params = params + (page_size, offset)

        sessions = []

        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                    session_id,
                    email,
                    username,
                    first_name,
                    last_name,
                    # status,
                    create_date,
                    update_date,
                    expiration_date,
                    member_id,
                    remote_ip_address,
                    user_device,
                    remote_city_name,
                    company_name,
                    remote_region_name,
                    remote_country_name,
                    user_os,
                    organization_name,
                    organization_type,
                    user_browser,
                    user_browser_version,
                    remote_postal_code,
                    remote_timezone_name,
                    remote_country_code_2,
                    remote_region_code,
            ) in cls.source.cursor:
                session = {
                    "session_id": session_id,
                    "email": email,
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    # "status": status,
                    "create_date": create_date,
                    "update_date": update_date,
                    "expiration_date": expiration_date,
                    "member_id": member_id,
                    'ip_address': remote_ip_address,
                    'device': user_device,
                    'city': remote_city_name,
                    "company_name": company_name,
                    "region": remote_region_name,
                    "country": remote_country_name,
                    "user_os": user_os,
                    "organization_name": organization_name,
                    "organization_type": organization_type,
                    "user_browser": user_browser,
                    "user_browser_version": user_browser_version,
                    "remote_postal_code": remote_postal_code,
                    "remote_timezone_name": remote_timezone_name,
                    "country_code": remote_country_code_2,
                    "region_code": remote_region_code,
                }

                sessions.append(session)

        return {"activities": sessions, "count": count}

def formatSortingParams(sort_by, entity_dict):
    columns_list = sort_by.split(',')
    new_columns_list = list()

    for column in columns_list:
        if column[0] == '-':
            column = column[1:]
            column = entity_dict.get(column)
            if column:
                column = column + ' DESC'
                new_columns_list.append(column)
        else:
            column = entity_dict.get(column)
            if column:
                column = column + ' ASC'
                new_columns_list.append(column)

    return (',').join(column for column in new_columns_list)
