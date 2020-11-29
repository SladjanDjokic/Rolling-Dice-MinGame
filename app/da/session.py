import logging
import traceback
import datetime

from app.util.db import source
from app.exceptions.data import DuplicateKeyError
from app.exceptions.session import SessionExistsError
from app.util.filestorage import amerize_url

logger = logging.getLogger(__name__)


class SessionDA (object):

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
    def create_session(cls, member, session_id, expiration_date, commit=True):

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
        (session_id, member_id, email, first_name, last_name,
            username, expiration_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
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
            file_storage_engine.storage_engine_id as s3_avatar_url

        FROM member_session
        LEFT JOIN member ON member_session.member_id = member.id
        LEFT JOIN member_location ON member_session.member_id = member_location.member_id
        LEFT JOIN member_contact ON member_session.member_id = member_contact.member_id
        LEFT OUTER JOIN job_title ON member.job_title_id = job_title.id
        LEFT OUTER JOIN member_profile ON member_session.member_id = member_profile.member_id
        LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
        WHERE member_session.session_id = %s AND member_session.expiration_date >= current_timestamp
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
                s3_avatar_url
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
                "amera_avatar_url": amerize_url(s3_avatar_url)
            }

            return session

        return None

    @classmethod
    def delete_session(cls, session_id):
        query = ("""
        DELETE
        FROM member_session
        WHERE session_id = %s
        """)

        params = (session_id, )
        cls.source.execute(query, params)
        cls.source.commit()

        return None

    @classmethod
    def get_session_table(cls):
        query = ("""
        SELECT
            session_id,
            member_id,
            email,
            create_date,
            update_date,
            expiration_date,
            username,
            status,
            first_name,
            last_name
        FROM member_session
        """)

        cls.source.execute(query, [])
        if cls.source.has_results():
            for (
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
            ) in cls.source.cursor:
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
                }

                yield session
            cls.source.cursor.close()
        return None

    @classmethod
    def get_sessions(cls, search_key, page_size=None, page_number=None, sort_params=''):
        sort_columns_string = 'first_name ASC, last_name ASC'
        if sort_params:
            session_dict = {
                'session_id': 'session_id',
                'email': 'email',
                'username': 'username',
                'first_name': 'first_name',
                'last_name': 'last_name',
                'status': 'status',
                'create_date': 'create_date',
                'update_date': 'update_date',
                'expiration_date': 'expiration_date'
            }
            sort_columns_string = formatSortingParams(
                sort_params, session_dict) or sort_columns_string
        query = (f"""
            SELECT
                session_id,
                email,
                username,
                first_name,
                last_name,
                status,
                create_date,
                update_date,
                expiration_date
            FROM member_session
            WHERE
                username LIKE %s
                OR first_name LIKE %s
                OR last_name LIKE %s
                OR email LIKE %s
            ORDER BY {sort_columns_string}
            """)

        countQuery = """
            SELECT
                COUNT(*)
            FROM member_session
            WHERE 
                username LIKE %s
                OR first_name LIKE %s
                OR last_name LIKE %s
                OR email LIKE %s
            """

        like_search_key = """%{}%""".format(search_key)
        params = tuple(4 * [like_search_key])
        cls.source.execute(countQuery, params)

        count = 0
        if cls.source.has_results():
            (count, ) = cls.source.cursor.fetchone()

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
                expiration_date
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
                    "expiration_date": expiration_date
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
