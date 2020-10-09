import logging

import uuid
from dateutil.relativedelta import relativedelta
from app.util.db import source
from app.exceptions.data import DuplicateKeyError, DataMissingError, \
    RelationshipReferenceError
from app.exceptions.invite import InviteExistsError, InviteDataMissingError, \
    InviteInvalidInviterError

logger = logging.getLogger(__name__)


class GroupDA(object):
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
    def get_groups_by_group_leader_id(cls, group_leader_id, sort_params):
        sort_columns_string = 'group_name ASC'
        if sort_params:
            entity_dict = {
                    'group_id': 'member_group.id',
                    'group_leader_id': 'member_group.group_leader_id',
                    'group_name': 'member_group.group_name',
                    'create_date': 'member_group.create_date',
                    'update_date': 'member_group.update_date',
                    'group_leader_first_name': 'member.first_name',
                    'group_leader_last_name': 'member.last_name',
                }
            sort_columns_string = cls.formatSortingParams(sort_params, entity_dict)
        
        group_list = list()
        query = (f"""
            SELECT
                member_group.id AS group_id,
                member_group.group_leader_id AS group_leader_id,
                member_group.group_name AS group_name,
                member_group.create_date AS create_date,
                member_group.update_date AS update_date,
                member.first_name AS group_leader_first_name,
                member.last_name AS group_leader_last_name,
                count(DISTINCT member_group_membership.member_id) AS total_member,
                count(DISTINCT shared_file.id) AS total_files
            FROM member_group
            LEFT JOIN member ON member_group.group_leader_id = member.id
            LEFT OUTER JOIN member_group_membership ON (member_group_membership.group_id = member_group.id)
            LEFT OUTER JOIN shared_file ON (shared_file.group_id = member_group.id)
            WHERE 
                member_group.group_leader_id = %s AND 
                member_group.status = 'active'
            GROUP BY 
                member_group.id,
                member_group.group_leader_id,
                member_group.group_name,
                member_group.create_date,
                member_group.update_date,
                member.first_name,
                member.last_name
            ORDER BY {sort_columns_string}
        """)
        params = (group_leader_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            all_group = cls.source.cursor.fetchall()
            for row in all_group:
                group = {
                    "group_id": row[0],
                    "group_leader_id": row[1],
                    "group_name": row[2],
                    "group_leader_name": f'{row[5]} {row[6]}',
                    "total_member": row[7],
                    "total_files": row[8],
                    "create_date": row[3],
                    "update_date": row[4],
                }
                group_list.append(group)
        return group_list

    @classmethod
    def get_all_groups_by_member_id(cls, member_id, sort_params):
        sort_columns_string = 'member_groups.group_name ASC'
        if sort_params:
            entity_dict = {
                'group_id': 'member_groups.group_id',
                'group_leader_id': 'member_groups.group_leader_id',
                'group_name': 'member_groups.group_name',
                'group_exchange_option': 'member_groups.group_exchange_option',
                'group_status': 'member_groups.group_status',
                'group_role': 'member_groups.group_role',
                'group_create_date': 'member_groups.group_create_date',
                'group_update_date': 'member_groups.group_update_date',
                'group_join_date': 'member_groups.group_join_date',
                'group_leader_first_name': 'member.first_name',
                'group_leader_last_name': 'member.last_name',
                'group_leader_email': 'member.email',
            }
            sort_columns_string = cls.formatSortingParams(
                sort_params, entity_dict)

        group_list = list()
        query = (f"""
SELECT member_groups.group_id,
       member_groups.group_leader_id,
       member_groups.group_name,
       member_groups.group_exchange_option,
       member_groups.group_status,
       member_groups.group_role,
       member_groups.group_create_date,
       member_groups.group_update_date,
       member_groups.group_join_date,
       member.first_name AS group_leader_first_name,
       member.last_name AS group_leader_last_name,
       member.email AS group_leader_email,
       count(DISTINCT group_membership_member.member_id) AS total_member,
       count(DISTINCT shared_file.id) AS total_files,
       json_agg(DISTINCT ( group_member_detail.id,
                group_member_detail.first_name,
                group_member_detail.last_name,
                group_member_detail.email,
                group_membership_member.create_date)
        ) AS members
FROM ( SELECT member_group.id AS group_id,
            member_group.group_leader_id,
            member_group.group_name,
            member_group.exchange_option AS group_exchange_option,
            member_group.status AS group_status,
            'group_leader' as group_role,
            member_group.create_date AS group_create_date,
            member_group.update_date AS group_update_date,
            NULL as group_join_date
    FROM member_group
    WHERE member_group.group_leader_id = %s
    UNION
    SELECT member_group.id AS group_id,
                member_group.group_leader_id,
                member_group.group_name,
                member_group.exchange_option AS group_exchange_option,
                member_group.status AS group_status,
                'group_member' as group_role,
                member_group.create_date AS group_create_date,
                member_group.update_date AS group_update_date,
                member_group_membership.create_date as group_join_date
    FROM member_group
    INNER JOIN member_group_membership ON (member_group.id = member_group_membership.group_id)
    WHERE member_group_membership.member_id = %s ) AS member_groups
LEFT OUTER JOIN member_group_membership AS group_membership_member ON (group_membership_member.group_id = member_groups.group_id)
LEFT OUTER JOIN member AS group_member_detail ON (group_membership_member.member_id = group_member_detail.id)
LEFT OUTER JOIN shared_file ON (shared_file.group_id = member_groups.group_id)
INNER JOIN member ON member_groups.group_leader_id = member.id
GROUP BY member_groups.group_id,
         member_groups.group_leader_id,
         member_groups.group_name,
         member_groups.group_exchange_option,
         member_groups.group_status,
         member_groups.group_role,
         member_groups.group_create_date,
         member_groups.group_update_date,
         member_groups.group_join_date,
         member.first_name,
         member.last_name,
         member.email
ORDER BY {sort_columns_string}
        """)
        params = (member_id, member_id)
        cls.source.execute(query, params)

        if cls.source.has_results():
            all_group = cls.source.cursor.fetchall()
            for row in all_group:
                group = {
                    "group_id": row[0],
                    "group_leader_id": row[1],
                    "group_name": row[2],
                    "group_exchange_option": row[3],
                    "group_status": row[4],
                    "group_role": row[5],
                    "group_create_date": row[6],
                    "group_update_date": row[7],
                    "group_join_date": row[8],
                    "group_leader_first_name": row[9],
                    "group_leader_last_name": row[10],
                    "group_leader_email": row[11],
                    "total_member": row[12],
                    "total_files": row[13],
                    "members": row[14],
                    "group_leader_name": f'{row[9]} {row[10]}'
                }
                group["members"] = [{
                    "id": m["f1"],
                    "first_name": m["f2"],
                    "last_name": m["f3"],
                    "email": m["f4"],
                    "create_date": m["f5"]
                } for m in group["members"]]
                group_list.append(group)
        
        return group_list

    @classmethod
    def formatSortingParams(cls, sort_by, entity_dict):
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
                    column= column + ' ASC'
                    new_columns_list.append(column)

        return (',').join(column for column in new_columns_list)

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

    @classmethod
    def create_expanded_group(cls, member_id, group_name, picture_file_id, pin, exchange_option, commit=True):
        query = ("""
            INSERT INTO member_group (group_leader_id, group_name, picture_file_id, pin, exchange_option)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """)

        params = (member_id, group_name, picture_file_id, pin, exchange_option)

        cls.source.execute(query, params)
        id = cls.source.get_last_row_id()
        if commit:
            cls.source.commit()

        return id

    @classmethod
    def change_group_status(cls, group_id, status, commit=True):
        query = """
            UPDATE member_group SET
                status = %s
            WHERE id = %s 
        """
        params = (status, group_id,)
        try:
            cls.source.execute(query, params)

            if commit:
                cls.source.commit()
        except Exception as err:
            raise err


class GroupMembershipDA(object):
    source = source

    @classmethod
    def create_group_membership(cls, group_id, member_id, commit=True):
        try:
            query = ("""
                SELECT group_leader_id
                FROM member_group
                WHERE id = %s
            """)
            params = (group_id,)
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
    def bulk_create_group_membership(cls, group_leader_id, group_id, members, commit=True):
        try:
            query = ("""
                INSERT INTO member_group_membership (group_id, member_id, status)
                VALUES %s
            """)

            members = filter(lambda x: x != group_leader_id, members)

            params = [(group_id, x, 'invited') for x in members]
            params = tuple(params)

            cls.source.execute(query, params, True)

            if commit:
                cls.source.commit()
        except Exception as e:
            return None

    @classmethod
    def get_group_membership_by_member_id(cls, member_id):
        try:
            query = ("""
SELECT member_group.id AS group_id,
       member_group.group_name,
       member_group.create_date,
       member_group.update_date,
       member.id AS member_id,
       member.first_name,
       member.last_name,
       member.email,
       member_group_membership.create_date,
       member_group_membership.update_date,
       count(DISTINCT group_membership_member.member_id) AS member_count,
       count(DISTINCT shared_file.id) AS file_count,
       json_agg(DISTINCT ( group_member_detail.id,
                group_member_detail.first_name,
                group_member_detail.last_name,
                group_member_detail.email,
                group_membership_member.create_date)
        ) AS members
FROM member_group_membership
INNER JOIN member_group ON (member_group.id = member_group_membership.group_id)
LEFT OUTER JOIN member_group_membership AS group_membership_member ON (group_membership_member.group_id = member_group.id)
LEFT OUTER JOIN member AS group_member_detail ON (group_membership_member.member_id = group_member_detail.id)
LEFT OUTER JOIN shared_file ON (shared_file.group_id = member_group.id)
INNER JOIN member ON member_group.group_leader_id = member.id
WHERE member_group_membership.member_id = %s
GROUP BY member_group.id,
         member_group.group_name,
         member_group.create_date,
         member_group.update_date,
         member.id,
         member.first_name,
         member.last_name,
         member.email,
         member_group_membership.create_date,
         member_group_membership.update_date
ORDER BY member_group.create_date DESC
            """)
            params = (member_id,)
            group_list = list()
            cls.source.execute(query, params)
            if cls.source.has_results():
                for elem in cls.source.cursor.fetchall():
                    # { 
                    #     "f1": 3, 
                    #     "f2": "taylor" , 
                    #     "f3": "user", 
                    #     "f4": "donald@email.com",
                    #     "f5":"2020-09-23T16:27:16.11328+00:00"
                    # }
                    # id
                    # first_name
                    # last_name
                    # email
                    # create_date
                    group = {
                        "group_id": elem[0],
                        "group_name": elem[1],
                        "group_create_date": elem[2],
                        "group_update_date": elem[3],
                        "group_leader_id": elem[4],
                        "group_leader_name": f'{elem[5]} {elem[6]}',
                        "group_leader_first_name": elem[5],
                        "group_leader_last_name": elem[6],
                        "group_leader_email": elem[7],
                        "create_date": elem[8],
                        "update_date": elem[9],
                        "total_member": elem[10],
                        "total_files": elem[11],
                        "members": elem[12]
                    }
                    group["members"] = [{
                        "id": m["f1"],
                        "first_name": m["f2"],
                        "last_name": m["f3"],
                        "email": m["f4"],
                        "create_date": m["f5"]
                    } for m in group["members"]]

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
            params = (group_id,)
            members = list()
            cls.source.execute(query, params)
            if cls.source.has_results():
                for elem in cls.source.cursor.fetchall():
                    member = {
                        "member_id": elem[0],
                        "first_name": elem[1],
                        "last_name": elem[2],
                        "email": elem[3],
                        "joined_date": elem[4],
                        "member_name": f'{elem[1]} {elem[2]}'
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
                params = (group_id, like_search_key, like_search_key, like_search_key, like_search_key, page_size,
                          (page_number - 1) * page_size)

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
            params = (group_id, member_id,)
            res = cls.source.execute(query, params)
            if commit:
                cls.source.commit()

            return member_id
        except Exception as e:
            return None


class GroupMemberInviteDA(object):
    source = source

    @classmethod
    def create_invite(cls, invite_key, email, first_name, last_name,
                      inviter_member_id, group_id, country, phone_number,
                        expiration, role, commit=True):

        query = ("""
            INSERT INTO invite
                (invite_key, email, first_name, last_name,
                    inviter_member_id, group_id, country, phone_number, 
                        expiration, role_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """)

        params = (
            invite_key, email, first_name, last_name,
            inviter_member_id, group_id, country, phone_number,
            expiration, role
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
