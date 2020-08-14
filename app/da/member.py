import logging
import datetime

from app.util.db import source
from app.util.config import settings

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
    def get_members(cls, member_id, search_key, page_size=None, page_number=None):

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
            WHERE ( email LIKE %s OR username LIKE %s OR first_name LIKE %s OR last_name LIKE %s ) AND id <> %s
            """

        like_search_key = """%{}%""".format(search_key)
        params = (like_search_key, like_search_key, like_search_key, like_search_key, member_id)

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
                    "member_name": f'{first_name} {last_name}'
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
    def register(cls, email, username, password, first_name,
                 last_name, date_of_birth, phone_number,
                 country, city, street, postal, state, province,
                 commit=True):

        # TODO: CHANGE THIS LATER TO ENCRYPT IN APP
        query_member = ("""
        INSERT INTO member
        (email, username, password, first_name, last_name, date_of_birth)
        VALUES (%s, %s, crypt(%s, gen_salt('bf')), %s, %s, %s)
        RETURNING id
        """)

        query_member_contact = ("""
        INSERT INTO member_contact
        (member_id, phone_number, email)
        VALUES (%s, %s, %s)
        RETURNING id
        """)

        query_member_location = ("""
        INSERT INTO member_location
        (member_id, street, city, state, province, postal, country)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """)

        # AES_ENCRYPT(%s, UNHEX(SHA2(%s)))
        # settings.get('MEMBER_KEY')
        # store member personal info
        params_member = (email, username, password, first_name, last_name, date_of_birth)
        cls.source.execute(query_member, params_member)
        id = cls.source.get_last_row_id()

        # store member contact info
        params_member_contact = (id, phone_number, email)
        cls.source.execute(query_member_contact, params_member_contact)

        # store member location info
        params_member_location = (id, street, city, state, province, postal, country)
        cls.source.execute(query_member_location, params_member_location)
        # params_member_contact_info = (id, phone_number, email)
        # cls.source.execute(query_member_contact, params_member_contact_info)

        # store member location info
        # params_member_location = (id, street, city, state, province, postal, country)
        # cls.source.execute(query_member_location, params_member_location)

        if commit:
            cls.source.commit()

        return id

    @classmethod
    def get_contact_member(cls, member_id):
        query = ("""
            SELECT
                member.email as email,
                member.first_name as first_name,
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
                    last_name,
                    country,
                    cell_phone,
            ) in cls.source.cursor:
                member = {
                    "email": email,
                    "first_name": first_name,
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
            for ( phone_number) in cls.source.cursor:
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
            for ( country) in cls.source.cursor:
                member = {
                    "country": country,
                }

                return member
        return None



class MemberContactDA(object):
    source = source

    @classmethod
    def get_member_contacts(cls, member_id):
        contacts = list()
        get_contacts_query = ("""
            SELECT
                contact.id as id,
                contact.contact_member_id as contact_member_id,
                contact.first_name as first_name,
                contact.last_name as last_name,
                contact.cell_phone as cell_phone,
                contact.office_phone as office_phone,
                contact.home_phone as home_phone,
                contact.email as email,
                contact.personal_email as personal_email,
                contact.company_name as company_name,
                contact.company_phone as company_phone,
                contact.company_web_site as company_web_site,
                contact.company_email as company_email,
                contact.company_bio as company_bio,
                contact.country as country,
                contact.contact_role as role,
                contact.create_date as create_date,
                contact.update_date as update_date
            FROM contact
            WHERE contact.member_id = %s
            ORDER BY contact.update_date DESC
            """)
        get_contacts_params = (member_id,)
        cls.source.execute(get_contacts_query, get_contacts_params)
        if cls.source.has_results():
            for (
                    id,
                    contact_member_id,
                    first_name,
                    last_name,
                    cell_phone,
                    office_phone,
                    home_phone,
                    email,
                    personal_email,
                    company_name,
                    company_phone,
                    company_web_site,
                    company_email,
                    company_bio,
                    country,
                    role,
                    create_date,
                    update_date
            ) in cls.source.cursor:
                contact = {
                    "id": id,
                    "contact_member_id": contact_member_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "member_name": f'{first_name} {last_name}',
                    "cell_phone": cell_phone,
                    "office_phone": office_phone,
                    "home_phone": home_phone,
                    "email": email,
                    "company_name": company_name,
                    "company_phone": company_phone,
                    "company_web_site": company_web_site,
                    "company_email": company_email,
                    "company_bio": company_bio,
                    "country": country,
                    "role": role,
                    "create_date": create_date,
                    "update_date": update_date,
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
                member.last_name as last_name,
                contact.contact_member_id as contact_member_id
            FROM member
            LEFT JOIN contact ON member.id = contact.contact_member_id
            WHERE member.id <> %s
            """)
        get_members_params = (member_id,)
        cls.source.execute(get_members_query, get_members_params)
        if cls.source.has_results():
            for (
                    id,
                    first_name,
                    last_name,
                    contact_member_id
            ) in cls.source.cursor:
                if not contact_member_id:
                    member = {
                        "id": id,
                        "name": f'{first_name} {last_name}'
                    }
                    members.append(member)
        return members

    @classmethod
    def get_member_contact(cls, contact_id):
        contact = cls.__get_member_contact('id', contact_id)
        return contact

    @classmethod
    def get_member_contact_by_email(cls, email):
        return cls.__get_member_contact('email', email)

    @classmethod
    def __get_member_contact(cls, key, value):
        get_contact_query = ("""
            SELECT
                id,
                contact_member_id,
                first_name,
                last_name,
                country,
                cell_phone,
                office_phone,
                home_phone,
                email,
                personal_email,
                company_name,
                company_phone,
                company_web_site,
                company_email,
                company_bio,
                contact_role,
                create_date,
                update_date
            FROM contact
            WHERE {} = %s
            """.format(key)
                             )

        get_contact_params = (value,)
        cls.source.execute(get_contact_query, get_contact_params)
        if cls.source.has_results():
            for (
                    id,
                    contact_member_id,
                    first_name,
                    last_name,
                    country,
                    cell_phone,
                    office_phone,
                    home_phone,
                    email,
                    personal_email,
                    company_name,
                    company_phone,
                    company_web_site,
                    company_email,
                    company_bio,
                    contact_role,
                    create_date,
                    update_date
            ) in cls.source.cursor:
                contact = {
                    "id": id,
                    "contact_member_id": contact_member_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "member_name": f'{first_name} {last_name}',
                    "country": country,
                    "cell_phone": cell_phone,
                    "office_phone": office_phone,
                    "home_phone": home_phone,
                    "email": email,
                    "personal_email": personal_email,
                    "company_name": company_name,
                    "company_phone": company_phone,
                    "company_web_site": company_web_site,
                    "company_email": company_email,
                    "company_bio": company_bio,
                    "contact_role": contact_role,
                    "create_date": create_date,
                    "update_date": update_date
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
            cls.source.execute(create_member_contact_query, create_member_contact_params)
            contact_id = cls.source.get_last_row_id()

            if commit:
                cls.source.commit()
            return contact_id
        except Exception as e:
            raise e

