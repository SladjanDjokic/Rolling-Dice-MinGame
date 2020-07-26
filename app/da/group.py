import logging

from app.util.db import source
from app.exceptions.data import DuplicateKeyError, DataMissingError,\
    RelationshipReferenceError
from app.exceptions.invite import InviteExistsError, InviteDataMissingError,\
    InviteInvalidInviterError

logger = logging.getLogger(__name__)


class GroupDA (object):

    source = source

    @classmethod
    def get_group(cls, group_id):
        return cls.__get_group('id', group_id)

    @classmethod
    def __get_group(cls, key, value):
        query = ("""
            SELECT
                id,
                group_leader_id,
                group_name,
                create_date,
                update_date
            FROM member_group
            WHERE {} = %s
            """.format(key))

        params = (value,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                id,
                group_leader_id,
                group_name,
                create_date,
                update_date,
            ) in cls.source.cursor:
                group = {
                    "group_id": id,
                    "group_leader_id": group_leader_id,
                    "group_name": group_name,
                    "create_date": create_date,
                    "update_date": update_date,
                    "total_member": 0
                }

                return group

        return None

    @classmethod
    def get_group_by_name_and_leader_id(cls, group_leader_id, group_name):
        query = ("""
            SELECT
                id,
                group_leader_id,
                group_name,
                create_date,
                update_date
            FROM member_group
            WHERE group_leader_id = %s AND group_name = %s
        """)

        params = (group_leader_id, group_name,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                    id,
                    group_leader_id,
                    group_name,
                    create_date,
                    update_date,
            ) in cls.source.cursor:
                group = {
                    "group_id": id,
                    "group_leader_id": group_leader_id,
                    "group_name": group_name,
                    "create_date": create_date,
                    "update_date": update_date
                }

                return group

        return None

    @classmethod
    def get_group_list_by_group_leader_id(cls, group_leader_id):
        query = ("""
            SELECT *
            FROM member_group
            WHERE group_leader_id = %s
            ORDER BY update_date DESC
        """)
        params = (group_leader_id,)
        cls.source.execute(query, params)
        group_list = list()
        if cls.source.has_results():
            all_group = cls.source.cursor.fetchall()
            for row in all_group:
                group = {
                    "group_id": row[0],
                    "group_leader_id": row[1],
                    "group_name": row[2],
                    "create_date": row[3],
                    "update_date": row[4]
                }
                group_id = group['group_id']
                members = GroupMembershipDA().get_members_by_group_id(group_id)
                group['total_member'] = len(members)
                group_list.append(group)
        return group_list

    @classmethod
    def create_group(cls, member_id, group_name, commit=True):
        query = ("""
            INSERT INTO member_group (group_leader_id, group_name)
            VALUES (%s, %s)
            RETURNING id
        """)

        params = (member_id, group_name)
        cls.source.execute(query, params)
        id = cls.source.get_last_row_id()

        if commit:
            cls.source.commit()

        return id


class GroupMembershipDA (object):

    source = source

    @classmethod
    def create_group_membership(cls, group_id, member_id, commit=True):
        try:
            query = ("""
                SELECT group_leader_id
                FROM member_group
                WHERE id = %s
            """)
            params = (group_id, )
            cls.source.execute(query, params)
            group_leader_id = cls.source.cursor.fetchone()[0]
            if group_leader_id == member_id:
                return None

            query = ("""
                INSERT INTO member_group_membership (group_id, member_id)
                VALUES (%s, %s)
                RETURNING member_id
            """)
            params = (group_id, member_id)
            cls.source.execute(query, params)
            id = cls.source.get_last_row_id()
            if commit:
                cls.source.commit()
            return id
        except Exception as e:
            return None

    @classmethod
    def get_group_by_member_id(cls, member_id):
        try:
            query = ("""
                SELECT
                    member_group.id,
                    member_group.group_name,
                    member_group.create_date,
                    member_group.update_date,
                    member.id,
                    member.first_name,
                    member.last_name,
                    member.email,
                    member_group_membership.create_date,
                    member_group_membership.update_date
                FROM  member_group_membership
                LEFT JOIN member_group ON member_group.id = member_group_membership.group_id
                LEFT JOIN member ON member_group.group_leader_id = member.id
                WHERE member_group_membership.member_id = %s
                ORDER BY member_group.create_date DESC
            """)
            params = (member_id,)
            group_list = list()
            cls.source.execute(query, params)
            if cls.source.has_results():
                for elem in cls.source.cursor.fetchall():
                    group = {
                        "group_id": elem[0],
                        "group_name": elem[1],
                        "group_created_date": elem[2],
                        "group_updated_date": elem[3],
                        "group_leader_id": elem[4],
                        "group_leader_first_name": elem[5],
                        "group_leader_last_name": elem[6],
                        "group_leader_email": elem[7],
                        "group_membership_create_date": elem[8],
                        "group_membership_update_date": elem[9]
                    }
                    group_id = group['group_id']
                    members = cls.get_members_by_group_id(group_id)
                    group_leader_member = {
                        "member_id": elem[4],
                        "first_name": elem[5],
                        "last_name": elem[6],
                        "email": elem[7],
                        "joined_date": elem[2]
                    }
                    members.append(group_leader_member)
                    members = sorted(members, key=lambda x: (x['joined_date']), reverse=True)
                    group['members'] = members
                    group['total_member'] = len(members)
                    group_list.append(group)
            return group_list
        except Exception as e:
            return None

    @classmethod
    def get_members_by_group_id(cls, group_id):
        try:
            query = ("""
                SELECT
                    member.id,
                    member.first_name,
                    member.last_name,
                    member.email,
                    member_group_membership.create_date
                FROM  member_group_membership
                LEFT JOIN member ON member_group_membership.member_id = member.id
                WHERE member_group_membership.group_id = %s
            """)
            params = (group_id, )
            members = list()
            cls.source.execute(query, params)
            if cls.source.has_results():
                for elem in cls.source.cursor.fetchall():
                    member = {
                        "member_id": elem[0],
                        "first_name": elem[1],
                        "last_name": elem[2],
                        "email": elem[3],
                        "joined_date": elem[4]
                    }
                    members.append(member)
            return members
        except Exception as e:
            return None

    @classmethod
    def get_members_not_in_group(cls, group_id, member_id, search_key, page_size=None, page_number=None):
        try:
            query = ("""
                SELECT
                    id,
                    first_name,
                    last_name,
                    email
                    FROM  member
                WHERE id
                    NOT IN (
                        SELECT member_id
                        FROM member_group_membership
                        WHERE member_group_membership.group_id = %s
                    )
                    AND id <> %s
                    AND (
                        email LIKE %s
                        OR username LIKE %s
                        OR first_name LIKE %s
                        OR last_name LIKE %s
                    )
                """)

            like_search_key = """%{}%""".format(search_key)
            params = (group_id, member_id, like_search_key, like_search_key, like_search_key, like_search_key)

            if page_size and page_number:
                query += """LIMIT %s OFFSET %s"""
                params = (group_id, like_search_key, like_search_key, like_search_key, like_search_key, page_size, (page_number-1)*page_size)

            members = list()
            cls.source.execute(query, params)
            if cls.source.has_results():
                for elem in cls.source.cursor.fetchall():
                    member = {
                        "member_id": elem[0],
                        "first_name": elem[1],
                        "last_name": elem[2],
                        "email": elem[3],
                    }
                    members.append(member)
            return members
        except Exception as e:
            return None

    @classmethod
    def remove_group_member(cls, group_id, member_id, commit=True):
        try:
            query = ("""
                DELETE FROM member_group_membership
                WHERE group_id = %s AND member_id = %s
            """)
            params = (group_id, member_id, )
            res = cls.source.execute(query, params)
            if commit:
                cls.source.commit()

            return member_id
        except Exception as e:
            return None


class GroupMemberInviteDA (object):

    source = source

    @classmethod
    def create_invite(cls, invite_key, email, first_name, last_name,
                      inviter_member_id, group_id, country, phone_number, expiration, commit=True):

        query = ("""
            INSERT INTO invite
                (invite_key, email, first_name, last_name,
                    inviter_member_id, group_id, country, phone_number, expiration)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """)

        params = (
            invite_key, email, first_name, last_name,
            inviter_member_id, group_id, country, phone_number, expiration
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
