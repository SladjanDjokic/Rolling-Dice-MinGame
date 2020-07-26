import logging
import traceback
import datetime

from app.util.db import source
from app.exceptions.data import DuplicateKeyError
from app.exceptions.session import SessionExistsError

logger = logging.getLogger(__name__)


class SessionDA (object):

    source = source

    @classmethod
    def auth(cls, username, password):
        # TODO: CHANGE THIS LATER TO ENCRYPT IN APP
        query = ("""
        SELECT id, email, first_name, last_name, username, status FROM member
        WHERE username = %s AND password = crypt(%s, password)
        """)

        params = (username, password)
        cls.source.execute(query, params)
        if cls.source.has_results():
            (id, email, first_name, last_name, username,
                status) = cls.source.cursor.fetchone()

            member = {
                "id": id,
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "username": username,
                "status": status,
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
        WHERE session_id = %s AND expiration_date >= current_timestamp
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
    def get_sessions(cls, search_key, page_size=None, page_number=None):
        query = """
            SELECT
                session_id,
                email,
                username,
                first_name,
                last_name,
                create_date,
                update_date,
                expiration_date
            FROM member_session
            WHERE
                username LIKE %s
                OR first_name LIKE %s
                OR last_name LIKE %s
                OR email LIKE %s
            """

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
        cls.source.execute(countQuery, params);

        count = 0
        if cls.source.has_results():
            ( count, ) = cls.source.cursor.fetchone()

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
                    "create_date": create_date,
                    "update_date": update_date,
                    "expiration_date": expiration_date
                }

                sessions.append(session)

        return { "activities": sessions, "count": count }
