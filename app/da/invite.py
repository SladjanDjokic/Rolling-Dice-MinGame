import logging
import datetime

from app.util.db import source
from app.exceptions.data import DuplicateKeyError, DataMissingError,\
    RelationshipReferenceError
from app.exceptions.invite import InviteExistsError, InviteDataMissingError,\
    InviteInvalidInviterError

logger = logging.getLogger(__name__)


class InviteDA (object):

    source = source

    @classmethod
    def create_invite(cls, invite_key, email, first_name, last_name,
                      inviter_member_id, expiration, commit=True):

        query = ("""
        INSERT INTO invite
            (invite_key, email, first_name, last_name,
                inviter_member_id, expiration)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
        """)

        params = (
            invite_key, email, first_name, last_name,
            inviter_member_id, expiration
        )
        try:
            cls.source.execute(query, params)
            invite_id = cls.source.get_last_row_id()

            if commit:
                cls.source.commit()

            return invite_id
        except DuplicateKeyError as err:
            raise InviteExistsError from err
        except DataMissingError as err:
            raise InviteDataMissingError from err
        except RelationshipReferenceError as err:
            raise InviteInvalidInviterError from err

    @classmethod
    def get_invite(cls, invite_key):
        query = ("""
        SELECT
            id, invite_key, email, expiration,
            first_name, last_name, inviter_member_id
        FROM invite
        WHERE invite_key = %s
        """)

        params = (invite_key,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            (
                id, invite_key, email, 
                expiration, first_name, 
                last_name, inviter_member_id
            ) = cls.source.cursor.fetchone()
            invite = {
                "id": id,
                "invite_key": invite_key,
                "email": email,
                "expiration": expiration,
                "first_name": first_name,
                "last_name": last_name,
                "inviter_member_id": inviter_member_id,
            }
            return invite

        return None

    @classmethod
    def update_invite_registered_member(cls, invite_key, registered_member_id, commit=True):

        query = ("""
        UPDATE invite SET
            registered_member_id = %s
        WHERE invite_key = %s
        """)

        params = (
            registered_member_id, invite_key,
        )
        try:
            cls.source.execute(query, params)

            if commit:
                cls.source.commit()
        except DataMissingError as err:
            raise InviteDataMissingError from err
        except RelationshipReferenceError as err:
            raise InviteInvalidInviterError from err

    @classmethod
    def delete_invite(cls, invite_key, commit=True):
        query = ("""
        DELETE FROM invite WHERE invite_key = %s
        """)

        params = (invite_key,)
        res = cls.source.execute(query, params)
        if commit:
            cls.source.commit()

        return res

    @classmethod
    def get_invites(cls, search_key, page_size=None, page_number=None):
        
        query = ("""
        SELECT
            invite.id,
            invite.invite_key,
            invite.email,
            invite.expiration,
            invite.first_name,
            invite.last_name,
            invite.inviter_member_id,
            invite.registered_member_id,
            invite.create_date,
            invite.update_date,
            member.first_name,
            member.last_name,
            member.email,
            member_group.id,
            member_group.group_name
        FROM invite
        LEFT JOIN member on invite.inviter_member_id = member.id
        LEFT JOIN member_group on invite.group_id = member_group.id
        WHERE 
            invite.email LIKE %s
            OR invite.first_name LIKE %s
            OR invite.last_name LIKE %s
           
            OR member.first_name LIKE %s
            OR member.last_name LIKE %s
            OR member.email LIKE %s
           
            OR member_group.group_name LIKE %s
        """)

        countQuery = ("""
        SELECT
            COUNT(*)
        FROM invite
        LEFT JOIN member on invite.inviter_member_id = member.id
        LEFT JOIN member_group on invite.group_id = member_group.id
        WHERE 
            invite.email LIKE %s
            OR invite.first_name LIKE %s
            OR invite.last_name LIKE %s
           
            OR member.first_name LIKE %s
            OR member.last_name LIKE %s
            OR member.email LIKE %s
           
            OR member_group.group_name LIKE %s
        """)

        like_search_key = """%{}%""".format(search_key)
        params = tuple(7 * [like_search_key])

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

        invites = []

        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                id,
                invite_key,
                email, 
                expiration,
                first_name,
                last_name,
                inviter_member_id,
                registered_member_id,
                create_date,
                update_date,
                inviter_first_name,
                inviter_last_name,
                inviter_email,
                group_id,
                group_name
            ) in cls.source.cursor:
                invite = {
                    "id": id,
                    "invite_key": invite_key,
                    "email": email,
                    "expiration": expiration,
                    "first_name": first_name,
                    "last_name": last_name,
                    "inviter_member_id": inviter_member_id,
                    "registered_member_id": registered_member_id,
                    "create_date": create_date,
                    "update_date": update_date,
                    "inviter_first_name": inviter_first_name,
                    "inviter_last_name": inviter_last_name,
                    "inviter_email": inviter_email,
                    "group_id": group_id,
                    "group_name": group_name
                }
                invites.append(invite)

        return { "activities": invites, "count": count }
