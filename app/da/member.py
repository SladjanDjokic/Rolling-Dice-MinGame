import logging
import datetime

from app.util.db import source
from app.util.config import settings

from app.exceptions.data import DuplicateKeyError, DataMissingError, RelationshipReferenceError
from app.exceptions.member import ForgotDuplicateDataError

logger = logging.getLogger(__name__)


class MemberDA(object):
    source = source

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
                job_title.name as job_title
            FROM member
            LEFT OUTER JOIN job_title ON job_title.id = member.job_title_id
            WHERE ( email LIKE %s OR username LIKE %s OR first_name LIKE %s OR last_name LIKE %s ) AND id <> %s
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
                    job_title
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
                    "job_title": job_title
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
    def register(cls, avatar_storage_id, email, username, password, first_name, middle_name,
                 last_name, company_name, job_title_id, date_of_birth, phone_number,
                 country, city, street, postal, state, province, cell_confrimation_ts, email_confrimation_ts, commit=True):

        # TODO: CHANGE THIS LATER TO ENCRYPT IN APP
        query_member = ("""
        INSERT INTO member
        (email, username, password, first_name, middle_name, last_name, date_of_birth, company_name, job_title_id, avatar_storage_id)
        VALUES (%s, %s, crypt(%s, gen_salt('bf')), %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """)
        query_member_contact = ("""
        INSERT INTO member_contact
        (member_id, phone_number, email)
        VALUES (%s, %s, %s)
        RETURNING id
        """)
        query_member_contact_2 = ("""
        INSERT INTO member_contact_2
        (member_id, description, device, device_type, device_country, device_confirm_date, method_type, display_order, primary_contact)
        VALUES (%s, %s, %s, %s, (SELECT id FROM country_code WHERE alpha2 = %s), TIMESTAMP %s, %s, %s, %s)
        RETURNING id
        """)
        query_member_location = ("""
        INSERT INTO member_location
        (member_id, street, address_1, city, state, province, postal, country, location_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'home')
        RETURNING id
        """)

        # AES_ENCRYPT(%s, UNHEX(SHA2(%s)))
        # settings.get('MEMBER_KEY')
        # store member personal info
        params_member = (email, username, password, first_name,
                         middle_name, last_name, date_of_birth, company_name, job_title_id, avatar_storage_id)
        cls.source.execute(query_member, params_member)
        id = cls.source.get_last_row_id()

        if email: 
            # Member_contact_2
            # FIXME: cell_confrimation_ts is passed temporary
            params_email_member_contact_2 = (id, "Office email", email, "email", country, email_confrimation_ts, "html", 2, False)
            cls.source.execute(query_member_contact_2, params_email_member_contact_2)
        
        if phone_number:
            # store member contact info
            params_member_contact = (id, phone_number, email)
            cls.source.execute(query_member_contact, params_member_contact)
            # Member_contact_2
            params_cell_member_contact_2 = (id, "Cell phone", phone_number, "cell", country, cell_confrimation_ts, "voice", 1, True)
            cls.source.execute(query_member_contact_2, params_cell_member_contact_2)
        if street:
            # store member location info
            params_member_location = (
                id, street, street, city, state, province, postal, country)
            cls.source.execute(query_member_location, params_member_location)

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
                member_contact.phone_number as cell_phone
            FROM member
            LEFT JOIN member_contact ON member.id = member_contact.member_id
            LEFT JOIN member_location ON member.id = member_location.member_id
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
            ) in cls.source.cursor:
                member = {
                    "email": email,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "country": country,
                    "cell_phone": cell_phone,
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
            password = crypt(%s, gen_salt('bf'))
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
    def get_job_list(cls,):
        query = """
        SELECT 
            id as job_title_id,
            name as job_title
        FROM job_title
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


class MemberContactDA(object):
    source = source

    @classmethod
    def get_member_contacts(cls, member_id):
        contacts = list()
        get_contacts_query = ("""
            SELECT contact.id as id,
                contact.contact_member_id as contact_member_id,
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
                json_agg(DISTINCT member_location.*) AS location_information,
                json_agg(DISTINCT member_contact_2.*) AS contact_information,
                json_agg(DISTINCT country_code.*) AS country_code
            FROM contact
                LEFT JOIN member ON member.id = contact.contact_member_id
                LEFT OUTER JOIN member_location ON member_location.member_id = contact.contact_member_id
                LEFT OUTER JOIN member_contact ON member_contact.member_id = contact.contact_member_id
                LEFT OUTER JOIN member_contact_2 ON member_contact_2.member_id = contact.contact_member_id
                LEFT OUTER JOIN country_code ON member_contact_2.device_country = country_code.id
                LEFT OUTER JOIN job_title ON member.job_title_id = job_title.id
            WHERE contact.member_id = %s
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
                contact.update_date
            ORDER BY contact.first_name ASC
            """)
        get_contacts_params = (member_id,)
        cls.source.execute(get_contacts_query, get_contacts_params)
        if cls.source.has_results():
            for (
                    id,
                    contact_member_id,
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
                    country_code
            ) in cls.source.cursor:
                contact = {
                    "id": id,
                    "contact_member_id": contact_member_id,
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
                    "country_code": country_code
                    # "city": city,
                    # "state": state,
                    # "province": province,
                    # "country": country
                }
                contacts.append(contact)
        return contacts

    @classmethod
    def get_members(cls, member_id):
        members = list()
        get_members_query = ("""
                SELECT 
                    member.id as id,
                    member.first_name as first_name,
                    member.middle_name as middle_name,
                    member.last_name as last_name,
                    member.email as email,
                    member.company_name as company,
                    job_title.name as title,
                    contact.contact_member_id as contact_member_id
                FROM member
                LEFT JOIN contact ON (member.id = contact.contact_member_id AND contact.member_id = %s)
                LEFT OUTER JOIN job_title ON member.job_title_id = job_title.id
                WHERE member.id <> %s
                ORDER BY member.first_name ASC
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
                    contact_member_id
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
                        "contact_member_id": contact_member_id
                    }
                    members.append(member)
        return members

    @classmethod
    def get_member_contact(cls, contact_id):
        contact = cls.__get_member_contact('contact.id', contact_id)
        return contact

    @classmethod
    def get_member_contact_by_email(cls, email):
        return cls.__get_member_contact('contact.email', email)

    @classmethod
    def __get_member_contact(cls, key, value):
        get_contact_query = ("""
            SELECT contact.id as id,
                contact.contact_member_id as contact_member_id,
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
                json_agg(DISTINCT member_location.*) AS location_information,
                json_agg(DISTINCT member_contact_2.*) AS contact_information,
                json_agg(DISTINCT country_code.*) AS country_code
            FROM contact
                LEFT JOIN member ON member.id = contact.contact_member_id
                LEFT OUTER JOIN member_location ON member_location.member_id = contact.contact_member_id
                LEFT OUTER JOIN member_contact ON member_contact.member_id = contact.contact_member_id
                LEFT OUTER JOIN member_contact_2 ON member_contact_2.member_id = contact.contact_member_id
                LEFT OUTER JOIN country_code ON member_contact_2.device_country = country_code.id
                LEFT OUTER JOIN job_title ON job_title.id = member.job_title_id
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
                contact.update_date
            """.format(key))

        get_contact_params = (value,)
        cls.source.execute(get_contact_query, get_contact_params)
        if cls.source.has_results():
            for (
                    id,
                    contact_member_id,
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
                    country_code
            ) in cls.source.cursor:
                contact = {
                    "id": id,
                    "contact_member_id": contact_member_id,
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
                    "country_code": country_code
                }

                return contact

        return None

    @classmethod
    def create_member_contact(cls, member_id, contact_member_id, first_name,
                              last_name, country, cell_phone, office_phone,
                              home_phone, email, personal_email, company_name,
                              company_phone, company_web_site, company_email,
                              company_bio, contact_role, commit=True):
        create_member_contact_query = ("""
                    INSERT INTO contact
                        (member_id, contact_member_id, first_name, last_name,
                        country, cell_phone, office_phone, home_phone,
                        email, personal_email, company_name, company_phone,
                        company_web_site, company_email, company_bio,
                        contact_role)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s)
                    RETURNING id
                    """)

        create_member_contact_params = (
            member_id, contact_member_id, first_name, last_name, country, cell_phone, office_phone,
            home_phone, email, personal_email, company_name, company_phone,
            company_web_site, company_email, company_bio, contact_role
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
                job_title.name as title,
                member.create_date as create_date,
                member.update_date as update_date,
                json_agg(DISTINCT member_location.*) AS location_information,
                json_agg(DISTINCT member_contact_2.*) AS contact_information,
                json_agg(DISTINCT country_code.*) AS country_code
            FROM member
                LEFT OUTER JOIN member_location ON member_location.member_id = member.id
                LEFT OUTER JOIN member_contact ON member_contact.member_id = member.id
                LEFT OUTER JOIN member_contact_2 ON member_contact_2.member_id = member.id
                LEFT OUTER JOIN country_code ON member_contact_2.device_country = country_code.id
                LEFT OUTER JOIN job_title ON member.job_title_id = job_title.name
            WHERE member.id = %s
            GROUP BY 
                member.id,
                member.first_name,
                member.middle_name,
                member.last_name,
                member.email,
                member.company_name,
                job_title.name,
                member.create_date,
                member.update_date
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
                    title,
                    create_date,
                    update_date,
                    location_information,
                    contact_information,
                    country_code
            ) in cls.source.cursor:
                member = {
                    "member_id": member_id,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "email": email,
                    "company": company,
                    "title": title,
                    "create_date": create_date,
                    "update_date": update_date,
                    "location_information": location_information,
                    "contact_information": contact_information,
                    "country_code": country_code
                }

                return member
