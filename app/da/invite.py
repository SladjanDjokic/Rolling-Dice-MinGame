import logging
from datetime import datetime

from app.util.db import source, formatSortingParams
from app.exceptions.data import DuplicateKeyError, DataMissingError, \
    RelationshipReferenceError
from app.exceptions.invite import InviteExistsError, InviteDataMissingError, \
    InviteInvalidInviterError

logger = logging.getLogger(__name__)


class InviteDA(object):
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
            id, invite_key, email, role_id, group_id, expiration,
            first_name, last_name, inviter_member_id,
            country_code, phone_number, registered_member_id
        FROM invite
        WHERE invite_key = %s
        """)

        params = (invite_key,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            (
                id, invite_key, email,
                role_id, group_id, expiration, first_name,
                last_name, inviter_member_id,
                country, phone_number, registered_member_id
            ) = cls.source.cursor.fetchone()
            invite = {
                "id": id,
                "invite_key": invite_key,
                "email": email,
                "role_id": role_id,
                "group_id": group_id,
                "expiration": expiration,
                "first_name": first_name,
                "last_name": last_name,
                "inviter_member_id": inviter_member_id,
                "country": country,
                "phone_number": phone_number,
                "registered_member_id": registered_member_id
            }
            return invite

        return None

    @classmethod
    def get_invite_for_register(cls, invite_key):
        query = ("""
        SELECT
            id, invite_key, email, group_id, expiration,
            first_name, last_name, country_code, phone_number, registered_member_id, confirm_phone_required,
            company_id, company_name
        FROM invite
        WHERE invite_key = %s
        """)

        params = (invite_key,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            (
                id, invite_key, email, group_id, expiration,
                first_name, last_name, country, phone_number, registered_member_id, confirm_phone_required,
                company_id, company_name
            ) = cls.source.cursor.fetchone()
            invite = {
                "id": id,
                "invite_key": invite_key,
                "email": email,
                "group_id": group_id,
                "expiration": expiration,
                "first_name": first_name,
                "last_name": last_name,
                "country": country,
                "phone_number": phone_number,
                "registered_member_id": registered_member_id,
                "confirm_phone_required": confirm_phone_required,
                "company_id": company_id,
                "company_name": company_name
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
    def update_invite_expiration_date(cls, id, expiration_date, commit=True):
        query = ("""
            UPDATE invite
            SET
                update_date = CURRENT_TIMESTAMP,
                expiration = %s
            WHERE id = %s AND registered_member_id IS NULL
            RETURNING 
                update_date,
                expiration,
                first_name,
                last_name,
                invite_key,
                email
        """)
        params = (expiration_date, id,)
        try:
            cls.source.execute(query, params)
            if commit:
                cls.source.commit()

            update_date = datetime.now()

            if cls.source.has_results():
                (update_date, expiration_date, first_name, last_name,
                 invite_key, email) = cls.source.cursor.fetchone()
            else:
                return None

            return {
                "id": id,
                "first_name": first_name,
                "last_name": last_name,
                "invite_key": invite_key,
                "update_date": update_date,
                "email": email,
                "expiration_date": expiration_date
            }
        except DataMissingError as err:
            raise InviteDataMissingError from err

    @classmethod
    def delete_invite(cls, invite_key, commit=True):
        query = ("""
            DELETE FROM invite WHERE invite_key = %s
                RETURNING id, email, invite_key
        """)

        params = (invite_key,)
        try:
            cls.source.execute(query, params)
            if commit:
                cls.source.commit()

            if cls.source.has_results():
                (id, email, expiration_date) = cls.source.cursor.fetchone()
            else:
                return None
            return {
                'id': id,
                'email': email,
                'expiration_date': expiration_date,
            }
        except DataMissingError as err:
            raise InviteDataMissingError from err

    @classmethod
    def get_invites(cls, search_key, page_size=None, page_number=None, sort_params='', get_all=False, member_id=None):
        sort_columns_string = 'invite.first_name ASC, invite.last_name ASC'
        if sort_params:
            invite_dict = {
                'id': 'invite.id',
                'invite_key': 'invite.invite_key',
                'email': 'invite.email',
                'expiration': 'invite.expiration',
                'first_name': 'invite.first_name',
                'last_name': 'invite.last_name',
                'inviter_member_id': 'invite.inviter_member_id',
                'status': 'invite.registered_member_id',
                'date_invited': 'invite.create_date',
                'update_date': 'invite.update_date',
                'inviter_first_name': 'member.first_name',
                'inviter_last_name': 'member.last_name',
                'inviter_email': 'member.email',
                'company_name': 'registered_member.company_name',
                'group_id': 'member_group.id',
                'group_name': 'member_group.group_name',
                'date_registered': 'registered_member.create_date',
                'city': 'remote_city_name',
                'ip_address': 'remote_ip_address',
                'region': 'remote_region_name',
                'country': ' remote_country_name'
            }
            sort_columns_string = formatSortingParams(
                sort_params, invite_dict) or sort_columns_string

        query = (f"""
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
            registered_member.company_name,
            member_group.id,
            member_group.group_name,
            registered_member.create_date as registered_date,
            member_location.city AS remote_city_name,
            CASE WHEN member_location.province IS NOT NULL THEN member_location.province ELSE member_location.state END as remote_region_name,
            COALESCE(country_code.name, (SELECT name FROM country_code WHERE id = 840)) AS remote_country_name,
            registered_member.status AS member_status
        FROM invite
            LEFT JOIN member on invite.inviter_member_id = member.id
            LEFT JOIN member_group on invite.group_id = member_group.id
            LEFT JOIN member AS registered_member on invite.registered_member_id = registered_member.id
            LEFT JOIN member_location on member_location.member_id = registered_member.id AND member_location.location_type = 'home'
            LEFT JOIN location ON location.id  = member_location.location_id
            LEFT JOIN country_code ON country_code.id = location.country_code_id
        WHERE
            {f'inviter_member_id = %s AND' if not get_all else ''}
            ( invite.email LIKE %s
            OR invite.first_name LIKE %s
            OR invite.last_name LIKE %s
            OR member.first_name LIKE %s
            OR member.last_name LIKE %s
            OR member.email LIKE %s
            OR member_group.group_name LIKE %s )
        ORDER BY {sort_columns_string}
        """)

        countQuery = (f"""
        SELECT
            COUNT(*)
        FROM invite
            LEFT JOIN member on invite.inviter_member_id = member.id
            LEFT OUTER JOIN member_group on invite.group_id = member_group.id
            LEFT OUTER JOIN member AS registered_member on invite.registered_member_id = registered_member.id
        WHERE
            {f'inviter_member_id = %s AND' if not get_all else ''}
            ( invite.email LIKE %s
            OR invite.first_name LIKE %s
            OR invite.last_name LIKE %s
            OR member.first_name LIKE %s
            OR member.last_name LIKE %s
            OR member.email LIKE %s
            OR member_group.group_name LIKE %s )
        """)

        like_search_key = """%{}%""".format(search_key)
        params = tuple(7 * [like_search_key])
        if not get_all:
            params = (member_id, ) + params

        cls.source.execute(countQuery, params)

        count = 0
        if cls.source.has_results():
            (count,) = cls.source.cursor.fetchone()

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
                    company_name,
                    group_id,
                    group_name,
                    registered_date,
                    remote_city_name,
                    remote_region_name,
                    remote_country_name,
                    member_status
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
                    "status": "Registered" if registered_member_id else "Unregistered",
                    "create_date": create_date,
                    "update_date": update_date,
                    "inviter_first_name": inviter_first_name,
                    "inviter_last_name": inviter_last_name,
                    "inviter_email": inviter_email,
                    "group_id": group_id,
                    "group_name": group_name,
                    "registered_date": registered_date,
                    "city":  remote_city_name,
                    "company_name": company_name,
                    "region": remote_region_name,
                    "country": remote_country_name,
                    'member_status': member_status
                }
                invites.append(invite)

        return {"activities": invites, "count": count}


class MemberInviteContactDA(object):
    source = source

    @classmethod
    def create_invite(cls, invite_key, email, first_name, last_name,
                      inviter_member_id, group_id, country, country_code, phone_number,
                      expiration, role, confirm_phone_required=False, company_id=None, company_name=None, 
                      commit=True):
        query = ("""
            INSERT INTO invite
                (invite_key, email, first_name, last_name,
                    inviter_member_id, group_id, country, country_code, phone_number,
                        expiration, role_id, confirm_phone_required, company_id, company_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """)

        params = (
            invite_key, email, first_name, last_name,
            inviter_member_id, group_id, country, country_code, phone_number,
            expiration, role, confirm_phone_required, company_id, company_name
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
