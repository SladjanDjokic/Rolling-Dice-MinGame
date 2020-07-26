import logging
import datetime

from app.util.db import source
from app.util.config import settings

logger = logging.getLogger(__name__)


class MemberDA (object):

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
            params = (like_search_key, like_search_key, like_search_key, like_search_key, member_id, page_size, (page_number-1)*page_size)

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
    def get_group_members(cls, member_id, search_key, page_size, page_number):

        groups_query ="""
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
                    OR id IN ( """ + group_members_query +""" ))
                AND id <> %s
                AND ( email LIKE %s
                    OR username LIKE %s
                    OR first_name LIKE %s
                    OR last_name LIKE %s )
            """

        like_search_key = """%{}%""".format(search_key)
        params = (member_id, member_id, member_id, member_id, like_search_key, like_search_key, like_search_key, like_search_key)

        if page_size and page_number:
            query += """LIMIT %s OFFSET %s"""
            params = (member_id, member_id, member_id, member_id, like_search_key, like_search_key, like_search_key, like_search_key, page_size, (page_number-1)*page_size)

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
        #store member personal info
        params_member = (email, username, password, first_name, last_name, date_of_birth)
        cls.source.execute(query_member, params_member)
        id = cls.source.get_last_row_id()
        
        #store member contact info
        params_member_contact = (id, phone_number, email)
        cls.source.execute(query_member_contact, params_member_contact)
        
        #store member location info
        params_member_location = (id, street, city, state, province, postal, country)
        cls.source.execute(query_member_location, params_member_location)        

        if commit:
            cls.source.commit()

        return id
    
