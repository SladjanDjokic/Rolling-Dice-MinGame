import logging

# import uuid
# from dateutil.relativedelta import relativedelta
from app.util.db import source
from app.exceptions.data import DuplicateKeyError, DataMissingError, \
    RelationshipReferenceError
from app.exceptions.invite import InviteExistsError, InviteDataMissingError, \
    InviteInvalidInviterError
from app.util.filestorage import amerize_url
from app.util.security import SECURITY_EXCHANGE_OPTIONS

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
    def get_groups_by_group_leader_id(cls, group_leader_id, sort_params, search_key = None):
        sort_columns_string = 'group_name ASC'
        if sort_params:
            group_dict = {
                'group_id': 'member_group.id',
                'group_leader_id': 'member_group.group_leader_id',
                'group_name': 'member_group.group_name',
                'group_create_date': 'member_group.create_date',
                'group_update_date': 'member_group.update_date',
                'group_leader_first_name': 'member.first_name',
                'group_leader_last_name': 'member.last_name',
                'group_leader_email': 'member.email',
                'total_member': 'total_member',
                'total_files': 'total_files'
            }
            sort_columns_string = cls.formatSortingParams(
                sort_params, group_dict) or sort_columns_string

        group_list = list()
        query = (f"""
            SELECT
                member_group.id,
                member_group.group_leader_id,
                member_group.group_name,
                member_group.exchange_option,
                member_group.status,
                'group_leader' as group_role,
                member_group.create_date,
                member_group.update_date,
                NULL as group_join_date,
                member.first_name AS group_leader_first_name,
                member.last_name AS group_leader_last_name,
                member.email AS group_leader_email,
                count(DISTINCT member_group_membership.member_id) AS total_member,
                count(DISTINCT file_tree_item.id) AS total_files,
            -- 	Members TODO: THIS QUERY NEEDS IMPROVEMENT
                (
                    SELECT json_agg(group_members) as members
                    FROM (
                        SELECT
                            member_group_membership.member_id as id,
                            member.first_name as first_name,
                            member.last_name as last_name,
                            member.email as email,
                            member.company_name as company,
                            job_title.name as title,
                            file_path(file_storage_engine.storage_engine_id, '/member/file') as amera_avatar_url,
                            member_group_membership.create_date as create_date
                        FROM member_group_membership
                        LEFT JOIN member ON member_group_membership.member_id = member.id 
                        LEFT JOIN job_title ON member.job_title_id = job_title.id
                        LEFT JOIN member_profile ON member.id = member_profile.member_id
                        LEFT JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id 
                        WHERE member_group_membership.group_id = member_group.id
                    ) AS group_members
                )
            FROM member_group
            LEFT JOIN member ON member_group.group_leader_id = member.id
            LEFT JOIN member_group_membership ON (member_group_membership.group_id = member_group.id)
            LEFT OUTER JOIN file_tree ON (file_tree.id = member_group.main_file_tree)
            LEFT OUTER JOIN (
            SELECT id, file_tree_id
            FROM file_tree_item
            WHERE file_tree_item.member_file_id is NOT NULL
            ) as file_tree_item ON (file_tree_item.file_tree_id = file_tree.id)
            WHERE
                member_group.group_leader_id = %s
                AND
                member_group.status = 'active'
                AND
                (
                    member_group.group_name ILIKE %s
                    OR concat_ws(' ', member.first_name, member.last_name) ILIKE %s
                    OR member.email ILIKE %s
                    OR concat('create year ', EXTRACT(YEAR FROM member_group.create_date)) LIKE %s
                    OR concat('create month ', EXTRACT(MONTH FROM member_group.create_date)) LIKE %s
                    OR concat('create month ', to_char(member_group.create_date, 'month')) LIKE %s
                    OR concat('create day ', EXTRACT(DAY FROM member_group.create_date)) LIKE %s
                    OR concat('create day ', to_char(member_group.create_date, 'day')) LIKE %s
                    OR concat('update year ', EXTRACT(YEAR FROM member_group.update_date)) LIKE %s
                    OR concat('update month ', EXTRACT(MONTH FROM member_group.update_date)) LIKE %s
                    OR concat('update month ', to_char(member_group.update_date, 'month')) LIKE %s
                    OR concat('update day ', EXTRACT(DAY FROM member_group.update_date)) LIKE %s
                    OR concat('update day ', to_char(member_group.update_date, 'day')) LIKE %s
                )
            GROUP BY
                member_group.id,
                member_group.group_leader_id,
                member_group.group_name,
                member_group.exchange_option,
                member_group.status,
                member_group.create_date,
                member_group.update_date,
                member.first_name,
                member.last_name,
                member.email
            ORDER BY {sort_columns_string}
        """)

        if not search_key:
            search_key = ""

        like_search_key = f"%{search_key}%"
        params = (group_leader_id, ) + tuple(13 * [like_search_key])
        cls.source.execute(query, params)
        if cls.source.has_results():
            all_group = cls.source.cursor.fetchall()
            for row in all_group:
                group = {
                    "group_id": row[0],
                    "group_leader_id": row[1],
                    "group_name": row[2],
                    "group_exchange_option": SECURITY_EXCHANGE_OPTIONS.get(row[3]),
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
                group_list.append(group)

        return group_list

    @classmethod
    def get_all_groups_by_member_id(cls, member_id, sort_params):
        sort_columns_string = 'member_groups.group_name ASC'
        if sort_params:
            entity_dict = {
                'group_id': 'member_groups.id',
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
                'total_member': 'total_member',
                'total_files': 'total_files'
            }
            sort_columns_string = cls.formatSortingParams(
                sort_params, entity_dict) or sort_columns_string

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
                count(DISTINCT file_tree_item.id) AS total_files,
                 -- 	Members TODO: THIS QUERY NEEDS IMPROVEMENT
                (
                    SELECT json_agg(group_members) as members
                    FROM (
                        SELECT
                            member_group_membership.member_id as id,
                            member.first_name as first_name,
                            member.last_name as last_name,
                            member.email as email,
                            member.company_name as company,
                            job_title.name as title,
                            file_path(file_storage_engine.storage_engine_id, '/member/file') as amera_avatar_url,
                            member_group_membership.create_date as create_date
                        FROM member_group_membership
                        LEFT JOIN member ON member_group_membership.member_id = member.id 
                        LEFT JOIN job_title ON member.job_title_id = job_title.id
                        LEFT JOIN member_profile ON member.id = member_profile.member_id
                        LEFT JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id 
                        WHERE member_group_membership.group_id = member_groups.group_id
                    ) AS group_members
                )
          FROM ( SELECT member_group.id AS group_id,
                      member_group.group_leader_id,
                      member_group.group_name,
                      member_group.exchange_option AS group_exchange_option,
                      member_group.status AS group_status,
                      'group_leader' as group_role,
                      member_group.create_date AS group_create_date,
                      member_group.update_date AS group_update_date,
                      NULL as group_join_date,
                      member_group.main_file_tree,
                      member_group.bin_file_tree
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
                          member_group_membership.create_date as group_join_date,
                          member_group.main_file_tree,
                          member_group.bin_file_tree
              FROM member_group
              INNER JOIN member_group_membership ON (member_group.id = member_group_membership.group_id)
              WHERE member_group_membership.member_id = %s ) AS member_groups
          LEFT OUTER JOIN member_group_membership AS group_membership_member ON (group_membership_member.group_id = member_groups.group_id)
          LEFT OUTER JOIN member AS group_member_detail ON (group_membership_member.member_id = group_member_detail.id)
          LEFT OUTER JOIN file_tree ON (file_tree.id = member_groups.main_file_tree)
          LEFT OUTER JOIN (
            SELECT id, file_tree_id
            FROM file_tree_item
            WHERE file_tree_item.member_file_id is NOT NULL
          ) as file_tree_item ON (file_tree_item.file_tree_id = file_tree.id)
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
                    "group_exchange_option": SECURITY_EXCHANGE_OPTIONS.get(row[3]),
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
                # group["members"] = [{
                #     "id": m["f1"],
                #     "first_name": m["f2"],
                #     "last_name": m["f3"],
                #     "email": m["f4"],
                #     "create_date": m["f5"]
                # } for m in group["members"]]
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
                    column = column + ' ASC'
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
    def create_expanded_group(cls, member_id, group_name, picture_file_id, pin, exchange_option, main_file_tree, bin_file_tree, commit=True):
        query = ("""
            INSERT INTO member_group (group_leader_id, group_name, picture_file_id, pin, exchange_option, main_file_tree, bin_file_tree)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """)

        params = (member_id, group_name, picture_file_id, pin,
                  exchange_option, main_file_tree, bin_file_tree)

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

    @classmethod
    def get_all_groups(cls):
        groups = list()
        query = ("""
            SELECT 
                id, 
                main_file_tree, 
                bin_file_tree
            FROM member_group
        """)
        cls.source.execute(query, None)
        if cls.source.has_results():
            for (
                    group_id,
                    main_file_tree,
                    bin_file_tree
            ) in cls.source.cursor:
                group = {
                    "group_id": group_id,
                    "main_file_tree": main_file_tree,
                    "bin_file_tree": bin_file_tree
                }

                groups.append(group)

        return groups

    @classmethod
    def assign_tree(cls, tree_type, group_id, tree_id):
        ''' 
            This is used to assign a tree id to an existing groups for migration purposes
        '''
        main_query = ("""
            UPDATE member_group
            SET main_file_tree = %s
            WHERE id = %s
        """)
        bin_query = ("""
            UPDATE member_group
            SET bin_file_tree = %s
            WHERE id = %s
        """)
        params = (tree_id, group_id)
        query = main_query if tree_type == 'main' else bin_query
        cls.source.execute(query, params)
        cls.source.commit()
        return True

    @classmethod
    def get_security(cls, group_id):
        query = """
            SELECT member_group.picture_file_id, member_group.pin, member_group.exchange_option,
                file_storage_engine.storage_engine_id as security_picture
            FROM member_group
                LEFT JOIN file_storage_engine ON file_storage_engine.id = member_group.picture_file_id
            WHERE member_group.id = %s
        """
        params = (group_id, )
        cls.source.execute(query, params)
        if cls.source.has_results():
            (
                picture_file_id,
                pin,
                exchange_option,
                security_picture,
            ) = cls.source.cursor.fetchone()
            return {
                "picture_file_id": picture_file_id,
                "pin": pin,
                "exchange_option": exchange_option,
                "security_picture": amerize_url(security_picture)
            }
        return None

    @classmethod
    def update_security(cls, group_id, picture_file_id, pin, exchange_option, commit=True):
        query = """
            UPDATE member_group SET
                picture_file_id = %s,
                pin = %s,
                exchange_option = %s
                WHERE
                id = %s;
        """
        params = (picture_file_id, pin, exchange_option, group_id)

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
                INSERT INTO member_group_membership (group_id, member_id, status)
                VALUES (%s, %s, %s)
                RETURNING member_id
            """)
            params = (group_id, member_id, 'invited')
            cls.source.execute(query, params)
            id = cls.source.get_last_row_id()
            if commit:
                cls.source.commit()
            return id
        except Exception:
            logger.exception('Unable to add to group membership')
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
        except Exception:
            logger.exception('UNable to bulk create group membership')
            return None

    @classmethod
    def get_group_membership_by_member_id(cls, member_id, sort_params, search_key=None):
        sort_columns_string = 'member_group.create_date DESC'
        if sort_params:
            group_dict = {
                'group_id': 'member_group.id',
                'group_name': 'member_group.group_name',
                'group_create_date': 'member_group.create_date',
                'group_update_date': 'member_group.update_date',
                'group_leader_id': 'member.id',
                'group_leader_first_name': 'member.first_name',
                'group_leader_last_name': 'member.last_name',
                'group_leader_email': 'member.email',
                'create_date': 'member_group_membership.create_date',
                'update_date': 'member_group_membership.update_date',
                'total_member': 'member_count',
                'total_files': 'file_count'
            }
            sort_columns_string = formatSortingParams(
                sort_params, group_dict) or sort_columns_string
        try:
            query = (f"""
                SELECT 
                    member_group.id AS group_id,
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
                    count(DISTINCT file_tree_item.id) AS file_count,
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
                LEFT OUTER JOIN file_tree ON (file_tree.id = member_group.main_file_tree)
                LEFT OUTER JOIN (
                  SELECT id, file_tree_id
                  FROM file_tree_item
                  WHERE file_tree_item.member_file_id is NOT NULL
                ) as file_tree_item ON (file_tree_item.file_tree_id = file_tree.id)
                INNER JOIN member ON member_group.group_leader_id = member.id
                WHERE 
                    member_group_membership.member_id = %s
                    AND
                    (
                        member_group.group_name ILIKE %s
                        OR concat_ws(' ', member.first_name, member.last_name) ILIKE %s
                        OR member.email ILIKE %s
                        OR concat('create year ', EXTRACT(YEAR FROM member_group.create_date)) LIKE %s
                        OR concat('create month ', EXTRACT(MONTH FROM member_group.create_date)) LIKE %s
                        OR concat('create month ', to_char(member_group.create_date, 'month')) LIKE %s
                        OR concat('create day ', EXTRACT(DAY FROM member_group.create_date)) LIKE %s
                        OR concat('create day ', to_char(member_group.create_date, 'day')) LIKE %s
                        OR concat('update year ', EXTRACT(YEAR FROM member_group.update_date)) LIKE %s
                        OR concat('update month ', EXTRACT(MONTH FROM member_group.update_date)) LIKE %s
                        OR concat('update month ', to_char(member_group.update_date, 'month')) LIKE %s
                        OR concat('update day ', EXTRACT(DAY FROM member_group.update_date)) LIKE %s
                        OR concat('update day ', to_char(member_group.update_date, 'day')) LIKE %s
                    )
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
                ORDER BY {sort_columns_string}
            """)

            if not search_key:
                search_key = ''

            like_search_key = f"%{search_key}%"
            params = (member_id, ) + tuple(13 * [like_search_key])
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
                    member.id as id,
                    member.first_name,
                    member.middle_name,
                    member.last_name,
                    member.email,
                    member_group_membership.create_date,
                    job_title.name as title,
                    member.company_name,
                    file_storage_engine.storage_engine_id
                FROM  member_group_membership
                LEFT JOIN member ON member_group_membership.member_id = member.id
                LEFT JOIN contact ON member.id = contact.contact_member_id
                LEFT JOIN job_title ON member.job_title_id = job_title.id
                LEFT JOIN member_profile ON contact.contact_member_id = member_profile.member_id
                LEFT JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                WHERE member_group_membership.group_id = %s
                GROUP BY
                    member.id,
                    member.first_name,
                    member.middle_name,
                    member.last_name,
                    member.email,
                    member_group_membership.create_date,
                    job_title.name,
                    member.company_name,
                    file_storage_engine.storage_engine_id
            """)
            params = (group_id,)
            members = list()
            cls.source.execute(query, params)
            if cls.source.has_results():
                for elem in cls.source.cursor.fetchall():
                    member = {
                        "member_id": elem[0],
                        "first_name": elem[1],
                        "middle_name": elem[2],
                        "last_name": elem[3],
                        "email": elem[4],
                        "joined_date": elem[5],
                        "member_name": f'{elem[1]} {elem[3]}',
                        "title": elem[6],
                        "company": elem[7],
                        "amera_avatar_url": amerize_url(elem[8])
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

            if not search_key:
                search_key = ""

            like_search_key = f"%{search_key}%"
            params = (group_id, member_id, like_search_key,
                      like_search_key, like_search_key, like_search_key)

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
            cls.source.execute(query, params)
            if commit:
                cls.source.commit()

            return member_id
        except Exception:
            logger.exception('Unable to delete from group membership')
            return None

    @classmethod
    def accept_group_invitation(cls, group_id, member_id, status, commit=True):
        try:
            query = """
                UPDATE member_group_membership SET
                    status = %s
                WHERE group_id = %s AND member_id = %s
            """
            params = (status, group_id, member_id)
            cls.source.execute(query, params)
            if commit:
                cls.source.commit()

        except Exception as err:
            logger.exception('Unable to update group membership')
            raise err


class GroupMemberInviteDA(object):
    source = source

    @classmethod
    def create_invite(cls, invite_key, email, first_name, last_name,
                      inviter_member_id, group_id, country, country_code, phone_number,
                      expiration, role, confirm_phone_required=False, commit=True):
        query = ("""
            INSERT INTO invite
                (invite_key, email, first_name, last_name,
                    inviter_member_id, group_id, country, country_code, phone_number,
                        expiration, role_id, confirm_phone_required)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """)

        params = (
            invite_key, email, first_name, last_name,
            inviter_member_id, group_id, country, country_code, phone_number,
            expiration, role, confirm_phone_required
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
