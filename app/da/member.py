from app.util.security import SECURITY_EXCHANGE_OPTIONS
import logging
import datetime
from urllib import parse

from app.util.db import source
from app.util.config import settings
from app.util.filestorage import amerize_url

from app.exceptions.data import DuplicateKeyError, DataMissingError, RelationshipReferenceError
from app.exceptions.member import ForgotDuplicateDataError


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
    def get_members(cls, member_id, search_key, page_size=None, page_number=None):

        query = """
            SELECT
                member.id as member_id,
                member.email as email,
                member.create_date as create_date,
                member.update_date as update_date,
                member.username as username,
                member.status as status,
                member.first_name as first_name,
                member.middle_name as middle_name,
                member.last_name as last_name,
                member.company_name as company_name,
                job_title.name as title
            FROM member
            LEFT OUTER JOIN job_title ON job_title.id = member.job_title_id
            WHERE ( email LIKE %s OR username LIKE %s OR first_name LIKE %s OR last_name LIKE %s ) AND member.id <> %s
            """

        like_search_key = """%{}%""".format(search_key)
        params = (like_search_key, like_search_key,
                  like_search_key, like_search_key, member_id)

        if page_size and page_number:
            query += """LIMIT %s OFFSET %s"""
            params = (like_search_key, like_search_key, like_search_key, like_search_key, member_id, page_size,
                      (page_number - 1) * page_size)

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
                    middle_name,
                    last_name,
                    company_name,
                    title
            ) in cls.source.cursor:
                member = {
                    "member_id": member_id,
                    "email": email,
                    "create_date": datetime.datetime.strftime(create_date, "%Y-%m-%d %H:%M:%S"),
                    "update_date": datetime.datetime.strftime(update_date, "%Y-%m-%d %H:%M:%S"),
                    "username": username,
                    "status": status,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "member_name": f'{first_name}{middle_name}{last_name}',
                    "title": title
                }

                members.append(member)

        return members

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
                    "create_date": datetime.datetime.strftime(create_date, "%Y-%m-%d %H:%M:%S"),
                    "update_date": datetime.datetime.strftime(update_date, "%Y-%m-%d %H:%M:%S"),
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
        query_member_location = ("""
        INSERT INTO member_location
        (member_id, city, state, province, postal,
         country, country_code_id, location_type)
        VALUES (%s, %s, %s, %s, %s, (SELECT name FROM country_code WHERE id = %s), %s, 'home')
        """)

        query_member_profile = ("""
        INSERT INTO member_profile (member_id, profile_picture_storage_id)
        VALUES (%s, %s)
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
        if postal:
            # store member location info
            city = None if city == 'null' else city
            state = None if state == 'null' else state
            province = None if province == 'null' else province
            params_member_location = (
                id, city, state, province, postal, country, country)
            # FIXME: We need to store only the country_id and pull everything else from the country_code table
            cls.source.execute(query_member_location, params_member_location)

        # When registering a new member, the uploaded photo is set as both profile and security picture. Profile picture can be changed later on.
        params_member_profile = (id, avatar_storage_id)
        cls.source.execute(query_member_profile, params_member_profile)

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
                member_location.country as country,
                member_contact.phone_number as cell_phone,
                contact.company_name as company_name,
                contact.role_id as role_id
            FROM member
            LEFT JOIN member_contact ON member.id = member_contact.member_id
            LEFT JOIN member_location ON member.id = member_location.member_id
            LEFT JOIN contact ON member.id = contact.member_id
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
            'country_code_id': 'member_location.country_code_id',
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
            sort_columns_string = cls.formatSortingParams(
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
                LEFT OUTER JOIN role ON contact.role_id = role.id
                LEFT OUTER JOIN member_location ON member_location.member_id = contact.contact_member_id
                -- LEFT OUTER JOIN member_contact ON member_contact.member_id = contact.contact_member_id
                LEFT OUTER JOIN member_contact_2 ON member_contact_2.member_id = contact.contact_member_id
                LEFT OUTER JOIN country_code ON member_contact_2.device_country = country_code.id
                LEFT OUTER JOIN job_title ON member.job_title_id = job_title.id
                LEFT OUTER JOIN member_profile ON contact.contact_member_id = member_profile.member_id
                LEFT OUTER JOIN member_achievement ON member_achievement.member_id = member.id
                LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                LEFT OUTER JOIN member_session ON
                    contact.contact_member_id = member_session.member_id AND
                    member_session.status IN ('online', 'disconnected') AND
                    member_session.expiration_date >= current_timestamp
                LEFT OUTER JOIN company_role_xref ON company_role_xref.member_id = member.id
                LEFT OUTER JOIN company ON company_role_xref.company_id = company.id
            WHERE
                contact.member_id = %s {filter_conditions_query}
                {get_contacts_search_query if search_key != "" else ''}
            GROUP BY
                contact.id,
                contact.contact_member_id,
                member.first_name,
                member.middle_name,
                member.last_name,
                member_profile.biography,
                -- contact.cell_phone,
                -- contact.office_phone,
                -- contact.home_phone,
                -- contact.email,
                -- contact.personal_email,
                member.company_name,
                job_title.name,
                -- contact.company_name,
                -- contact.company_phone,
                -- contact.company_web_site,
                -- contact.company_email,
                -- contact.company_bio,
                role.name,
                role.id,
                contact.create_date,
                contact.update_date,
                file_storage_engine.storage_engine_id,
                contact.status,
                member_session.status,
                company.id,
                company.name
            """)

        if search_key != '':
            like_search_key = """%{}%""".format(search_key.lower())
            get_contacts_params = get_contacts_params + \
                tuple(11 * [like_search_key])

        get_contacts_query = (f"""
            SELECT 
                contact.id as id,
                contact.contact_member_id as contact_member_id,
                member.first_name as first_name,
                member.middle_name as middle_name,
                member.last_name as last_name,
                member_profile.biography as biography,
                -- contact.cell_phone as cell_phone,
                -- contact.office_phone as office_phone,
                -- contact.home_phone as home_phone,
                -- contact.email as email,
                -- contact.personal_email as personal_email,
                member.company_name as company,
                job_title.name as title,
                -- contact.company_name as company_name,
                -- contact.company_phone as company_phone,
                -- contact.company_web_site as company_web_site,
                -- contact.company_email as company_email,
                -- contact.company_bio as company_bio,
                role.name as role,
                role.id as role_id,
                contact.create_date as create_date,
                contact.update_date as update_date,
                COALESCE(json_agg(DISTINCT member_location.*) FILTER (WHERE member_location.id IS NOT NULL), '[]') AS location_information,
                COALESCE(json_agg(DISTINCT member_contact_2.*) FILTER (WHERE member_contact_2.id IS NOT NULL), '[]') AS contact_information,
                COALESCE(json_agg(DISTINCT country_code.*) FILTER (WHERE country_code.id IS NOT NULL), '[]') AS country_code,
                COALESCE(json_agg(DISTINCT member_achievement.*) FILTER (WHERE member_achievement.id IS NOT NULL), '[]') AS achievement_information,
                file_storage_engine.storage_engine_id as s3_avatar_url,
                contact.security_exchange_option,
                contact.status,
                CASE
                    WHEN member_session.status IS NOT NULL
                    THEN member_session.status
                    ELSE 'inactive'
                END as online_status,
                company.id as company_id,
                company.name as member_company_name
                {get_contacts_base_query}
            ORDER BY {sort_columns_string}
        """)

        get_contacts_count_query = (f"""
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
                        first_name,
                        middle_name,
                        last_name,
                        biography,
                        # cell_phone,
                        # office_phone,
                        # home_phone,
                        # email,
                        # personal_email,
                        company,
                        title,
                        # company_name,
                        # company_phone,
                        # company_web_site,
                        # company_email,
                        # company_bio,
                        role,
                        role_id,
                        create_date,
                        update_date,
                        location_information,
                        contact_information,
                        country_code,
                        achievement_information,
                        s3_avatar_url,
                        security_exchange_option,
                        status,
                        online_status,
                        company_id,
                        member_company_name
                ) in cls.source.cursor:
                    contact = {
                        "id": id,
                        "contact_member_id": contact_member_id,
                        "first_name": first_name,
                        "middle_name": middle_name,
                        "last_name": last_name,
                        "member_name": f'{first_name} {last_name}',
                        "biography": biography,
                        # "cell_phone": cell_phone,
                        # "office_phone": office_phone,
                        # "home_phone": home_phone,
                        # "email": email,
                        # "personal_email": personal_email,
                        "company": company,
                        "title": title,
                        # "company_name": company_name,
                        # "company_phone": company_phone,
                        # "company_web_site": company_web_site,
                        # "company_email": company_email,
                        # "company_bio": company_bio,
                        "role": role,
                        "role_id": role_id,
                        "create_date": create_date,
                        "update_date": update_date,
                        "location_information": location_information,
                        "contact_information": contact_information,
                        "country_code": country_code,
                        "achievement_information": achievement_information,
                        "amera_avatar_url": amerize_url(s3_avatar_url),
                        "security_exchange_option":
                            SECURITY_EXCHANGE_OPTIONS.get(
                                security_exchange_option, 0),
                        "status": status,
                        "online_status": online_status,
                        "company_id": company_id,
                        "member_company_name": member_company_name

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
                INNER JOIN country_code ON (member_location.country_code_id = country_code.id)
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
    def get_members(cls, member_id, sort_params):
        sort_columns_string = 'first_name ASC'
        if sort_params:
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
            sort_columns_string = cls.formatSortingParams(
                sort_params, member_dict) or sort_columns_string
        logger.debug('sorting params for members {} and sort_by_columns {}'.format(
            sort_params, sort_columns_string))
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
                    file_storage_engine.storage_engine_id as s3_avatar_url
                FROM member
                LEFT JOIN contact ON (member.id = contact.contact_member_id AND contact.member_id = %s)
                LEFT OUTER JOIN job_title ON member.job_title_id = job_title.id
                LEFT OUTER JOIN member_profile ON member.id = member_profile.member_id
                LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                WHERE member.id <> %s
                ORDER BY {sort_columns_string}
                """)
        get_members_params = (member_id, member_id,)
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
                    s3_avatar_url
            ) in cls.source.cursor:
                if not contact_member_id:
                    member = {
                        "id": id,
                        "first_name": first_name,
                        "middle_name": middle_name,
                        "last_name": last_name,
                        "email": email,
                        "company": company,
                        "title": title,
                        "contact_member_id": contact_member_id,
                        "amera_avatar_url": amerize_url(s3_avatar_url)
                    }
                    members.append(member)
        return members

    @classmethod
    def formatSortingParams(cls, sort_by, entity_dict):
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
    def create_member_contact(cls, member_id, contact_member_id, status, first_name,
                              last_name, country, cell_phone, office_phone,
                              home_phone, email, personal_email, company_name,
                              company_phone, company_web_site, company_email,
                              company_bio, contact_role, role_id, commit=True):
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
                member.job_title_id as job_title_id,
                job_title.name as job_title,
                member.department_id as department_id,
                member.create_date as create_date,
                member.update_date as update_date,
                COALESCE(json_agg(DISTINCT member_location.*) FILTER (WHERE member_location.id IS NOT NULL), '[]') AS location_information,
                COALESCE(json_agg(DISTINCT member_contact_2.*) FILTER (WHERE member_contact_2.id IS NOT NULL), '[]') AS contact_information,
                COALESCE(json_agg(DISTINCT country_code.*) FILTER (WHERE country_code.id IS NOT NULL), '[]') AS country_code,
                COALESCE(json_agg(DISTINCT member_achievement.*) FILTER (WHERE member_achievement.id IS NOT NULL), '[]') AS achievement_information,
                file_storage_engine.storage_engine_id as s3_avatar_url,
                member_profile.biography as biography
            FROM member
                LEFT OUTER JOIN job_title ON member.job_title_id = job_title.id
                LEFT OUTER JOIN member_location ON member_location.member_id = member.id
                LEFT OUTER JOIN member_contact ON member_contact.member_id = member.id
                LEFT OUTER JOIN member_contact_2 ON member_contact_2.member_id = member.id
                LEFT OUTER JOIN country_code ON member_contact_2.device_country = country_code.id
                LEFT OUTER JOIN member_achievement ON member_achievement.member_id = member.id
                LEFT OUTER JOIN member_profile ON member.id = member_profile.member_id
                LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
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
                member.department_id,
                member.create_date,
                member.update_date,
                file_storage_engine.storage_engine_id,
                member_profile.biography
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
                    job_title_id,
                    job_title,
                    department_id,
                    create_date,
                    update_date,
                    location_information,
                    contact_information,
                    country_code,
                    achievement_information,
                    s3_avatar_url,
                    biography
            ) in cls.source.cursor:
                member = {
                    "member_id": member_id,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "email": email,
                    "company_name": company,
                    "job_title_id": job_title_id,
                    "job_title": job_title,
                    "department_id": department_id,
                    "create_date": create_date,
                    "update_date": update_date,
                    "location_information": location_information,
                    "contact_information": contact_information,
                    "country_code": country_code,
                    "achievement_information": achievement_information,
                    "amera_avatar_url": amerize_url(s3_avatar_url),
                    "biography": biography
                }

                return member

    @classmethod
    def update_member_info(cls, member_id, member, member_profile, member_achievement, member_contact_2, member_location):

        try:
            # TODO: - PERFORMANCE CHECK
            # Into member - first_name, middle_name, last_name, company_name, job_title_id, department_id,
            # Into member_profile - biography,
            # Into member_achievement - entity, description, display_order
            # Into member_contact_2 -  description, device, device_type, device_country, device_confirm_date, method_type, display_order, primary_contact
            # Into member_location - address_1, address_2, city, state, province, postal, country, country_code_id, location_type

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
            member_location_update_query = ("""
                UPDATE member_location
                SET
                    address_1 = %s,
                    street = %s,
                    address_2 = %s,
                    city = %s,
                    state = %s,
                    province = %s,
                    postal = %s,
                    country = %s,
                    country_code_id = %s,
                    location_type = %s,
                    update_date = CURRENT_TIMESTAMP
                WHERE id=%s AND member_id = %s;
            """)
            member_location_insert_query = ("""
                INSERT INTO member_location (address_1, street, address_2, city, state, province, postal, country, country_code_id, location_type, member_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """)
            member_location_delete_query = ("""
                DELETE FROM member_location
                WHERE member_id = %s AND NOT id = ANY(%s);
            """)

            if member_location:
                location_ids_to_stay = list()
                for location in member_location:
                    if location:
                        id_, street, address_1, address_2, city, state, province, postal, country, country_code_id, location_type = [
                            location[k] for k in ('id', 'street', 'address_1', 'address_2', 'city', 'state', 'province', 'postal', 'country', 'country_code_id', 'location_type')]

                    if type(id_) == int:
                        cls.source.execute(
                            member_location_update_query, (address_1, street, address_2, city, state, province, postal, country, country_code_id, location_type, id_, member_id))
                        location_ids_to_stay.append(id_)
                    else:
                        cls.source.execute(
                            member_location_insert_query, (address_1, street, address_2, city, state, province, postal, country, country_code_id, location_type, member_id))
                        location_ids_to_stay.append(
                            cls.source.get_last_row_id())
                    cls.source.commit()
                # Track what was deleted in the UI and kill it in db as well
                cls.source.execute(member_location_delete_query,
                                   (member_id, location_ids_to_stay))
                cls.source.commit()
            return True
        except:
            pass

class MemberSettingDA(object):
    source = source

    def get_member_setting(cls, member_id):
        get_member_setting_query = ("""
            SELECT
                COALESCE(json_agg(DISTINCT member_location.*) FILTER (WHERE member_location.id IS NOT NULL), '[]') AS location_information,
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
                LEFT OUTER JOIN member_location ON member_location.member_id = member_profile.member_id
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
    def update_member_setting(cls, member_id, member_profile, member_location):

        try:
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

            # Member location
            member_location_update_query = ("""
                UPDATE member_location
                SET
                    description = %s,
                    address_1 = %s,
                    street = %s,
                    address_2 = %s,
                    city = %s,
                    state = %s,
                    province = %s,
                    postal = %s,
                    country = %s,
                    country_code_id = %s,
                    location_type = %s
                WHERE id=%s AND member_id = %s;
            """)
            member_location_insert_query = ("""
                INSERT INTO member_location (description, address_1, street, address_2, city, state, province, postal, country, country_code_id, location_type, member_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
            """)
            member_location_delete_query = ("""
                DELETE FROM member_location
                WHERE member_id = %s AND NOT id = ANY(%s) AND location_type IN ('other', 'billing');
            """)

            if member_location:
                location_ids_to_stay = list()
                for location in member_location:
                    if location:
                        id_, description, street, address_1, address_2, city, state, province, postal, country, country_code_id, location_type = [
                            location[k] for k in ('id', 'description', 'street', 'address_1', 'address_2', 'city', 'state', 'province', 'postal', 'country', 'country_code_id', 'location_type')]

                    if type(id_) == int:
                        cls.source.execute(
                            member_location_update_query, (description, address_1, street, address_2, city, state, province, postal, country, country_code_id, location_type, id_, member_id))
                        location_ids_to_stay.append(id_)
                    else:
                        cls.source.execute(
                            member_location_insert_query, (description, address_1, street, address_2, city, state, province, postal, country, country_code_id, location_type, member_id))
                        location_ids_to_stay.append(
                            cls.source.get_last_row_id())
                    cls.source.commit()
                # Track what was deleted in the UI and kill it in db as well
                cls.source.execute(member_location_delete_query,
                                   (member_id, location_ids_to_stay))
                cls.source.commit()
            return True
        except Exception as e:
            logger.debug("iss+++++ {}".format(e))
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
