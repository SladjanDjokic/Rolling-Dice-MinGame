import logging
from datetime import datetime, timezone

from app.util.db import source

logger = logging.getLogger(__name__)


class ExternalAccountDA(object):
    source = source

    @classmethod
    def create_external_account(cls, member_id, account_type, username,
                                email, profile_link, company, scope, token):
        try:
            query = """
                INSERT INTO member_external_account
                 (member_id, external_account, external_username, 
                 external_email, profile_link, company, scope, token,
                 create_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            current_date = datetime.now(timezone.utc)
            params = (member_id, account_type, username, email,
                      profile_link, company, scope, token, current_date)

            cls.source.execute(query, params)
            if cls.source.has_results():
                cls.source.commit()
                (member_id, account_type, username,
                 email, profile_link, scope, token,
                 create_date, update_date
                 ) = cls.source.cursor.fetchone()
                external_account = {
                    "member_id": member_id,
                    "account_type": account_type,
                    "username": username,
                    "email": email,
                    "profile_link": profile_link,
                    "scope": scope,
                    "token": token,
                    "create_date": create_date,
                    "update_date": update_date
                }
                return external_account
            else:
                return False
        except Exception as e:
            logger.debug(e)

    @classmethod
    def update_external_account(cls, member_id, account_type, username,
                                email, profile_link, company, scope, token):
        try:
            query = """
                        UPDATE member_external_account
                        SET member_id = %s,
                        external_account = %s,
                        external_username = %s, 
                        external_email = %s,
                        profile_link = %s ,
                        company = %s,
                        scope = %s,
                        token = %s,
                        update_date = %s
                       WHERE member_id = %s and external_account=%s
                   """

            current_date = datetime.now(timezone.utc)
            params = (member_id, account_type, username, email,
                      profile_link, company, scope, token,
                      current_date, member_id, account_type)

            cls.source.execute(query, params)
            if cls.source.has_results():
                cls.source.commit()
                (member_id, account_type, username,
                 email, profile_link, scope, token,
                 create_date, update_date
                 ) = cls.source.cursor.fetchone()
                external_account = {
                    "member_id": member_id,
                    "account_type": account_type,
                    "username": username,
                    "email": email,
                    "profile_link": profile_link,
                    "scope": scope,
                    "token": token,
                    "create_date": create_date,
                    "update_date": update_date
                }
                return external_account
            else:
                return False
        except Exception as e:
            logger.debug(e)

    @classmethod
    def get_external_account_by_username(cls, username, account_type):
        query = ("""
                SELECT
                    *
                FROM member_external_account
                WHERE external_username = %s and external_account= %s
                """)

        params = (username,account_type)
        cls.source.execute(query, params)
        if cls.source.has_results():
            cls.source.commit()
            (_, member_id, account_type, username,
             email, profile_link, company, scope, token,
             create_date, update_date
             ) = cls.source.cursor.fetchone()
            external_account = {
                "member_id": member_id,
                "account_type": account_type,
                "username": username,
                "email": email,
                "profile_link": profile_link,
                "scope": scope,
                "token": token,
                "create_date": create_date,
                "update_date": update_date
            }
            return external_account
        return None

    @classmethod
    def get_external_account_by_member_id(cls, member_id, account_type):
        query = ("""
                    SELECT
                        *
                    FROM member_external_account
                    WHERE member_id = %s and external_account= %s
                    """)

        params = (member_id, account_type)
        cls.source.execute(query, params)
        if cls.source.has_results():
            cls.source.commit()
            (_, member_id, account_type, username,
             email, profile_link, company, scope, token,
             create_date, update_date
             ) = cls.source.cursor.fetchone()
            external_account = {
                "member_id": member_id,
                "account_type": account_type,
                "username": username,
                "email": email,
                "profile_link": profile_link,
                "scope": scope,
                "token": token,
                "create_date": create_date,
                "update_date": update_date
            }
            return external_account
        return None
