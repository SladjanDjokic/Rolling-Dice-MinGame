from app.util.security import SECURITY_EXCHANGE_OPTIONS
import app.util.json as json
import logging
# import datetime
from urllib import parse

from app.util.db import source, formatSortingParams
from app.util.config import settings
from app.util.filestorage import amerize_url
from app.da.location import LocationDA

from app.exceptions.data import DataMissingError, RelationshipReferenceError
# from app.exceptions.member import ForgotDuplicateDataError


logger = logging.getLogger(__name__)


class MemberDA(object):
    source = source

    @classmethod
    def member_exists(cls, member_id):
        check_query = """
            SELECT EXISTS(
                SELECT id FROM member WHERE id = %s
            );
        """
        cls.source.execute(check_query, (member_id, ))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        else:
            return False

    @classmethod
    def get_member(cls, member_id):
        return cls.__get_member('id', member_id)

    @classmethod
    def get_member_by_username(cls, username):
        return cls.__get_member('username', username)

    @classmethod
    def get_member_by_email(cls, email):
        return cls.__get_member('email', email)

    @classmethod
    def get_all_members(cls, member_id):
        members = list()
        get_all_members_query = """
            SELECT
                id,
                email,
                create_date,
                update_date,
                username,
                status,
                first_name,
                last_name
            FROM member
            WHERE id <> %s
        """

        get_all_members_params = (member_id, )
        cls.source.execute(get_all_members_query, get_all_members_params)
        if cls.source.has_results():
            for (
                    member_id,
                    email,
                    create_date,
                    update_date,
                    username,
                    status,
                    first_name,
                    last_name,
            ) in cls.source.cursor:
                member = {
                    "member_id": member_id,
                    "email": email,
                    "create_date": create_date,
                    "update_date": update_date,
                    "username": username,
                    "status": status,
                    "first_name": first_name,
                    "last_name": last_name,
                    "member_name": f'{first_name} {last_name}'
                }

                members.append(member)

        return members

    @classmethod
    def extractAvailableMembers(cls, event_invite_to_list):
        res = []
        if len(event_invite_to_list) == 0:
            return res

        separator = ','
        strCanidateList = separator.join(map(str, event_invite_to_list))
        logger.debug("strCanidateList: {}".format(strCanidateList))

        query = ("""
            select id from member where member.id = ANY ('{""" + strCanidateList + """}'::int[])
        """)

        logger.debug("query: {}".format(query))

        params = ()
        cls.source.execute(query, params)
        if cls.source.has_results():
            for entry_da in cls.source.cursor.fetchall():
                res.append(entry_da[0])
        return res

    @classmethod
    def get_password_reset_info_by_email(cls, email):
        return cls.__get_password_reset_info('email', email)

    @classmethod
    def get_password_reset_info_by_forgot_key(cls, forgot_key):
        return cls.__get_password_reset_info('forgot_key', forgot_key)

    @classmethod
    def get_members(cls, member_id, search_key, page_size=None, page_number=None, sort_params='', all_members=False):
        sort_columns_string = 'create_date DESC, first_name ASC'
        members_dict = {
            "member_id": "member.id",
            "user_type": "member.user_type",
            "email": "member.email",
            "create_date": "member.create_date",
            "update_date": "member.update_date",
            "username": "member.username",
            "status": "member.status",
            "first_name": "member.first_name",
            "middle_name": "member.middle_name",
            "last_name": "member.last_name",
            "company_name": "company_name",
            "department": "department.name",
            "title": "job_title.name"
        }

        if sort_params:
            sort_columns_string = formatSortingParams(
                sort_params, members_dict) or sort_columns_string

        where_clause = ""
        if search_key != "" and len(search_key) > 0:
            where_clause = """
            (
                email LIKE %s
                OR
                username LIKE %s
                OR first_name LIKE %s
                OR last_name LIKE %s
            )
            """

        if not all_members:
            if where_clause != "":
                where_clause = where_clause + " AND "
            where_clause = where_clause + " member.id <> %s "

        if where_clause != "":
            where_clause = " WHERE " + where_clause

        query = f"""
            SELECT
                member.id as member_id,
                member.user_type as user_type,
                member.email as email,
                member.create_date as create_date,
                member.update_date as update_date,
                member.username as username,
                member.status as status,
                member.first_name as first_name,
                member.middle_name as middle_name,
                member.last_name as last_name,
                COALESCE(company.name, member.company_name) as company_name,
                department.name as department,
                job_title.name as title,
                file_storage_engine.storage_engine_id as s3_avatar_url
            FROM member
                LEFT OUTER JOIN department ON department.id = member.department_id
                LEFT OUTER JOIN job_title ON job_title.id = member.job_title_id
                LEFT OUTER JOIN member_profile ON member.id = member_profile.member_id
                LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                LEFT JOIN company_member ON company_member.member_id = member.id
                LEFT JOIN company ON company_member.company_id=company.id
                {where_clause}
            ORDER BY {sort_columns_string}
            """

        count = (f"SELECT COUNT(id) FROM member {where_clause}")

        like_search_key = """%{}%""".format(search_key)
        params = ()
        if search_key != "" and len(search_key) > 0:
            params = (like_search_key, like_search_key,
                      like_search_key, like_search_key)
        if not all_members:
            params = params + (member_id, )

        # logger.debug(f"COUNT QUERY: {count}")
        # logger.debug(f"COUNT PARAM: {params}")
        cls.source.execute(count, params)

        count = 0
        if cls.source.has_results():
            (count,) = cls.source.cursor.fetchone()
        logger.debug(f"COUNT RESULT: {count}")

        if count > 0 and page_size and page_number >= 0:
            query += """LIMIT %s OFFSET %s"""
            offset = 0
            if page_number > 0:
                offset = page_number * page_size
            params = params + (page_size, offset)

        members = []
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                    member_id,
                    user_type,
                    email,
                    create_date,
                    update_date,
                    username,
                    status,
                    first_name,
                    middle_name,
                    last_name,
                    company_name,
                    department,
                    title,
                    s3_avatar_url
            ) in cls.source.cursor:
                member = {
                    "member_id": member_id,
                    "user_type": user_type,
                    "email": email,
                    "create_date": create_date,
                    "update_date": update_date,
                    "username": username,
                    "status": status,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "member_name": f'{first_name}{middle_name}{last_name}',
                    "company_name": company_name,
                    "department": department,
                    "title": title,
                    "amera_avatar_url": amerize_url(s3_avatar_url)
                }

                members.append(member)

        return {
            "members": members,
            "count": count
        }

    @classmethod
    def get_group_members(cls, member_id, search_key, page_size, page_number):

        groups_query = """
            SELECT
                group_id
            FROM member_group_membership
            WHERE member_id = %s
            """

        same_group_members_query = """
            SELECT
                member_id
            FROM member_group_membership
            WHERE group_id
                IN (
            """ + groups_query + """ )"""

        group_leaders_query = """
            SELECT
                group_leader_id
            FROM member_group
            WHERE id
                IN (
            """ + groups_query + ")"

        group_members_query = """
            SELECT
                member_id
            FROM member_group_membership
            WHERE group_id
                IN (
                    SELECT
                        id
                    FROM member_group
                    WHERE group_leader_id = %s
                )
            """

        query = """
            SELECT
                id,
                email,
                create_date,
                update_date,
                username,
                status,
                first_name,
                last_name
            FROM member
            WHERE (id IN ( """ + same_group_members_query + """ )
                    OR id IN ( """ + group_leaders_query + """)
                    OR id IN ( """ + group_members_query + """ ))
                AND id <> %s
                AND ( email LIKE %s
                    OR username LIKE %s
                    OR first_name LIKE %s
                    OR last_name LIKE %s )
            """

        like_search_key = """%{}%""".format(search_key)
        params = (
            member_id, member_id, member_id, member_id, like_search_key, like_search_key, like_search_key, like_search_key)

        if page_size and page_number:
            query += """LIMIT %s OFFSET %s"""
            params = (member_id, member_id, member_id, member_id, like_search_key, like_search_key, like_search_key,
                      like_search_key, page_size, (page_number - 1) * page_size)

        members = []
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                    member_id,
                    email,
                    create_date,
                    update_date,
                    username,
                    status,
                    first_name,
                    last_name,
            ) in cls.source.cursor:
                member = {
                    "member_id": member_id,
                    "email": email,
                    "create_date": create_date,
                    "update_date": update_date,
                    "username": username,
                    "status": status,
                    "first_name": first_name,
                    "last_name": last_name,
                }

                members.append(member)

        return members

    @classmethod
    def __get_member(cls, key, value):
        query = ("""
        SELECT
            id,
            email,
            create_date,
            update_date,
            username,
            status,
            first_name,
            last_name
        FROM member
        WHERE {} = %s
        """.format(key))

        params = (value,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                    member_id,
                    email,
                    create_date,
                    update_date,
                    username,
                    status,
                    first_name,
                    last_name,
            ) in cls.source.cursor:
                member = {
                    "member_id": member_id,
                    "email": email,
                    "create_date": create_date,
                    "update_date": update_date,
                    "username": username,
                    "status": status,
                    "first_name": first_name,
                    "last_name": last_name,
                }

                return member

        return None

    @classmethod
    def __get_password_reset_info(cls, key, value):
        query = ("""
        SELECT
            id,
            member_id,
            email,
            forgot_key,
            expiration
        FROM forgot_password
        WHERE {} = %s
        """.format(key))

        params = (value,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                id,
                member_id,
                email,
                forgot_key,
                expiration
            ) in cls.source.cursor:
                forgot_password = {
                    "id": id,
                    "member_id": member_id,
                    "email": email,
                    "forgot_key": forgot_key,
                    "expiration": expiration
                }

                return forgot_password

        return None

    @classmethod
    def register(cls, city, state, province, pin, avatar_storage_id, email, username, password, first_name,
                 last_name, company_name, job_title_id, date_of_birth, phone_number,
                 country, postal, cell_confrimation_ts, email_confrimation_ts, department_id, main_file_tree_id, bin_file_tree_id,
                 commit=True):

        page_settings = settings.get('page_settings')

        # TODO: CHANGE THIS LATER TO ENCRYPT IN APP
        query_member = ("""
        INSERT INTO member
        (pin, email, username, password, first_name, last_name,
         date_of_birth, company_name, job_title_id, security_picture_storage_id, department_id, main_file_tree, bin_file_tree)
        VALUES (%s, %s, %s, crypt(%s, gen_salt('bf')), %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """)
        query_member_contact = ("""
        INSERT INTO member_contact
        (member_id, phone_number, email)
        VALUES (%s, %s, %s)
        """)
        query_phone_code = ("""
        SELECT phone FROM country_code WHERE id = %s
        """)
        query_member_contact_2 = ("""
        INSERT INTO member_contact_2
        (member_id, description, device, device_type, device_country,
         device_confirm_date, method_type, display_order, primary_contact)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """)

        query_member_profile = ("""
        INSERT INTO member_profile (member_id, profile_picture_storage_id)
        VALUES (%s, %s)
        """)

        query_member_page_settings = ("""
            INSERT INTO member_page_settings
                (member_id, page_type, view_type, sort_order)
            VALUES (%s, %s, %s, %s)
        """)

        # AES_ENCRYPT(%s, UNHEX(SHA2(%s)))
        # settings.get('MEMBER_KEY')
        # store member personal info
        params_member = (pin, email, username, password, first_name,
                         last_name, date_of_birth, company_name, job_title_id,
                         avatar_storage_id, department_id, main_file_tree_id, bin_file_tree_id)
        cls.source.execute(query_member, params_member)
        id = cls.source.get_last_row_id()

        if email:
            # Member_contact_2
            params_email_member_contact_2 = (
                id, "Office email", email, "email", country, email_confrimation_ts, "html", 2, True)
            cls.source.execute(query_member_contact_2,
                               params_email_member_contact_2)

        if phone_number:
            # Get phone code. Lame but fast
            cls.source.execute(query_phone_code, (country,))
            phone_code = str(cls.source.cursor.fetchone()[0])
            # store member contact info
            # Subtract phone code from number
            params_member_contact = (
                id, phone_number.lstrip(phone_code), email)
            cls.source.execute(query_member_contact, params_member_contact)
            # Member_contact_2

            params_cell_member_contact_2 = (
                id, "Cell phone", phone_number.lstrip(phone_code), "cell", country, cell_confrimation_ts, "voice", 1, True)
            cls.source.execute(query_member_contact_2,
                               params_cell_member_contact_2)

        # When registering a new member, the uploaded photo is set as both profile and security picture. Profile picture can be changed later on.
        params_member_profile = (id, avatar_storage_id)
        cls.source.execute(query_member_profile, params_member_profile)

        for key in page_settings:
            page_setting = page_settings[key]
            page_type = page_setting['page_type']
            view_type = page_setting['view_type']
            sort_order = page_setting['sort_order']

            cls.source.execute(query_member_page_settings,
                               (id, page_type, view_type, sort_order))

        if commit:
            cls.source.commit()

        return id

    @classmethod
    def get_contact_member(cls, member_id):
        query = ("""
            SELECT
                member.email as email,
                member.first_name as first_name,
                member.middle_name as middle_name,
                member.last_name as last_name,
                COALESCE(location.country_code_id, 840) AS country_code_id,
                COALESCE(country_code.name, (SELECT name FROM country_code WHERE id = 840)) as country,
                member_contact.phone_number as cell_phone,
                contact.company_name as company_name,
                contact.role_id as role_id
            FROM member
            LEFT JOIN member_contact ON member.id = member_contact.member_id
            LEFT JOIN member_location ON member.id = member_location.member_id
            LEFT JOIN location ON location.id = member_location.location_id
            LEFT JOIN contact ON member.id = contact.member_id
            LEFT JOIN country_code ON country_code.id = location.country_code_id
            WHERE member.id = %s
            """)

        params = (member_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                    email,
                    first_name,
                    middle_name,
                    last_name,
                    country,
                    country_code_id,
                    cell_phone,
                    company_name,
                    role_id
            ) in cls.source.cursor:
                member = {
                    "email": email,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "country": country,
                    "country_code_id": country_code_id,
                    "cell_phone": cell_phone,
                    "company_name": company_name,
                    "role_id": role_id
                }

                return member

        return None

    @classmethod
    def get_member_contact(cls, member_id):
        query = """
        SELECT
            phone_number
        FROM member_contact
        WHERE member_id = %s
        """

        params = (member_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (phone_number) in cls.source.cursor:
                member = {
                    "phone_number": phone_number,
                }

                return member
        return None

    @classmethod
    def get_member_location(cls, member_id):
        query = """
        SELECT
            country
        FROM member_location
        WHERE member_id = %s
        """

        params = (member_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (country) in cls.source.cursor:
                member = {
                    "country": country,
                }

                return member
        return None

    @classmethod
    def __get_member_forgot_by_email(cls, key, value):
        query = ("""
            SELECT
                id,
                member_id,
                email,
                forgot_key,
                expiration
            FROM forgot_password
            WHERE {} = %s
            """.format(key))

        params = (value,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                id,
                member_id,
                email,
                forgot_key,
                expiration
            ) in cls.source.cursor:
                forgot_password = {
                    "id": id,
                    "member_id": member_id,
                    "email": email,
                    "forgot_key": forgot_key,
                    "expiration": expiration
                }

                return forgot_password

        return None

    @classmethod
    def create_forgot_password(cls, member_id, email, forgot_key,
                               expiration, commit=True):

        query = ("""
        INSERT INTO forgot_password
            (member_id, email, forgot_key, expiration)
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """)

        params = (
            member_id, email, forgot_key, expiration
        )
        cls.source.execute(query, params)

        if commit:
            cls.source.commit()
        result = cls.get_password_reset_info_by_email(email)
        return result

    @classmethod
    def delete_reset_password_info(cls, id, commit=True):
        query = ("""
            DELETE FROM forgot_password WHERE id = %s
            """)

        params = (id,)
        res = cls.source.execute(query, params)
        if commit:
            cls.source.commit()

        return res

    @classmethod
    def expire_reset_password_key(cls, expiration, forgot_key, commit=True):

        query = ("""
        UPDATE forgot_password SET
            expiration = %s
        WHERE forgot_key = %s
        """)

        params = (
            expiration, forgot_key,
        )
        try:
            cls.source.execute(query, params)

            if commit:
                cls.source.commit()
        except DataMissingError as err:
            raise DataMissingError from err

    @classmethod
    def update_member_password(cls, member_id, password, commit=True):
        query = ("""
        UPDATE member SET
            password = crypt(%s, gen_salt('bf')),
            update_date = CURRENT_TIMESTAMP
        WHERE id = %s
        """)
        params = (
            password, member_id
        )
        try:
            cls.source.execute(query, params)

            if commit:
                cls.source.commit()
        except DataMissingError as err:
            raise DataMissingError from err

    @classmethod
    def update_member_status(cls, member_id, status, commit=True):
        try:
            query = ("""
                UPDATE member SET
                    status = %s,
                    update_date = CURRENT_TIMESTAMP
                WHERE id = %s
                RETURNING id
            """)
            params = (
                status, member_id
            )
            cls.source.execute(query, params)
            if commit:
                cls.source.commit()

            if cls.source.has_results():
                (id, ) = cls.source.cursor.fetchone()
                return id
            return None

        except DataMissingError as err:
            raise DataMissingError from err

    @classmethod
    def get_job_list(cls,):
        query = """
        SELECT
            id as job_title_id,
            name as job_title
        FROM job_title
        ORDER BY name
        """
        params = ()
        cls.source.execute(query, params)
        if cls.source.has_results():
            entry = list()
            for entry_da in cls.source.cursor.fetchall():
                entry_element = {
                    "job_title_id": entry_da[0],
                    "job_title": entry_da[1]
                }
                entry.append(entry_element)
            return entry
        return None

    @classmethod
    def get_department_list(cls,):
        query = """
        SELECT
            id as department_id,
            name as department_name
        FROM department
        ORDER BY name
        """
        params = ()
        cls.source.execute(query, params)
        if cls.source.has_results():
            entry = list()
            for entry_da in cls.source.cursor.fetchall():
                entry_element = {
                    "department_id": entry_da[0],
                    "department_name": entry_da[1]
                }
                entry.append(entry_element)
            return entry
        return None

    @classmethod
    def get_department_name(cls, department_id):
        query = ("""
            SELECT name
            FROM department
            WHERE id = %s
        """)
        cls.source.execute(query, (department_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def get_terms(cls,):
        query = ("""
                SELECT
                    amera_tos.id as amera_tos_id,
                    amera_tos.contract_text as contract_text,
                    country_code.alpha2 as country_code_alpha2,
                    country_code.alpha3 as country_code_alpha3
                FROM amera_tos
                LEFT JOIN amera_tos_country ON amera_tos_country.amera_tos_id = amera_tos.id
                LEFT JOIN country_code ON country_code.id = amera_tos_country.country_code_id
                WHERE amera_tos.status = 'active'
            """)
        params = ()
        cls.source.execute(query, params)
        if cls.source.has_results():
            entry = list()
            for entry_da in cls.source.cursor.fetchall():
                entry_element = {
                    "amera_tos_id": entry_da[0],
                    "contract_text": entry_da[1],
                    "country_code_alpha2": entry_da[2],
                    "country_code_alpha3": entry_da[3],
                }
                entry.append(entry_element)
            return entry
        return None

    @classmethod
    def get_timezones(cls,):
        query = ("""
                SELECT * FROM timezone
            """)
        params = ()
        cls.source.execute(query, params)
        if cls.source.has_results():
            entry = list()
            for entry_da in cls.source.cursor.fetchall():
                entry_element = {
                    "tz_id": entry_da[0],
                    # because timedelta is not JSON-serializable
                    "utc_offset": str(entry_da[1]),
                    "gmt_offset": str(entry_da[2]),
                    "zone_name": entry_da[3],
                    "country_code_id": entry_da[4]
                }
                entry.append(entry_element)
            return entry
        return None

    @classmethod
    def assign_tree(cls, tree_type, member_id, tree_id):
        '''
            This is used to assign a tree id to an existing members for migration purposes
        '''
        main_query = ("""
            UPDATE member
            SET main_file_tree = %s,
                update_date = CURRENT_TIMESTAMP
            WHERE id = %s
        """)
        bin_query = ("""
            UPDATE member
            SET bin_file_tree = %s,
                update_date = CURRENT_TIMESTAMP
            WHERE id = %s
        """)
        params = (tree_id, member_id)
        query = main_query if tree_type == 'main' else bin_query
        cls.source.execute(query, params)
        cls.source.commit()
        return True

    @classmethod
    def get_all_skills(cls,):
        query = ("""
            SELECT json_agg(rows)
            FROM (
                SELECT DISTINCT ON (name)
                    id,
                    name
                FROM profile_skill
                WHERE display_status = TRUE
                ORDER BY name
            ) AS rows
        """)
        params = ()
        cls.source.execute(query, params)
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        else:
            return None

    @classmethod
    def get_all_industries(cls,):
        query = ("""
            SELECT json_agg(rows) AS industries
            FROM (
                SELECT
                    id AS industry_id,
                    name AS industry_name
                FROM profile_industry
                WHERE display_status = TRUE
                ORDER BY name
            ) AS rows
        """)
        params = ()
        cls.source.execute(query, params)
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        else:
            return None

    @classmethod
    def _get_all_members(cls):
        members = list()
        query = ("""
            SELECT
                id,
                email,
                create_date,
                update_date,
                username,
                status,
                first_name,
                last_name,
                main_file_tree,
                bin_file_tree
            FROM member
        """)

        cls.source.execute(query, None)
        if cls.source.has_results():
            for (
                    member_id,
                    email,
                    create_date,
                    update_date,
                    username,
                    status,
                    first_name,
                    last_name,
                    main_file_tree,
                    bin_file_tree
            ) in cls.source.cursor:
                member = {
                    "member_id": member_id,
                    "email": email,
                    "create_date": create_date,
                    "update_date": update_date,
                    "username": username,
                    "status": status,
                    "first_name": first_name,
                    "last_name": last_name,
                    "member_name": f'{first_name} {last_name}',
                    "main_file_tree": main_file_tree,
                    "bin_file_tree": bin_file_tree
                }

                members.append(member)

        return members


class MemberContactDA(object):
    source = source

    @classmethod
    def get_member_contacts(cls, member_id, sort_params, filter_params, search_key='', page_size=None, page_number=None):
        sort_columns_string = 'first_name ASC'
        contact_dict = {
            'id': 'contact.id',
            'contact_member_id': 'contact.contact_member_id',
            'first_name': 'member.first_name',
            'middle_name': 'member.middle_name',
            'last_name': 'member.last_name',
            'biography': 'member_profile.biography',
            # 'cell_phone': 'contact.cell_phone',
            # 'office_phone': 'contact.office_phone',
            # 'home_phone': 'contact.home_phone',
            # 'email': 'contact.email',
            # 'personal_email': 'contact.personal_email',
            'company': 'member.company_name',
            'title': 'job_title.name',
            'country_code_id': 'location.country_code_id',
            'company_name': 'member.company_name',
            # 'company_phone': 'contact.company_phone',
            # 'company_web_site': 'contact.company_web_site',
            # 'company_email': 'contact.company_email',
            # 'company_bio': 'contact.company_bio',
            'role': 'role.name',
            'role_id': 'role.id',
            'create_date': 'contact.create_date',
            'update_date': 'contact.update_date',
            'status': 'contact.status',
            'online_status': 'member_session.status',
            'company_id': ''
        }

        if sort_params:
            sort_columns_string = formatSortingParams(
                sort_params, contact_dict) or sort_columns_string

        (filter_conditions_query, filter_conditions_params) = cls.formatFilterConditions(
            filter_params, contact_dict)
        get_contacts_params = (member_id, ) + filter_conditions_params
        contacts = list()

        get_contacts_search_query = """
        AND
        (
            lower(member.first_name) LIKE %s
            OR lower(member.middle_name) LIKE %s
            OR lower(member.last_name) LIKE %s
            OR lower(member_profile.biography) LIKE %s
            OR lower(member_contact_2.device) LIKE %s
            OR lower(job_title.name) LIKE %s
            OR lower(member.company_name) LIKE %s
            OR lower(company.name) LIKE %s
            OR lower(company.primary_url) LIKE %s
            OR lower(company.main_phone) LIKE %s
            OR lower(role.name) LIKE %s
        )
        """

        get_contacts_base_query = (f"""
            FROM contact
                LEFT JOIN member ON member.id = contact.contact_member_id
                LEFT JOIN role ON contact.role_id = role.id
                LEFT JOIN member_location ON member_location.member_id = contact.contact_member_id
                LEFT JOIN member_contact_2 ON member_contact_2.member_id = contact.contact_member_id
                LEFT JOIN country_code ON member_contact_2.device_country = country_code.id
                LEFT JOIN job_title ON member.job_title_id = job_title.id
                LEFT JOIN department ON member.department_id = department.id
                LEFT JOIN member_profile ON contact.contact_member_id = member_profile.member_id
                LEFT JOIN member_achievement ON member_achievement.member_id = member.id
                LEFT JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                LEFT JOIN online_sessions ON contact.contact_member_id  = online_sessions.member_id
                LEFT JOIN company_member ON company_member.member_id = member.id
                LEFT JOIN company ON company.id = company_member.company_id
                LEFT JOIN member_rate ON member_rate.member_id = member.id
                LEFT JOIN member_skill ON member_skill.member_id = member.id
                LEFT JOIN profile_skill ON profile_skill.id = member_skill.profile_skill_id
                LEFT JOIN member_workhistory ON member_workhistory.member_id = member.id
                LEFT JOIN member_education ON member_education.member_id = member.id
                LEFT JOIN member_certificate ON member_certificate.member_id = member.id
            WHERE
                contact.member_id = %s {filter_conditions_query}
                {get_contacts_search_query if search_key != "" else ''}
            GROUP BY
                member.id,
                contact.id,
                contact.contact_member_id,
                member_rate.pay_rate,
            	member_rate.currency_code_id,
                member.first_name,
                member.middle_name,
                member.last_name,
                member_profile.biography,
                member.email,
                member.company_name,
                job_title.name,
                department.name,
                role.name,
                role.id,
                contact.create_date,
                contact.update_date,
                file_storage_engine.storage_engine_id,
                contact.status,
                online_sessions.online_status
            """)

        if search_key != '':
            like_search_key = """%{}%""".format(search_key.lower())
            get_contacts_params = get_contacts_params + \
                tuple(11 * [like_search_key])

        get_contacts_query = (f"""
            WITH online_sessions AS (
                SELECT
                    member_session.member_id,
                    CASE WHEN bool_or(member_session.status = 'online' AND member_session.status is not null) = true THEN 'online' ELSE 'offline' END as online_status
                FROM  member_session
                WHERE
                    member_session.status IN ('online', 'disconnected') AND
                    member_session.expiration_date >= current_timestamp
                GROUP BY
                    member_session.member_id
            )
            SELECT
                contact.id as id,
                contact.contact_member_id as contact_member_id,
                CASE WHEN member_rate.pay_rate IS NOT NULL THEN member_rate.pay_rate ELSE 0 END as default_pay_rate,
                member_rate.currency_code_id,
                member.first_name as first_name,
                member.middle_name as middle_name,
                member.last_name as last_name,
                member_profile.biography as biography,
                member.email as email,
                member.company_name as company,
                job_title.name as title,
                department.name as department,
                (
                    SELECT json_agg(rows) AS group_memberships
                    FROM (
                        SELECT
                            member_group.id AS group_id,
                            group_name,
                            group_role
                        FROM member_group_membership
                        LEFT JOIN member_group ON member_group.id = member_group_membership.group_id
                        WHERE member_group_membership.status = 'active'
                        AND member_group_membership.member_id = contact.contact_member_id
                        AND member_group.group_type = 'contact'
                    ) AS rows
                ),
                -- company membership
                (
                    SELECT row_to_json(row) AS company_membership
                    FROM (
                        SELECT 
                            company.id,
                            company.parent_company_id,
                            company.name,
                            company.country_code_id,
                            company.main_phone,
                            company.main_phone_ext,
                            company.primary_url,
                            company.logo_storage_id,
                            company.email,
                            company.location_id,
                            location.admin_area_1,
                            location.admin_area_2,
                            location.locality,
                            location.sub_locality,
                            location.street_address_1,
                            location.street_address_2,
                            location.postal_code,
                            location.latitude,
                            location.longitude,
                            location.map_vendor,
                            location.map_link,
                            location.place_id,
                            ls.company_role,
                            ls.company_department_id,
                            ls.department_name,
                            ls.department_id,
                            ls.department_status,
                            ls.update_date AS status_update_date
                        FROM company_member
                        LEFT JOIN (
                            SELECT DISTINCT ON (company_member_id)
                                company_member_id,
                                company_role,
                                company_status,
                                company_department_id,
                                department.name AS department_name,
                                department.id AS department_id,
                                department_status,
                                company_member_status.update_date
                            FROM company_member_status
                            LEFT JOIN company_department ON company_department.id = company_member_status.company_department_id
                            LEFT JOIN department ON department.id = company_department.department_id
                            ORDER BY company_member_id, update_date DESC
                        ) AS ls ON ls.company_member_id = company_member.id
                        LEFT JOIN company ON company.id = company_member.company_id
                        LEFT JOIN location ON location.id = company.location_id
                        WHERE company_member.member_id = member.id
                        ORDER BY company_member.create_date DESC
                        LIMIT 1
                    ) AS row
                ),
                role.name as role,
                role.id as role_id,
                contact.create_date as create_date,
                contact.update_date as update_date,
                (
                    SELECT COALESCE(json_agg(rows), '[]'::json) AS location_information
                    FROM (
                        SELECT 
                            member_location.id,
                            member_location.location_type,
                            member_location.description,
                            member_location.location_id,
                            location.country_code_id,
                            country_code.name AS country_name,
                            location.admin_area_1,
                            location.admin_area_2,
                            location.locality,
                            location.sub_locality,
                            location.street_address_1,
                            location.street_address_2,
                            location.postal_code,
                            location.latitude,
                            location.longitude,
                            location.map_vendor,
                            location.map_link,
                            location.place_id
                        FROM member_location
                        LEFT JOIN location ON location.id = member_location.location_id
                        LEFT JOIN country_code ON country_code.id = location.country_code_id
                        WHERE member_id = member.id
                    ) AS rows
                ),
                COALESCE(json_agg(DISTINCT member_contact_2.*) FILTER (WHERE member_contact_2.id IS NOT NULL), '[]') AS contact_information,
                COALESCE(json_agg(DISTINCT country_code.*) FILTER (WHERE country_code.id IS NOT NULL), '[]') AS country_code,
                COALESCE(json_agg(DISTINCT member_achievement.*) FILTER (WHERE member_achievement.id IS NOT NULL), '[]') AS achievement_information,
                COALESCE(json_agg(DISTINCT profile_skill.*) FILTER (WHERE profile_skill.display_status = TRUE), '[]') AS skills_information,
                COALESCE(json_agg(DISTINCT member_workhistory.*), '[]') AS workhistory_information,
                COALESCE(json_agg(DISTINCT member_education.*), '[]') AS education_information,
                COALESCE(json_agg(DISTINCT member_certificate.*), '[]') AS certificate_information,
                file_storage_engine.storage_engine_id as s3_avatar_url,
                contact.security_exchange_option,
                contact.status,
                CASE WHEN online_sessions.online_status IS NOT NULL THEN online_sessions.online_status ELSE 'offline' END as online_status,
                -- Leaving the below for now
                COALESCE(json_agg(DISTINCT company.*) FILTER (WHERE company.id IS NOT NULL), '[]')->0->'id' as company_id,
                COALESCE(json_agg(DISTINCT company.*) FILTER (WHERE company.id IS NOT NULL), '[]')->0->'name' as member_company_name,
                COALESCE(json_agg(DISTINCT company.*) FILTER (WHERE company.id IS NOT NULL), '[]') AS companies
                {get_contacts_base_query}
            ORDER BY {sort_columns_string}
        """)

        get_contacts_count_query = (f"""
            WITH online_sessions AS (
                SELECT
                    member_session.member_id,
                    CASE WHEN bool_or(member_session.status = 'online' AND member_session.status is not null) = true THEN 'online' ELSE 'offline' END as online_status
                FROM  member_session
                WHERE
                    member_session.status IN ('online', 'disconnected') AND
                    member_session.expiration_date >= current_timestamp
                GROUP BY
                    member_session.member_id
            )

            SELECT COUNT(*)
                FROM (SELECT COUNT(DISTINCT contact.contact_member_id)
                {get_contacts_base_query}) as sq
        """)

        count = 0
        cls.source.execute(get_contacts_count_query, get_contacts_params)
        logger.debug(get_contacts_count_query)
        logger.debug(get_contacts_params)
        if cls.source.has_results():
            result = cls.source.cursor.fetchone()
            logger.debug(f"Result: {result}")
            (count, ) = result
            logger.debug(f"Count: {count}")
        if count > 0:
            if page_size and page_number >= 0:
                get_contacts_query += """LIMIT %s OFFSET %s"""
                offset = 0
                if page_number > 0:
                    offset = page_number * page_size
                get_contacts_params = get_contacts_params + (page_size, offset)

            logger.debug(get_contacts_query)
            cls.source.execute(get_contacts_query, get_contacts_params)
            if cls.source.has_results():
                for (
                        id,
                        contact_member_id,
                        default_pay_rate,
                        currency_code_id,
                        first_name,
                        middle_name,
                        last_name,
                        biography,
                        # cell_phone,
                        # office_phone,
                        # home_phone,
                        email,
                        # personal_email,
                        company,
                        title,
                        department,
                        # company_name,
                        # company_phone,
                        # company_web_site,
                        # company_email,
                        # company_bio,
                        group_memberships,
                        company_membership,
                        role,
                        role_id,
                        create_date,
                        update_date,
                        location_information,
                        contact_information,
                        country_code,
                        achievement_information,
                        skills_information,
                        workhistory_information,
                        education_information,
                        certificate_information,
                        s3_avatar_url,
                        security_exchange_option,
                        status,
                        online_status,
                        # all_statuses,
                        company_id,
                        member_company_name,
                        companies
                ) in cls.source.cursor:
                    contact = {
                        "id": id,
                        "contact_member_id": contact_member_id,
                        "default_pay_rate": default_pay_rate,
                        "currency_code_id": currency_code_id,
                        "first_name": first_name,
                        "middle_name": middle_name,
                        "last_name": last_name,
                        "member_name": f'{first_name} {last_name}',
                        "biography": biography,
                        # "cell_phone": cell_phone,
                        # "office_phone": office_phone,
                        # "home_phone": home_phone,
                        "email": email,
                        # "personal_email": personal_email,
                        "company": company,
                        "title": title,
                        "department": department,
                        # "company_name": company_name,
                        # "company_phone": company_phone,
                        # "company_web_site": company_web_site,
                        # "company_email": company_email,
                        # "company_bio": company_bio,
                        "group_memberships": group_memberships,
                        "company_membership": company_membership,
                        "role": role,
                        "role_id": role_id,
                        "create_date": create_date,
                        "update_date": update_date,
                        "location_information": location_information,
                        "contact_information": contact_information,
                        "country_code": country_code,
                        "achievement_information": achievement_information,
                        "skills_information": skills_information,
                        "workhistory_information": workhistory_information,
                        "education_information": education_information,
                        "certificate_information": certificate_information,
                        "amera_avatar_url": amerize_url(s3_avatar_url),
                        "security_exchange_option":
                            SECURITY_EXCHANGE_OPTIONS.get(
                                security_exchange_option, 0),
                        "status": status,
                        "online_status": online_status,
                        # "all_statuses": all_statuses,
                        "company_id": company_id,
                        "member_company_name": member_company_name,
                        "companies": companies

                        # "city": city,
                        # "state": state,
                        # "province": province,
                        # "country": country
                    }
                    contacts.append(contact)
        return {
            "contacts": contacts,
            "count": count
        }

    @classmethod
    def get_contacts_roles(cls, member_id):
        roles = list()
        query = (f"""
            SELECT role.id,
                   role.name,
                   count(*)
            FROM role
            INNER JOIN contact ON (role.id = contact.role_id)
            WHERE member_id = %s
            GROUP BY role.id,
                     role.name
            ORDER BY role.name
        """)
        params = (member_id, )
        cls.source.execute(query, params)
        if cls.source.has_results:
            for (
                role_id,
                contact_role,
                count
            ) in cls.source.cursor:
                role = {
                    "id": role_id,
                    "name": contact_role,
                    "count": count
                }
                roles.append(role)
        return roles

    @classmethod
    def get_contacts_companies(cls, member_id):
        companies = list()
        query = (f"""
            SELECT
                member.company_name,
                count(*)
            FROM
                member
                INNER JOIN contact ON member.id = contact.contact_member_id
            WHERE
                contact.member_id = %s
                AND member.company_name IS NOT NULL
                AND trim(member.company_name) != ''
            GROUP BY
                member.company_name
            ORDER BY
                member.company_name
        """)

        params = (member_id, )
        cls.source.execute(query, params)
        if cls.source.has_results:
            for (
                company_name,
                count
            ) in cls.source.cursor:
                company = {
                    "company_name": company_name,
                    "count": count
                }
                companies.append(company)

        return companies

    @classmethod
    def get_contacts_countries(cls, member_id):
        countries = list()
        query = (f"""
            SELECT
                country_code.id as id,
                country_code.name as name,
                count(*) as count
            FROM
                contact
                INNER JOIN member_location ON (contact.contact_member_id = member_location.member_id)
                INNER JOIN location ON member_location.location_id = location.id
                INNER JOIN country_code ON (location.country_code_id = country_code.id)
            WHERE
                contact.member_id = %s
            GROUP BY
                country_code.id,
                country_code.name
            ORDER BY
                country_code.name
        """)
        params = (member_id, )
        cls.source.execute(query, params)
        if cls.source.has_results:
            for (
                id,
                name,
                total
            ) in cls.source.cursor:
                country = {
                    "id": id,
                    "name": name,
                    "total": total
                }
                countries.append(country)
        return countries

    @classmethod
    def get_members(cls, member_id, sort_params, filter_params, search_key='', page_size=None, page_number=None):
        sort_columns_string = 'first_name ASC'
        member_dict = {
            'id': 'member.id',
            'first_name': 'member.first_name',
            'middle_name': 'member.middle_name',
            'last_name': 'member.last_name',
            'email': 'member.email',
            'company': 'member.company_name',
            'title': 'job_title.name',
            'contact_member_id': 'contact.contact_member_id'
        }

        if sort_params:
            sort_columns_string = formatSortingParams(
                sort_params, member_dict) or sort_columns_string

        # (filter_conditions_query, filter_conditions_params) = cls.formatFilterConditions(
        #     filter_params, member_dict)

        get_members_params = (member_id, member_id, )
        # + filter_conditions_params

        get_members_search_query = ""
        if search_key:
            get_members_search_query = """
                AND
                (
                    concat_ws('', member.first_name, member.last_name, member.last_name) iLIKE %s
                    OR member.email iLIKE %s
                    OR job_title.name iLIKE %s
                    OR member.company_name iLIKE %s
                )
            """
            like_search_key = """%{}%""".format(search_key)
            get_members_params = get_members_params + ((like_search_key, )*4)

        members = list()
        get_members_query = (f"""
                SELECT
                    member.id as id,
                    member.first_name as first_name,
                    member.middle_name as middle_name,
                    member.last_name as last_name,
                    member.email as email,
                    member.company_name as company,
                    job_title.name as title,
                    contact.contact_member_id as contact_member_id,
                    file_storage_engine.storage_engine_id as s3_avatar_url,
                   -- company membership
                    (
                        SELECT row_to_json(row) AS company_membership
                        FROM (
                            SELECT 
                                company.*,
                                ls.company_role,
                                ls.company_department_id,
                                ls.department_name,
                                ls.department_id,
                                ls.department_status,
                                ls.update_date AS status_update_date
                            FROM company_member
                            LEFT JOIN (
                                SELECT DISTINCT ON (company_member_id)
                                    company_member_id,
                                    company_role,
                                    company_status,
                                    company_department_id,
                                    department.name AS department_name,
                                    department.id AS department_id,
                                    department_status,
                                    company_member_status.update_date
                                FROM company_member_status
                                LEFT JOIN company_department ON company_department.id = company_member_status.company_department_id
                                LEFT JOIN department ON department.id = company_department.department_id
                                ORDER BY company_member_id, update_date DESC
                            ) AS ls ON ls.company_member_id = company_member.id
                            LEFT JOIN company ON company.id = company_member.company_id
                            WHERE company_member.member_id = member.id
                            ORDER BY company_member.create_date DESC
                            LIMIT 1
                        ) AS row
                    )
                FROM member
                LEFT JOIN contact ON (member.id = contact.contact_member_id AND contact.member_id = %s)
                LEFT OUTER JOIN job_title ON member.job_title_id = job_title.id
                LEFT OUTER JOIN member_profile ON member.id = member_profile.member_id
                LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                WHERE 
                    member.id <> %s 
                    AND contact.contact_member_id IS NULL
                    {get_members_search_query}
                ORDER BY {sort_columns_string}
                """)

        countQuery = (f"SELECT COUNT(*) FROM ({get_members_query}) src;")

        count = 0
        cls.source.execute(countQuery, get_members_params)
        if cls.source.has_results():
            result = cls.source.cursor.fetchone()
            (count, ) = result
        if count > 0:
            if page_size and page_number >= 0:
                get_members_query += """LIMIT %s OFFSET %s"""
                offset = 0
                if page_number > 0:
                    offset = page_number * page_size
                get_members_params = get_members_params + (page_size, offset)

        cls.source.execute(get_members_query, get_members_params)
        if cls.source.has_results():
            for (
                    id,
                    first_name,
                    middle_name,
                    last_name,
                    email,
                    company,
                    title,
                    contact_member_id,
                    s3_avatar_url,
                    company_membership
            ) in cls.source.cursor:
                member = {
                    "id": id,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "email": email,
                    "company": company,
                    "title": title,
                    "contact_member_id": contact_member_id,
                    "amera_avatar_url": amerize_url(s3_avatar_url),
                    "company_membership": company_membership
                }
                members.append(member)
        return {
            "members": members,
            "count": count
        }

    @classmethod
    def formatFilterConditions(cls, filter_by, entity_dict):
        filter_by_dict = parse.parse_qs(filter_by)
        filter_conditions_query = ''
        filter_conditions_params = []
        for key in filter_by_dict:
            filter_conditions_query = filter_conditions_query + \
                (f""" and {entity_dict.get(key)} = %s""")
            param = None
            # try:
            #     param = int(filter_by_dict[key][0])
            # except ValueError:
            # param = filter_by_dict[key][0]
            param = filter_by_dict[key][0]

            filter_conditions_params.append(param)
        return (filter_conditions_query, tuple(filter_conditions_params))

    @classmethod
    def map_member_table(cls, column_name):
        return

    @classmethod
    def map_contact_table(cls, column_name):
        return

    @classmethod
    def get_member_contact(cls, contact_id):
        contact = cls.__get_member_contact('contact.id', contact_id)
        return contact

    @classmethod
    def get_member_contact_by_email(cls, email):
        return cls.__get_member_contact('contact.email', email)

    @classmethod
    def get_member_contact_by_member_id(cls, member_id):
        return cls.__get_member_contact("contact.contact_member_id", member_id)

    @classmethod
    def __get_member_contact(cls, key, value):
        get_contact_query = ("""
            SELECT contact.id as id,
                contact.contact_member_id as contact_member_id,
                contact.status as status,
                contact.first_name as first_name,
                member.middle_name as middle_name,
                contact.last_name as last_name,
                contact.cell_phone as cell_phone,
                contact.office_phone as office_phone,
                contact.home_phone as home_phone,
                contact.email as email,
                contact.personal_email as personal_email,
                member.company_name as company,
                job_title.name as title,
                contact.company_name as company_name,
                contact.company_phone as company_phone,
                contact.company_web_site as company_web_site,
                contact.company_email as company_email,
                contact.company_bio as company_bio,
                contact.contact_role as role,
                contact.create_date as create_date,
                contact.update_date as update_date,
                COALESCE(json_agg(DISTINCT member_location.*) FILTER (WHERE member_location.id IS NOT NULL), '[]') AS location_information,
                COALESCE(json_agg(DISTINCT member_contact_2.*) FILTER (WHERE member_contact_2.id IS NOT NULL), '[]') AS contact_information,
                COALESCE(json_agg(DISTINCT country_code.*) FILTER (WHERE country_code.id IS NOT NULL), '[]') AS country_code,
                file_storage_engine.storage_engine_id as s3_avatar_url,
                contact.security_exchange_option
            FROM contact
                LEFT JOIN member ON member.id = contact.contact_member_id
                LEFT OUTER JOIN member_location ON member_location.member_id = contact.contact_member_id
                LEFT OUTER JOIN member_contact ON member_contact.member_id = contact.contact_member_id
                LEFT OUTER JOIN member_contact_2 ON member_contact_2.member_id = contact.contact_member_id
                LEFT OUTER JOIN country_code ON member_contact_2.device_country = country_code.id
                LEFT OUTER JOIN job_title ON job_title.id = member.job_title_id
                LEFT OUTER JOIN member_profile ON contact.contact_member_id = member_profile.member_id
                LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
            WHERE {} = %s
            GROUP BY
                contact.contact_member_id,
                contact.id,
                contact.contact_member_id,
                contact.first_name,
                member.middle_name,
                contact.last_name,
                contact.cell_phone,
                contact.office_phone,
                contact.home_phone,
                contact.email,
                contact.personal_email,
                member.company_name,
                job_title.name,
                contact.company_name,
                contact.company_phone,
                contact.company_web_site,
                contact.company_email,
                contact.company_bio,
                contact.contact_role,
                contact.create_date,
                contact.update_date,
                file_storage_engine.storage_engine_id,
                security_exchange_option
            """.format(key))

        get_contact_params = (value,)
        cls.source.execute(get_contact_query, get_contact_params)
        if cls.source.has_results():
            for (
                    id,
                    contact_member_id,
                    status,
                    first_name,
                    middle_name,
                    last_name,
                    cell_phone,
                    office_phone,
                    home_phone,
                    email,
                    personal_email,
                    company,
                    title,
                    company_name,
                    company_phone,
                    company_web_site,
                    company_email,
                    company_bio,
                    role,
                    create_date,
                    update_date,
                    location_information,
                    contact_information,
                    country_code,
                    s3_avatar_url,
                    security_exchange_option
            ) in cls.source.cursor:
                contact = {
                    "id": id,
                    "contact_member_id": contact_member_id,
                    "status": status,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "member_name": f'{first_name} {last_name}',
                    "cell_phone": cell_phone,
                    "office_phone": office_phone,
                    "home_phone": home_phone,
                    "email": email,
                    "company": company,
                    "title": title,
                    "company_name": company_name,
                    "company_phone": company_phone,
                    "company_web_site": company_web_site,
                    "company_email": company_email,
                    "company_bio": company_bio,
                    "role": role,
                    "create_date": create_date,
                    "update_date": update_date,
                    "location_information": location_information,
                    "contact_information": contact_information,
                    "country_code": country_code,
                    "amera_avatar_url": amerize_url(s3_avatar_url),
                    "security_exchange_option":
                        SECURITY_EXCHANGE_OPTIONS.get(
                            security_exchange_option, 0),
                }

                return contact

        return None

    @classmethod
    def create_member_contact(cls, member_id, contact_member_id, status, role_id=None,
                              first_name=None, last_name=None, country=None, 
                              cell_phone=None, office_phone=None, home_phone=None,
                              email=None, personal_email=None, company_name=None,
                              company_phone=None, company_web_site=None,
                              company_email=None, company_bio=None, contact_role=None,
                              commit=True):
        create_member_contact_query = ("""
                    INSERT INTO contact
                        (member_id, contact_member_id, status, first_name, last_name,
                        country, cell_phone, office_phone, home_phone,
                        email, personal_email, company_name, company_phone,
                        company_web_site, company_email, company_bio,
                        contact_role, role_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """)

        create_member_contact_params = (
            member_id, contact_member_id, status, first_name, last_name, country, cell_phone, office_phone,
            home_phone, email, personal_email, company_name, company_phone,
            company_web_site, company_email, company_bio, contact_role, role_id
        )

        try:
            cls.source.execute(create_member_contact_query,
                               create_member_contact_params)
            contact_id = cls.source.get_last_row_id()

            if commit:
                cls.source.commit()
            return contact_id
        except Exception as e:
            raise e

    @classmethod
    def update_member_contact_role(cls, contact_id, contact_role_id, contact_role, commit=True):
        query = ("""
        UPDATE contact SET
            role_id = %s,
            contact_role = %s,
            update_date = CURRENT_TIMESTAMP
        WHERE id = %s
        """)
        params = (
            contact_role_id, contact_role, contact_id
        )
        try:
            cls.source.execute(query, params)

            if commit:
                cls.source.commit()
        except DataMissingError as err:
            raise DataMissingError from err

    @classmethod
    def delete_contact(cls, contact_id, commit=True):
        query = """
            DELETE FROM contact
            WHERE id = %s
        """
        params = (contact_id,)
        try:
            cls.source.execute(query, params)

            if commit:
                cls.source.commit()
        except Exception as err:
            raise err

    @classmethod
    def get_security(cls, member_id, contact_member_id):
        query = """
            SELECT contact.security_pin, contact.security_exchange_status,
                contact.security_exchange_option,
                contact.security_picture_storage_id,
                file_storage_engine.storage_engine_id as security_picture
            FROM contact
                LEFT OUTER JOIN file_storage_engine ON contact.security_picture_storage_id = file_storage_engine.id
            WHERE
            member_id = %s AND contact_member_id = %s;
        """
        params = (member_id, contact_member_id)
        cls.source.execute(query, params)
        if cls.source.has_results():
            (
                security_pin,
                security_exchange_status,
                security_exchange_option,
                security_picture_storage_id,
                security_picture,
            ) = cls.source.cursor.fetchone()
            return {
                "security_exchange_status": security_exchange_status,
                "security_picture_storage_id": security_picture_storage_id,
                "pin": security_pin,
                "exchange_option": security_exchange_option,
                "security_picture": amerize_url(security_picture)
            }
        return None

    @classmethod
    def update_security(cls, member_id, contact_member_id,
                        security_picture_storage_id, security_pin, exchangeOption, commit=True):
        query = """
            UPDATE contact SET
                security_exchange_status = %s,
                security_exchange_option = %s,
                security_pin = %s,
                security_picture_storage_id = %s,
                update_date = CURRENT_TIMESTAMP
            WHERE
                member_id = %s AND contact_member_id = %s;
        """
        params = ('requested', exchangeOption,
                  security_pin, security_picture_storage_id, member_id, contact_member_id)

        try:
            cls.source.execute(query, params)

            if commit:
                cls.source.commit()
        except Exception as err:
            raise err

        params = ('pending', exchangeOption,
                  security_pin, security_picture_storage_id,
                  contact_member_id, member_id)

        try:
            cls.source.execute(query, params)
            if commit:
                cls.source.commit()
        except Exception as err:
            raise err

    @classmethod
    def accept_invitation(cls, member_id, contact_member_id,
                          status, commit=True):
        query = """
            UPDATE contact SET
                status = %s,
                update_date = CURRENT_TIMESTAMP
            WHERE
                member_id = %s AND contact_member_id = %s;
        """
        params = (status, member_id, contact_member_id)

        try:
            cls.source.execute(query, params)

            if commit:
                cls.source.commit()
        except Exception as err:
            raise err

        params = (status, contact_member_id, member_id)

        try:
            cls.source.execute(query, params)
            if commit:
                cls.source.commit()
        except Exception as err:
            raise err

    @classmethod
    def get_all_contact_invitations_by_member_id(cls, member_id, is_history=False):
        contacts = list()

        try:
            pending = ""

            if not is_history:
                pending = " AND receiver_contact.status = 'pending'"

            query = f"""
                SELECT
                    receiver_contact.id,
                    receiver_contact.status,
                    receiver_contact.create_date,
                    receiver_contact.update_date,
                    member.id as create_user_id,
                    member.first_name,
                    member.last_name,
                    member.email,
                    COALESCE(company.name, member.company_name) as company,
                    member.job_title_id as job_title_id,
                    member.department_id as department_id,
                    contact.id as requester_contact_id,
                    contact.security_exchange_option,
                    job_title.name as job_title,
                    department.name as department_name,
                    COALESCE(json_agg(DISTINCT member_location.*) FILTER (WHERE member_location.id IS NOT NULL), '[]') AS location_information,
                    COALESCE(json_agg(DISTINCT member_contact_2.*) FILTER (WHERE member_contact_2.id IS NOT NULL), '[]') AS contact_information,
                    COALESCE(json_agg(DISTINCT country_code.*) FILTER (WHERE country_code.id IS NOT NULL), '[]') AS country_code,
                    COALESCE(json_agg(DISTINCT member_achievement.*) FILTER (WHERE member_achievement.id IS NOT NULL), '[]') AS achievement_information,
                    COALESCE(json_agg(DISTINCT profile_skill.*) FILTER (WHERE profile_skill.display_status = TRUE), '[]') AS skills_information,
                    COALESCE(json_agg(DISTINCT member_workhistory.*), '[]') AS workhistory_information, 
                    COALESCE(json_agg(DISTINCT member_education.*), '[]') AS education_information,
                    COALESCE(json_agg(DISTINCT member_certificate.*), '[]') AS certificate_information,
                    member_profile.biography as biography,
                    member_security_preferences.facial_recognition as facial_recognition,
                    member_rate.pay_rate,
                    member_rate.currency_code_id,
                    currency_code.currency_code,
                    file_storage_engine.storage_engine_id
                FROM contact
                INNER JOIN contact receiver_contact ON
                        contact.contact_member_id = receiver_contact.member_id
                    AND contact.member_id = receiver_contact.contact_member_id
                INNER JOIN member ON contact.member_id = member.id
                LEFT JOIN member_profile ON member.id = member_profile.member_id
                LEFT JOIN file_storage_engine on file_storage_engine.id = member_profile.profile_picture_storage_id
                LEFT OUTER JOIN job_title ON job_title.id = member.job_title_id
                LEFT OUTER JOIN member_contact_2 ON member_contact_2.member_id = member.id
                LEFT OUTER JOIN country_code ON country_code.id = member_contact_2.device_country
                LEFT OUTER JOIN member_location ON member_location.member_id = member.id
                LEFT OUTER JOIN member_achievement ON member_achievement.member_id = member.id
                LEFT OUTER JOIN member_security_preferences ON member_security_preferences.member_id = member.id 
                LEFT JOIN member_rate ON member_rate.member_id = member.id
                LEFT JOIN member_skill ON member_skill.member_id = member.id
                LEFT JOIN profile_skill ON profile_skill.id = member_skill.profile_skill_id
                LEFT JOIN member_workhistory ON member_workhistory.member_id = member.id
                LEFT JOIN member_education ON member_education.member_id = member.id
                LEFT JOIN member_certificate ON member_certificate.member_id = member.id
                LEFT JOIN department ON department.id = member.department_id
                LEFT JOIN currency_code ON currency_code.id = member_rate.currency_code_id
                LEFT JOIN company_member ON company_member.member_id = member.id
                LEFT JOIN company ON company_member.company_id=company.id
                WHERE 
                    receiver_contact.member_id = %s
                    {pending}
                GROUP BY
                    receiver_contact.id,
                    member.id,
                    contact.id,
                    company.name,
                    member.company_name,
                    member.job_title_id,
                    job_title.name,
                    department.name,
                    member.department_id,
                    receiver_contact.create_date,
                    receiver_contact.update_date,
                    file_storage_engine.storage_engine_id,
                    member_profile.biography,
                    member_security_preferences.facial_recognition,
                    member_rate.pay_rate,
                    member_rate.currency_code_id,
                    currency_code.currency_code
                ORDER BY receiver_contact.update_date DESC
                LIMIT 25
            """

            params = (member_id,)

            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                        id,
                        status,
                        create_date,
                        update_date,
                        create_user_id,
                        first_name,
                        last_name,
                        email,
                        company,
                        job_title_id,
                        department_id,
                        requester_contact_id,
                        security_exchange_option,
                        job_title,
                        department_name,
                        location_information,
                        contact_information,
                        country_code,
                        achievement_information,
                        skills_information,
                        workhistory_information,
                        education_information,
                        certificate_information,
                        biography,
                        facial_recognition,
                        pay_rate,
                        currency_code_id,
                        currency_code,
                        storage_engine_id,
                ) in cls.source.cursor:
                    contact = {
                        "id": id,
                        "status": status,
                        "create_date": create_date,
                        "update_date": update_date,
                        "create_user_id": create_user_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "company": company,
                        "job_title_id": job_title_id,
                        "department_id": department_id,
                        "requester_contact_id": requester_contact_id,
                        "security_exchange_option": SECURITY_EXCHANGE_OPTIONS.get(security_exchange_option, 0),
                        "job_title": job_title,
                        "department_name": department_name,
                        "location_information": location_information,
                        "contact_information": contact_information,
                        "country_code": country_code,
                        "achievement_information": achievement_information,
                        "skills_information": skills_information,
                        "workhistory_information": workhistory_information,
                        "education_information": education_information,
                        "certificate_information": certificate_information,
                        "biography": biography,
                        "facial_recognition": facial_recognition,
                        "pay_rate": pay_rate,
                        "currency_code_id": currency_code_id,
                        "currency_code": currency_code,
                        "amera_avatar_url": amerize_url(storage_engine_id),
                        "invitation_type": "contact_invitation"
                    }
                    contacts.append(contact)

            return contacts
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    @classmethod
    def get_member_cell(cls, member_id):
        query = ("""
        SELECT CONCAT(phone,device) AS cell
        FROM member_contact_2
        LEFT JOIN country_code ON country_code.id = device_country
        WHERE device_type = 'cell' AND device_confirm_date IS NOT NULL AND enabled= TRUE AND member_id = %s
        LIMIT 1
        """)
        cls.source.execute(query, (member_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        else:
            return None


class MemberInfoDA(object):
    source = source

    def get_member_info(cls, member_id):
        get_member_info_query = ("""
           SELECT
                member.first_name as first_name,
                member.middle_name as middle_name,
                member.last_name as last_name,
                member.email as email,
                member.company_name as company,
                -- company membership
                (
                    SELECT row_to_json(row) AS company_membership
                    FROM (
                        SELECT 
                            company.name AS company_name,
                            company_member.company_id,
                            ls.company_role,
                            ls.company_department_id,
                            ls.department_name,
                            ls.department_id,
                            ls.department_status,
                            ls.update_date AS status_update_date
                        FROM company_member
                        LEFT JOIN (
                            SELECT DISTINCT ON (company_member_id)
                                company_member_id,
                                company_role,
                                company_status,
                                company_department_id,
                                department.name AS department_name,
                                department.id AS department_id,
                                department_status,
                                company_member_status.update_date
                            FROM company_member_status
                            LEFT JOIN company_department ON company_department.id = company_member_status.company_department_id
                            LEFT JOIN department ON department.id = company_department.department_id
                            ORDER BY company_member_id, update_date DESC
                        ) AS ls ON ls.company_member_id = company_member.id
                        LEFT JOIN company ON company.id = company_member.company_id
                        WHERE company_member.member_id = member.id
                        ORDER BY company_member.create_date DESC
                        LIMIT 1
                    ) AS row
                ),
                member.job_title_id as job_title_id,
                job_title.name as job_title,
                member.department_id as department_id,
                department.name as department_name,
                member.create_date as create_date,
                member.update_date as update_date,
                (
                    SELECT COALESCE(json_agg(rows), '[]'::json) AS location_information
                    FROM (
                        SELECT 
                            member_location.id,
                            member_location.location_type,
                            member_location.description,
                            member_location.location_id,
                            location.country_code_id,
                            location.vendor_formatted_address,
                            country_code.name AS country_name,
                            location.admin_area_1,
                            location.admin_area_2,
                            location.locality,
                            location.sub_locality,
                            location.street_address_1,
                            location.street_address_2,
                            location.postal_code,
                            location.latitude,
                            location.longitude,
                            location.map_vendor,
                            location.map_link,
                            location.place_id
                        FROM member_location
                        LEFT JOIN location ON location.id = member_location.location_id
                        LEFT JOIN country_code ON country_code.id = location.country_code_id
                        WHERE member_id = member.id
                    ) AS rows
                ),
                COALESCE(json_agg(DISTINCT member_contact_2.*) FILTER (WHERE member_contact_2.id IS NOT NULL), '[]') AS contact_information,
                COALESCE(json_agg(DISTINCT country_code.*) FILTER (WHERE country_code.id IS NOT NULL), '[]') AS country_code,
                COALESCE(json_agg(DISTINCT member_achievement.*) FILTER (WHERE member_achievement.id IS NOT NULL), '[]') AS achievement_information,
                COALESCE(json_agg(DISTINCT profile_skill.*) FILTER (WHERE profile_skill.display_status = TRUE), '[]') AS skills_information,
                COALESCE(json_agg(DISTINCT member_workhistory.*), '[]') AS workhistory_information,
                COALESCE(json_agg(DISTINCT member_education.*), '[]') AS education_information,
                COALESCE(json_agg(DISTINCT member_certificate.*), '[]') AS certificate_information,
                file_storage_engine.storage_engine_id as s3_avatar_url,
                member_profile.biography as biography,
                member_security_preferences.facial_recognition as facial_recognition,
                member_rate.pay_rate,
                member_rate.currency_code_id,
                currency_code.currency_code
            FROM member
                LEFT JOIN job_title ON member.job_title_id = job_title.id
                LEFT JOIN member_location ON member_location.member_id = member.id
                LEFT JOIN member_contact ON member_contact.member_id = member.id
                LEFT JOIN member_contact_2 ON member_contact_2.member_id = member.id
                LEFT JOIN country_code ON member_contact_2.device_country = country_code.id
                LEFT JOIN member_achievement ON member_achievement.member_id = member.id
                LEFT JOIN member_profile ON member.id = member_profile.member_id
                LEFT JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                LEFT JOIN member_security_preferences ON member.id = member_security_preferences.member_id
                LEFT JOIN member_rate ON member.id = member_rate.member_id
                LEFT JOIN member_skill ON member_skill.member_id = member.id
                LEFT JOIN profile_skill ON profile_skill.id = member_skill.profile_skill_id
                LEFT JOIN member_workhistory ON member_workhistory.member_id = member.id
                LEFT JOIN member_education ON member_education.member_id = member.id
                LEFT JOIN member_certificate ON member_certificate.member_id = member.id
                LEFT JOIN department ON department.id = member.department_id
                LEFT JOIN currency_code ON currency_code.id = member_rate.currency_code_id
            WHERE member.id = %s
            GROUP BY
                member.id,
                member.first_name,
                member.middle_name,
                member.last_name,
                member.email,
                member.company_name,
                member.job_title_id,
                job_title.name,
                department.name,
                member.department_id,
                member.create_date,
                member.update_date,
                file_storage_engine.storage_engine_id,
                member_profile.biography,
                member_security_preferences.facial_recognition,
                member_rate.pay_rate,
                member_rate.currency_code_id,
                currency_code.currency_code
            """)
        get_member_info_params = (member_id,)
        cls.source.execute(get_member_info_query, get_member_info_params)
        if cls.source.has_results():
            for (
                    first_name,
                    middle_name,
                    last_name,
                    email,
                    company,
                    company_membership,
                    job_title_id,
                    job_title,
                    department_id,
                    department_name,
                    create_date,
                    update_date,
                    location_information,
                    contact_information,
                    country_code,
                    achievement_information,
                    skills_information,
                    workhistory_information,
                    education_information,
                    certificate_information,
                    s3_avatar_url,
                    biography,
                    facial_recognition,
                    pay_rate,
                    currency_code_id,
                    currency_code
            ) in cls.source.cursor:
                member = {
                    "member_id": member_id,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "email": email,
                    "company_name": company,
                    "company_membership": company_membership,
                    "job_title_id": job_title_id,
                    "job_title": job_title,
                    "department_id": department_id,
                    "department_name": department_name,
                    "create_date": create_date,
                    "update_date": update_date,
                    "location_information": location_information,
                    "contact_information": contact_information,
                    "country_code": country_code,
                    "achievement_information": achievement_information,
                    "skills_information": skills_information,
                    "workhistory_information": workhistory_information,
                    "education_information": education_information,
                    "certificate_information": certificate_information,
                    "amera_avatar_url": amerize_url(s3_avatar_url),
                    "biography": biography,
                    "facial_recognition": facial_recognition,
                    "pay_rate": pay_rate,
                    "currency_code_id": currency_code_id,
                    "currency_code": currency_code
                }

                return member

    @classmethod
    def update_member_info(cls, member_id, member, member_profile, member_achievement, member_contact_2, member_locations):
        #  Member table
        first_name, middle_name, last_name, company_name, job_title_id, department_id = [
            member[k] for k in ('first_name', 'middle_name', 'last_name', 'company_name', 'job_title_id', 'department_id')]

        member_query = ("""
            UPDATE member
            SET
                first_name = %s,
                middle_name = %s,
                last_name = %s,
                company_name = %s,
                job_title_id = %s,
                department_id = %s,
                update_date = CURRENT_TIMESTAMP
            WHERE id = %s
        """)

        member_params = (first_name, middle_name, last_name,
                         company_name, job_title_id, department_id, member_id)

        cls.source.execute(member_query, member_params)
        cls.source.commit()

        # Member_profile
        member_profile_query = ("""
            INSERT INTO member_profile (member_id, biography)
            VALUES (%s, %s)
            ON conflict(member_id) DO UPDATE
            SET biography = %s, update_date = CURRENT_TIMESTAMP
        """)

        member_profile_params = (
            member_id, member_profile["biography"], member_profile["biography"])
        cls.source.execute(member_profile_query, member_profile_params)
        cls.source.commit()

        # Member achievements
        member_achievement_update_query = ("""
            UPDATE member_achievement
            SET
                entity = %s,
                description = %s,
                display_order = %s,
                update_date = CURRENT_TIMESTAMP
            WHERE id=%s AND member_id=%s;
        """)
        member_achievement_insert_query = ("""
            INSERT INTO member_achievement (entity, description, display_order, member_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id;
        """)
        member_achievement_delete_query = ("""
            DELETE FROM member_achievement
            WHERE member_id = %s AND NOT id = ANY(%s);
        """)

        if member_achievement:
            achievement_ids_to_stay = list()
            for achievement in member_achievement:
                if achievement:
                    id_, entity, description, display_order = [
                        achievement[k] for k in ('id', 'entity', 'description', 'display_order')]
                    if type(id_) == int:
                        cls.source.execute(
                            member_achievement_update_query, (entity, description, display_order, id_, member_id))
                        achievement_ids_to_stay.append(id_)
                    else:
                        cls.source.execute(
                            member_achievement_insert_query, (entity, description, display_order, member_id))
                        achievement_ids_to_stay.append(
                            cls.source.get_last_row_id())
                    cls.source.commit()
            # Track what was deleted in the UI and kill it in db as well
            cls.source.execute(member_achievement_delete_query,
                               (member_id, achievement_ids_to_stay))
            cls.source.commit()

        # Member contact 2
        member_contact_2_update_query = ("""
            UPDATE member_contact_2
            SET
                description = %s,
                device_type = %s,
                device_country = %s,
                device = %s,
                method_type = %s,
                display_order = %s,
                primary_contact = %s,
                device_confirm_date = CURRENT_TIMESTAMP,
                update_date = CURRENT_TIMESTAMP
            WHERE id = %s AND member_id = %s;
        """)
        member_contact_2_insert_query = ("""
            INSERT INTO member_contact_2 (description, device_type, device_country, device, method_type, display_order, primary_contact, device_confirm_date, member_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s)
            RETURNING id;
        """)
        member_contact_2_delete_query = ("""
            DELETE FROM member_contact_2
            WHERE member_id = %s AND NOT id = ANY(%s);
        """)

        if member_contact_2:
            contact_ids_to_stay = list()
            for contact in member_contact_2:
                if contact:
                    id_, description, device_type, device_country, device, method_type, display_order, primary_contact = [
                        contact[k] for k in ('id', 'description', 'device_type', 'device_country', 'device', 'method_type', 'display_order', 'primary_contact')]
                    if (type(id_) == int):
                        cls.source.execute(
                            member_contact_2_update_query, (description, device_type, device_country, device, method_type, display_order, primary_contact, id_, member_id))
                        contact_ids_to_stay.append(id_)
                    else:
                        cls.source.execute(
                            member_contact_2_insert_query, (description, device_type, device_country, device, method_type, display_order, primary_contact, member_id))
                        contact_ids_to_stay.append(
                            cls.source.get_last_row_id())
                    cls.source.commit()
            # Track what was deleted in the UI and kill it in db as well
            cls.source.execute(member_contact_2_delete_query,
                               (member_id, contact_ids_to_stay))
            cls.source.commit()

        # Member location
        logger.debug(f"member locations {member_locations}")
        cls.handle_member_locations(member_locations, member_id)
        # if member_locations:
        #     location_ids_to_stay = list()
        #     for member_location in member_locations:
        #         logger.debug(f"item {member_location}")
        #         if member_location:
        #             id_, country_code_id, location_type, admin_area_1, admin_area_2, locality, sub_locality, street_address_1, street_address_2, postal_code, latitude, longitude, map_vendor, map_link, place_id, vendor_formatted_address, description = [
        #                 member_location[k] for k in ('id', 'country_code_id', 'location_type', 'admin_area_1', 'admin_area_2', 'locality', 'sub_locality', 'street_address_1', 'street_address_2', 'postal_code', 'latitude', 'longitude', 'map_vendor', 'map_link', 'place_id', 'vendor_formatted_address', 'description')]

        #             location_params = {"country_code_id": country_code_id,
        #                                "admin_area_1": json.convert_null(admin_area_1),
        #                                "admin_area_2": json.convert_null(admin_area_2),
        #                                "locality": json.convert_null(locality),
        #                                "sub_locality": json.convert_null(sub_locality),
        #                                "street_address_1": json.convert_null(street_address_1),
        #                                "street_address_2": json.convert_null(street_address_2),
        #                                "postal_code": json.convert_null(postal_code),
        #                                "latitude": json.convert_null(latitude),
        #                                "longitude": json.convert_null(longitude),
        #                                "map_vendor": json.convert_null(map_vendor),
        #                                "map_link": json.convert_null(map_link),
        #                                "place_id": json.convert_null(place_id),
        #                                "vendor_formatted_address": json.convert_null(vendor_formatted_address)}
        #             location_id = LocationDA.insert_location(
        #                 location_params)

        #             if (type(id_) == int):
        #                 logger.info(f"Will update member_location {id_}")
        #                 cls.update_member_location({
        #                     "location_type": location_type,
        #                     "member_location_id": id_,
        #                     "location_id": location_id,
        #                     "member_id": member_id,
        #                     "description": description
        #                 })
        #                 location_ids_to_stay.append(id_)
        #             else:
        #                 logger.info(f"Will insert member_location {id_}")
        #                 inserted = cls.create_member_location({
        #                     "location_type": location_type,
        #                     "member_id": member_id,
        #                     "location_id": location_id,
        #                     "description": description
        #                 })
        #                 location_ids_to_stay.append(inserted)
        #     # Track what was deleted in the UI and kill it in db as well
        #     cls.delete_member_location(member_id, location_ids_to_stay)
        # return True

    @classmethod
    def create_member_location(cls, params, commit=True):
        query = ("""
            INSERT INTO member_location (location_type, member_id, location_id, description)
            VALUES ( %(location_type)s, %(member_id)s, %(location_id)s, %(description)s)
            RETURNING id;
        """)
        cls.source.execute(query, params)

        if commit:
            cls.source.commit()
        id = cls.source.get_last_row_id()
        if id:
            return id
        else:
            return None

    @classmethod
    def update_member_location(cls, params, commit=True):
        query = ("""
            UPDATE member_location
            SET
                location_type = %(location_type)s,
                location_id = %(location_id)s,
                description = %(description)s
            WHERE id=%(member_location_id)s AND member_id = %(member_id)s;
        """)
        cls.source.execute(query, params)
        if commit:
            cls.source.commit()

    @classmethod
    def delete_member_location(cls, member_id, location_ids_to_stay, commit=True):
        query = ("""
            DELETE FROM member_location
            WHERE member_id = %s AND NOT id = ANY(%s);
        """)
        cls.source.execute(query, (member_id, location_ids_to_stay))
        if commit:
            cls.source.commit()

    @classmethod
    def handle_member_locations(cls, member_locations, member_id, commit=True):
        if member_locations:
            location_ids_to_stay = list()
            for member_location in member_locations:
                logger.debug(f"item {member_location}")
                if member_location:
                    id_, country_code_id, location_type, admin_area_1, admin_area_2, locality, sub_locality, street_address_1, street_address_2, postal_code, latitude, longitude, map_vendor, map_link, place_id, vendor_formatted_address, description = [
                        member_location[k] for k in ('id', 'country_code_id', 'location_type', 'admin_area_1', 'admin_area_2', 'locality', 'sub_locality', 'street_address_1', 'street_address_2', 'postal_code', 'latitude', 'longitude', 'map_vendor', 'map_link', 'place_id', 'vendor_formatted_address', 'description')]

                    location_params = {"country_code_id": country_code_id,
                                       "admin_area_1": json.convert_null(admin_area_1),
                                       "admin_area_2": json.convert_null(admin_area_2),
                                       "locality": json.convert_null(locality),
                                       "sub_locality": json.convert_null(sub_locality),
                                       "street_address_1": json.convert_null(street_address_1),
                                       "street_address_2": json.convert_null(street_address_2),
                                       "postal_code": json.convert_null(postal_code),
                                       "latitude": json.convert_null(latitude),
                                       "longitude": json.convert_null(longitude),
                                       "map_vendor": json.convert_null(map_vendor),
                                       "map_link": json.convert_null(map_link),
                                       "place_id": json.convert_null(place_id),
                                       "vendor_formatted_address": json.convert_null(vendor_formatted_address)}
                    location_id = LocationDA.insert_location(
                        location_params)

                    if (type(id_) == int):
                        logger.info(f"Will update member_location {id_}")
                        cls.update_member_location({
                            "location_type": location_type,
                            "member_location_id": id_,
                            "location_id": location_id,
                            "member_id": member_id,
                            "description": description
                        })
                        location_ids_to_stay.append(id_)
                    else:
                        logger.info(f"Will insert member_location {id_}")
                        inserted = cls.create_member_location({
                            "location_type": location_type,
                            "member_id": member_id,
                            "location_id": location_id,
                            "description": description
                        })
                        location_ids_to_stay.append(inserted)
            # Track what was deleted in the UI and kill it in db as well
            cls.delete_member_location(member_id, location_ids_to_stay)
        return True

    @classmethod
    def get_member_skills(cls, member_id):
        query = ("""
            SELECT ARRAY(
                SELECT profile_skill_id FROM member_skill WHERE member_id =%s
            )
        """)
        cls.source.execute(query, (member_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return []

    @classmethod
    def add_skill(cls, member_id, skill_id):
        query = ("""
            INSERT INTO member_skill (member_id, profile_skill_id)
            VALUES (%s, %s)
        """)
        params = (member_id, skill_id)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def unlist_skill(cls, member_id, skill_id):
        query = ("""
            DELETE FROM member_skill
            WHERE member_id = %s AND profile_skill_id = %s
        """)
        params = (member_id, skill_id)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def get_all_work_ids(cls, member_id):
        query = ("""
            SELECT ARRAY(
                SELECT id FROM member_workhistory WHERE member_id = %s
            )
        """)
        cls.source.execute(query, (member_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return []

    @classmethod
    def create_work_record(cls, params):
        query = ("""
            INSERT INTO member_workhistory (member_id, job_title, employment_type, company_id, company_name, company_location, start_date, end_date)
            VALUES (%(member_id)s, %(job_title)s, %(employment_type)s, %(company_id)s, %(company_name)s, %(company_location)s, %(start_date)s, %(end_date)s)
            RETURNING id;
        """)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def update_work_record(cls, params):
        query = ("""
            UPDATE member_workhistory
            SET job_title = %(job_title)s,
                employment_type=%(employment_type)s,
                company_id=%(company_id)s,
                company_name=%(company_name)s,
                company_location=%(company_location)s,
                start_date=%(start_date)s,
                end_date=%(end_date)s
            WHERE id = %(id)s
        """)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def delete_work_record(cls, id):
        query = ("""
            DELETE FROM member_workhistory WHERE id=%s
        """)
        params = (id,)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def get_all_education_ids(cls, member_id):
        query = ("""
            SELECT ARRAY(
                SELECT id FROM member_education WHERE member_id = %s
            )
        """)
        cls.source.execute(query, (member_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return []

    @classmethod
    def create_education_record(cls, params):
        query = ("""
            INSERT INTO member_education (member_id, school_name, school_location, degree, field_of_study, start_date, end_date, activity_text)
            VALUES (%(member_id)s, %(school_name)s, %(school_location)s, %(degree)s, %(field_of_study)s, %(start_date)s, %(end_date)s, %(activity_text)s)
            RETURNING id;
        """)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def update_education_record(cls, params):
        query = ("""
            UPDATE member_education
            SET school_name= %(school_name)s,
                school_location = %(school_location)s,
                degree = %(degree)s,
                field_of_study = %(field_of_study)s,
                start_date = %(start_date)s,
                end_date = %(end_date)s,
                activity_text = %(activity_text)s
            WHERE id = %(id)s
        """)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def delete_education_record(cls, id):
        query = ("""
            DELETE FROM member_education WHERE id=%s
        """)
        params = (id,)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def get_all_certificate_ids(cls, member_id):
        query = ("""
            SELECT ARRAY (
                SELECT id FROM member_certificate WHERE member_id = %s
            )
        """)
        cls.source.execute(query, (member_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return []

    @classmethod
    def create_certificate_record(cls, params):
        query = ("""
            INSERT INTO member_certificate (member_id, title, description, date_received)
            VALUES (%(member_id)s, %(title)s, %(description)s, %(date_received)s)
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def update_certificate_record(cls, params):
        query = ("""
            UPDATE member_certificate
                SET title =  %(title)s,
                    description = %(description)s,
                    date_received = %(date_received)s
            WHERE id = %(id)s
        """)
        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def delete_certificate_record(cls, id):
        query = ("""
            DELETE FROM member_certificate WHERE id=%s
        """)
        params = (id,)
        cls.source.execute(query, params)
        cls.source.commit()


class MemberSettingDA(object):
    source = source

    @classmethod
    def get_member_setting(cls, member_id):
        get_member_setting_query = ("""
            SELECT
                (
                    SELECT COALESCE(json_agg(rows), '[]'::json) AS location_information
                    FROM (
                        SELECT 
                            member_location.id,
                            member_location.location_type,
                            member_location.description,
                            member_location.location_id,
                            location.country_code_id,
                            location.vendor_formatted_address,
                            country_code.name AS country_name,
                            location.admin_area_1,
                            location.admin_area_2,
                            location.locality,
                            location.sub_locality,
                            location.street_address_1,
                            location.street_address_2,
                            location.postal_code,
                            location.latitude,
                            location.longitude,
                            location.map_vendor,
                            location.map_link,
                            location.place_id
                        FROM member_location
                        LEFT JOIN location ON location.id = member_location.location_id
                        LEFT JOIN country_code ON country_code.id = location.country_code_id
                        WHERE member_id = member_profile.member_id
                    ) AS rows
                ),
                member_profile.online_status,
                member_profile.view_profile,
                member_profile.add_contact,
                member_profile.join_date,
                member_profile.login_location,
                member_profile.unit_of_measure,
                member_profile.timezone_id,
                member_profile.date_format,
                member_profile.time_format,
                member_profile.start_day
            FROM member_profile
                LEFT JOIN member_location ON member_location.member_id = member_profile.member_id
            WHERE member_profile.member_id = %s
            GROUP BY member_profile.member_id
            """)
        get_member_setting_params = (member_id,)
        cls.source.execute(get_member_setting_query, get_member_setting_params)
        if cls.source.has_results():
            for (
                    location_information,
                    online_status,
                    view_profile,
                    add_contact,
                    join_date,
                    login_location,
                    unit_of_measure,
                    timezone_id,
                    date_format,
                    time_format,
                    start_day
            ) in cls.source.cursor:
                member = {
                    "location_information": location_information,
                    "online_status": online_status,
                    "view_profile": view_profile,
                    "add_contact": add_contact,
                    "join_date": join_date,
                    "login_location": login_location,
                    "unit_of_measure": unit_of_measure,
                    "timezone_id": timezone_id,
                    "date_format": date_format,
                    "time_format": time_format,
                    "start_day": start_day
                }

                return member

    @classmethod
    def update_member_setting(cls, member_id, member_profile, member_locations):
        # TODO: - PERFORMANCE CHECK
        # Member_profile
        member_profile_query = ("""
            INSERT INTO member_profile (
                member_id,
                online_status,
                view_profile,
                add_contact,
                join_date,
                login_location,
                unit_of_measure,
                timezone_id,
                date_format,
                time_format,
                start_day )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON conflict(member_id) DO UPDATE
            SET online_status = %s,
                view_profile = %s,
                add_contact = %s,
                join_date = %s,
                login_location = %s,
                unit_of_measure = %s,
                timezone_id = %s,
                date_format = %s,
                time_format = %s,
                start_day = %s
        """)

        member_profile_params = (
            member_id,) + tuple(2 * [member_profile["online_status"], member_profile["view_profile"],
                                    member_profile["add_contact"], member_profile["join_date"], member_profile["login_location"],
                                    member_profile["unit_of_measure"], member_profile["timezone_id"], member_profile["date_format"],
                                    member_profile["time_format"], member_profile["start_day"]])

        cls.source.execute(member_profile_query, member_profile_params)
        cls.source.commit()

        updated = MemberInfoDA.handle_member_locations(
            member_locations, member_id)
        return updated

    @classmethod
    def update_member_payment_setting(cls, member_id, member_locations):
        # Member location
        updated = MemberInfoDA.handle_member_locations(
            member_locations, member_id)
        return updated


    @classmethod
    def update_outgoing_contact(cls, member_id, contact_id):

        try:
            reset_query = ("""
                UPDATE member_contact_2
                SET
                    outgoing_caller = false
                WHERE member_id = %s;
            """)
            cls.source.execute(reset_query, (member_id,))
            cls.source.commit()

            set_query = ("""
                UPDATE member_contact_2
                SET
                    outgoing_caller = true
                WHERE id = %s;
            """)
            logger.debug(f"outgoing_caller_contact_idxx: {contact_id}")

            cls.source.execute(set_query, (contact_id,))
            cls.source.commit()

        except Exception as e:
            logger.debug("iss+++++xx {}".format(e))
            pass



class MemberNotificationsSettingDA(object):
    source = source

    @classmethod
    def update_notifications_setting(cls, member_id, notifications_setting):
        try:
            query = """
                UPDATE member_profile
                SET notification_settings = %s,
                    update_date = CURRENT_TIMESTAMP
                WHERE member_id = %s
            """
            params = (notifications_setting, member_id, )

            cls.source.execute(query, params)
            if cls.source.has_results():
                cls.source.commit()
                return True
            else:
                return False
        except Exception as e:
            logger.debug(e.message)

    @classmethod
    def get_notifications_setting(cls, memberId):
        try:
            query = """
                SELECT
                    member_id,
                    notification_settings
                FROM member_profile
                WHERE member_id = %s
            """
            params = (memberId, )
            cls.source.execute(query, params)
            result = None
            if cls.source.has_results():
                (member_id, notification_settings) = cls.source.cursor.fetchone()
                result = {
                    "member_id": member_id,
                    "data": notification_settings
                }
            return result
        except Exception as e:
            logger.debug(e.message)


class MemberVideoMailDA(object):
    source = source

    @classmethod
    def create_reply_video_mail(cls, message_from, video_storage_id, subject, media_type, replied_id):
        try:
            query = """
                INSERT INTO video_mail (message_from, video_storage_id, subject, type, media_type, replied_id)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING ID
            """
            params = (message_from, video_storage_id, subject,
                      'reply', media_type, replied_id)

            cls.source.execute(query, params)
            id = cls.source.get_last_row_id()
            cls.source.commit()

            return id
        except Exception as e:
            logger.debug(e)

    @classmethod
    def create_group_video_mail(cls, message_from, group_id, video_storage_id, subject, media_type):
        try:
            query = """
                INSERT INTO video_mail (message_from, group_id, video_storage_id, subject, type, media_type)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING ID
            """
            params = (message_from, group_id, video_storage_id,
                      subject, "group", media_type)

            cls.source.execute(query, params)
            id = cls.source.get_last_row_id()
            cls.source.commit()

            return id

        except Exception as e:
            logger.debug(e)

    @classmethod
    def create_contact_video_mail(cls, message_from, video_storage_id, subject, media_type):
        try:
            query = """
                INSERT INTO video_mail (message_from, video_storage_id, subject, type, media_type)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING ID
            """
            params = (message_from, video_storage_id,
                      subject, 'contact', media_type)

            cls.source.execute(query, params)
            id = cls.source.get_last_row_id()
            cls.source.commit()

            return id
            query = """
                    INSERT INTO video_mail_xref (member_id, video_mail_id)
                    VALUES (%s, %s)
                """

            params = (receiver, id)

            if type == 'contact' or type == 'reply':
                cls.source.execute(query, params)
                cls.source.commit()

            else:
                group_leader_query = """SELECT
                    group_leader_id
                    FROM member_group
                    WHERE id = %s
                """
                group_param = (receiver,)

                cls.source.execute(group_leader_query, group_param)

                if cls.source.has_results():
                    (group_leader_id,) = cls.source.cursor.fetchone()

                group_member_query = """
                    INSERT INTO video_mail_xref (member_id, video_mail_id)
                    SELECT member_group_membership.member_id, %s as video_mail_id
                    FROM member_group_membership
                    WHERE member_group_membership.group_id = %s AND member_group_membership.member_id <> %s
                """
                params = (id, receiver, message_from)

                cls.source.execute(group_member_query, params)
                cls.source.commit()

                params = (group_leader_id, id)

                if group_leader_id is not message_from:
                    cls.source.execute(query, params)
                    cls.source.commit()

            return id
        except Exception as e:
            logger.debug(e)

    @classmethod
    def create_contact_video_mail_xref(cls, message_to, video_mail_id):
        try:
            query = """
                    INSERT INTO video_mail_xref (member_id, video_mail_id)
                    VALUES (%s, %s)
                """

            params = (message_to, video_mail_id)

            cls.source.execute(query, params)
            cls.source.commit()
        except Exception as e:
            logger.debug(e)

    @classmethod
    def create_group_video_mail_xref(cls, message_from, group_id, video_mail_id):
        try:

            group_member_query = """
                INSERT INTO video_mail_xref (member_id, video_mail_id)
                SELECT member_group_membership.member_id, %s as video_mail_id
                FROM member_group_membership
                WHERE member_group_membership.group_id = %s AND member_group_membership.member_id <> %s
            """
            params = (video_mail_id, group_id, message_from)

            cls.source.execute(group_member_query, params)
            cls.source.commit()
        except Exception as e:
            logger.debug(e)

    @classmethod
    def get_video_mails(cls, member_id, search_key='', page_number=None, page_size=None):
        query = """
            SELECT
                vm.id,
                vm.subject,
                vm.type,
                vm.media_type,
                vmx.status,
                vm.create_date,
                vm.group_id,
                member_group.group_name,
                sender.id as member_id,
                sender.email,
                sender.first_name,
                sender.last_name,
                file_storage_engine.storage_engine_id as video_url,
                COALESCE(json_agg(DISTINCT t1.*) FILTER (WHERE t1.member_id IS NOT NULL), '[]') AS read_members
            FROM video_mail_xref as vmx
            LEFT JOIN video_mail as vm ON vm.id = vmx.video_mail_id
            LEFT JOIN member as sender ON sender.id = vm.message_from
            LEFT OUTER JOIN (
                SELECT
                    reader.id as member_id,
                    reader.email as email,
                    reader.first_name as first_name,
                    reader.last_name as last_name,
                    vmx_read.video_mail_id
                FROM video_mail_xref as vmx_read
                LEFT JOIN member as reader ON vmx_read.member_id = reader.id
                WHERE vmx_read.status <> 'unread' AND vmx_read.member_id <> %s
            ) as t1 ON t1.video_mail_id = vm.id
            LEFT OUTER JOIN member_group ON member_group.id = vm.group_id
            LEFT OUTER JOIN file_storage_engine ON vm.video_storage_id = file_storage_engine.id
            WHERE (
                sender.email like %s OR
                sender.first_name LIKE %s OR
                sender.last_name LIKE %s OR
                vm.subject LIKE %s )
                AND vmx.member_id = %s
                AND vmx.status <> 'deleted'
            GROUP BY
                vm.id,
                vm.subject,
                vm.type,
                vm.media_type,
                vmx.status,
                vm.create_date,
                vm.group_id,
                member_group.group_name,
                sender.id,
                sender.email,
                sender.first_name,
                sender.last_name,
                file_storage_engine.storage_engine_id
            ORDER BY vm.create_date desc
            """

        like_search_key = """%{}%""".format(search_key)
        params = (member_id, like_search_key, like_search_key,
                  like_search_key, like_search_key, member_id)

        if page_size and page_number:
            query += """LIMIT %s OFFSET %s"""
            params = (member_id, like_search_key, like_search_key, like_search_key, like_search_key, member_id, page_size,
                      (page_number - 1) * page_size)

        mails = []
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                id,
                subject,
                type,
                media_type,
                status,
                create_date,
                group_id,
                group_name,
                member_id,
                email,
                first_name,
                last_name,
                video_url,
                read_members
            ) in cls.source.cursor:
                mail = {
                    "id": id,
                    "subject": subject,
                    "type": type,
                    "media_type": media_type,
                    "status": status,
                    "create_date": create_date,
                    "group_id": group_id,
                    "group_name": group_name,
                    "member_id": member_id,
                    "email": email,
                    "first_name": first_name,
                    "last_name": last_name,
                    "video_url": amerize_url(video_url),
                    "read_members": read_members
                }

                mails.append(mail)
        return mails

    @classmethod
    def read_video_mail(cls, member_id, mail_id):
        try:
            query = """
                UPDATE video_mail_xref
                SET status = 'read'
                WHERE
                    video_mail_xref.member_id= %s
                    AND video_mail_xref.video_mail_id = %s
                    AND video_mail_xref.status = 'unread'
            """

            params = (member_id, mail_id)

            cls.source.execute(query, params)
            cls.source.commit()

            return
        except Exception as e:
            logger.debug(e.message)

    @classmethod
    def delete_video_mail(cls, member_id, mail_id):
        try:
            query = """
                UPDATE video_mail_xref
                SET status = 'deleted'
                WHERE
                    video_mail_xref.member_id= %s
                    AND video_mail_xref.video_mail_id = %s
            """

            params = (member_id, mail_id)

            cls.source.execute(query, params)
            cls.source.commit()

            return
        except Exception as e:
            logger.debug(e.message)

    @classmethod
    def get_all_media_mails(cls, member_id, is_history=False, mail_type=None):
        mails = list()

        try:
            unread = ""
            mail_type = ""

            if not is_history:
                unread = " AND xref.status = 'unread'"

            if mail_type:
                mail_type = f" AND head.type = {mail_type}"

            query_mails = f"""
                SELECT
                    head.id,
                    head.subject,
                    head.type,
                    head.media_type,
                    xref.id as xref_id,
                    xref.status,
                    xref.create_date,
                    mail_storage.storage_engine_id as mail_url,
                    member.email as email,
                    member.first_name as first_name,
                    member.last_name as last_name,
                    file_storage_engine.storage_engine_id as s3_avatar_url,
                    member_group.id as group_id,
                    member_group.group_name
                FROM video_mail as head
                INNER JOIN  file_storage_engine mail_storage on mail_storage.id = head.video_storage_id
                INNER JOIN video_mail_xref xref on head.id = xref.video_mail_id
                INNER JOIN member member on member.id = head.message_from
                LEFT OUTER JOIN member_profile profile on member.id = profile.member_id
                LEFT OUTER JOIN file_storage_engine on file_storage_engine.id = profile.profile_picture_storage_id
                LEFT OUTER JOIN member_group on member_group.id = head.group_id
                WHERE
                    xref.member_id = %s
                    {unread}
                    {mail_type}
                ORDER BY xref.create_date DESC
                LIMIT 25
            """

            param_mails = (member_id,)

            cls.source.execute(query_mails, param_mails)
            if cls.source.has_results():
                for (
                        id,
                        subject,
                        type,
                        media_type,
                        xref_id,
                        status,
                        create_date,
                        mail_url,
                        email,
                        first_name,
                        last_name,
                        s3_avatar_url,
                        group_id,
                        group_name
                ) in cls.source.cursor:
                    mail = {
                        "id": id,
                        "subject": subject,
                        "mail_type": type,
                        "media_type": media_type,
                        "xref_id": xref_id,
                        "status": status,
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "amera_avatar_url": amerize_url(s3_avatar_url),
                        "mail_url": amerize_url(mail_url),
                        "group_id": group_id,
                        "group_name": group_name,
                        "create_date": create_date,
                        "invitation_type": "media_mail"
                    }
                    mails.append(mail)

            return mails
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
