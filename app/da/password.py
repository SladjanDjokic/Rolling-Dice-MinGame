import logging
import datetime
from app.util.db import source, formatSortingParams
from app.util.filestorage import amerize_url

logger = logging.getLogger(__name__)


class PasswordDA(object):
    source = source

    @classmethod
    def add_new_password(cls, member_id, name, website, type, username, password, icon, commit=True):
        query = """INSERT INTO member_pm_account
            (member_id, website_name, website_url, website_type, username, password, website_icon)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (member_id, name, website, type, username, password, icon)
        try:
            cls.source.execute(query, params, debug_query=False)
            password_id = cls.source.get_last_row_id()

            if commit:
                cls.source.commit()
            return password_id

        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    @classmethod
    def get_passwords(cls, member_id, search_key, page_size=None, page_number=None):
        sort_columns_string = 'mpa.create_date DESC'

        query = (f"""
            SELECT
                mpa.id,
                mpa.website_name,
                mpa.website_url,
                mpa.website_type,
                fse.storage_engine_id as website_icon,
                mpa.username,
                mpa.password,
                mpa.create_date
            FROM member_pm_account mpa
            LEFT OUTER JOIN file_storage_engine fse ON fse.id = mpa.website_icon
            WHERE
                member_id = %s
                {'AND mpa.website_name like %s' if search_key and len(search_key) > 0 else ''}
            ORDER BY {sort_columns_string}
        """)
        like_search_key = """%{}%""".format(search_key)
        params = [member_id]
        if len(search_key) > 0:
            params.append(search_key)

        countQuery = f"""
            SELECT
                COUNT(DISTINCT mpa.id)
            FROM member_pm_account as mpa
            WHERE
                member_id = %s
                {'AND mpa.website_name like %s' if search_key and len(search_key) > 0 else ''}
        """
        cls.source.execute(countQuery, tuple(params))

        count = 0
        if cls.source.has_results():
            (count,) = cls.source.cursor.fetchone()

        if count > 0 and page_size and page_number >= 0:
            query += """LIMIT %s OFFSET %s"""
            offset = 0
            if page_number > 0:
                offset = page_number * page_size
            params = params + (page_size, offset)

        passwords = []
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                id,
                website_name,
                website_url,
                website_type,
                website_icon,
                username,
                password,
                create_date
            ) in cls.source.cursor:
                password = {
                    "id": id,
                    "name": website_name,
                    "website": website_url,
                    "type": website_type,
                    "icon": amerize_url(website_icon),
                    "username": username,
                    "password": password,
                    "create_date": create_date
                }

                passwords.append(password)

        return {
            "passwords": passwords,
            "count": count
        }

    @classmethod
    def get_password(cls, password_id):

        query = """
            SELECT
                mpa.id,
                mpa.website_name,
                mpa.website_url,
                mpa.website_type,
                mpa.website_icon,
                fse.storage_engine_id,
                mpa.username,
                mpa.password,
                mpa.create_date
            FROM member_pm_account as mpa
            LEFT OUTER JOIN file_storage_engine fse ON fse.id = mpa.website_icon
            WHERE
                mpa.id = %s
        """
        params = (password_id,)

        cls.source.execute(query, params)

        if cls.source.has_results():
            (
                id,
                website_name,
                website_url,
                website_type,
                website_icon,
                storage_engine_id,
                username,
                password,
                create_date
            ) = cls.source.cursor.fetchone()

            password = {
                "id": id,
                "name": website_name,
                "website": website_url,
                "type": website_type,
                "icon": website_icon,
                "storage_engine_id": storage_engine_id,
                "username": username,
                "password": password,
                "create_date": create_date
            }

            return password

        return None

    @classmethod
    def update_password(cls, password_id, name, website, type, username, password, icon):

        query = """
            UPDATE
                member_pm_account
            SET
                website_name = %s,
                website_url = %s,
                website_type = %s,
                username = %s,
                password = %s,
                website_icon = %s
            WHERE id = %s
        """
        params = (name, website, type, username, password, icon, password_id)

        cls.source.execute(query, params)
        cls.source.commit()

    @classmethod
    def update_password_favicon(cls, password_id, icon):
        query = f"""UPDATE member_pm_account
                    SET website_icon = %s
                WHERE id = %s"""

        cls.source.execute(query, (icon, password_id))
        cls.source.commit()

    @classmethod
    def delete_password(cls, password_id):

        query = """
            DELETE
            FROM member_pm_account
            WHERE id = %s
        """
        params = (password_id,)

        cls.source.execute(query, params)
        cls.source.commit()
