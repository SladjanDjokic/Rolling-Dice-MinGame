import logging

# import uuid
# from dateutil.relativedelta import relativedelta
from app.util.db import source, formatSortingParams
from app.exceptions.data import DuplicateKeyError, DataMissingError, \
    RelationshipReferenceError
from app.exceptions.invite import InviteExistsError, InviteDataMissingError, \
    InviteInvalidInviterError
from app.util.filestorage import amerize_url
from app.da.file_sharing import FileTreeDA
from app.config import settings
from app.util.security import SECURITY_EXCHANGE_OPTIONS
from enum import Enum


class GroupRole(Enum):
    OWNER = 'owner'
    ADMIN = 'administrator'
    STANDARD = 'standard'


class GroupMemberStatus(Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    DISABLED = 'disabled'
    TEMP = 'temporary'
    INVITED = 'invited'
    DECLINED = 'declined'


class GroupExchangeOptions(Enum):
    NO_ENCRYPTION = 'NO_ENCRYPTION'
    LEAST_SECURE = 'LEAST_SECURE'
    SECURE = 'SECURE'
    VERY_SECURE = 'VERY_SECURE'
    MOST_SECURE = 'MOST_SECURE'


logger = logging.getLogger(__name__)


class GroupDA(object):
    source = source

    @classmethod
    def get_group(cls, group_id):
        return cls.__get_group('id', group_id)

    @classmethod
    def __get_group(cls, key, value, group_type='contact'):
        query = (f"""
            SELECT
                id,
                (
                    SELECT member_id
                    FROM member_group_membership
                    WHERE group_id = member_group.id
                    AND group_role = 'owner'
                ) AS group_leader_id,
                group_name,
                create_date,
                update_date,
                (
                    SELECT COUNT(*)
                    FROM member_group_membership
                    WHERE group_id = member_group.id
                ) AS total_member
            FROM member_group
            WHERE {key} = %s AND group_type = %s
        """)

        params = (value, group_type)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                    id,
                    group_leader_id,
                    group_name,
                    create_date,
                    update_date,
                    total_member
            ) in cls.source.cursor:
                group = {
                    "group_id": id,
                    "group_leader_id": group_leader_id,
                    "group_name": group_name,
                    "create_date": create_date,
                    "update_date": update_date,
                    "total_member": total_member
                }

                return group

        return None

    @classmethod
    def get_group_by_name_and_owner_id(cls, group_name, owner_id, group_type='contact'):
        query = ("""
            SELECT
                id,
                member_id as group_leader_id,
                group_name,
                member_group.create_date,
                member_group.update_date
            FROM member_group
            LEFT JOIN member_group_membership ON member_group_membership.group_id = member_group.id
            WHERE group_type = %s AND group_name = %s AND member_group_membership.member_id = %s AND member_group_membership.group_role = 'owner'
        """)
        params = (group_type, group_name, owner_id)
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
    def get_groups_by_group_leader_id(cls, group_leader_id, sort_params, group_type='contact', search_key=None):
        sort_columns_string = 'group_name ASC'
        if sort_params:
            group_dict = {
                'group_id': 'member_group.id',
                'group_leader_id': 'member_group_membership.member_id',
                'group_name': 'group_name',
                'group_create_date': 'member_group.create_date',
                'group_update_date': 'member_group.update_date',
                'group_leader_first_name': 'member.first_name',
                'group_leader_last_name': 'member.last_name',
                'group_leader_email': 'member.email',
                'total_member': 'total_member',
                'total_files': 'total_files',
                'total_videos': 'total_videos'
            }
            sort_columns_string = formatSortingParams(
                sort_params, group_dict) or sort_columns_string

        search_query = ("""
        AND (
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
        """)
        query = (f"""
            WITH online_sessions AS (
                SELECT
                    member_session.member_id,
                    CASE WHEN bool_or(member_session.status = 'online' AND member_session.status is not null) = true THEN 'online' ELSE 'offline' END as online_status
                FROM  member_session 
                WHERE
                    member_session.status IN ('online', 'disconnected') AND
                    member_session.expiration_date >= current_timestamp
                GROUP BY
                    member_session.member_id
            )

            SELECT
                member_group.id AS group_id,
                member_group_membership.member_id AS group_leader_id,
                group_name,
                exchange_option AS group_exchange_option,
                member_group.status AS group_status,
                member_group_membership.group_role AS group_role,
                member_group.create_date AS group_create_date,
                member_group.update_date AS group_create_date,
                member_group_membership.create_date AS group_join_date,
                member.first_name AS group_leader_first_name,
                member.last_name AS group_leader_last_name,
                member.email AS group_leader_email,
                COUNT(DISTINCT(membership_members.id)) AS total_member,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'id', membership_members.id,
                            'first_name', membership_members.first_name,
                            'last_name', membership_members.last_name,
                            'email', membership_members.email,
                            'company', membership_members.company_name,
                            'title', job_title.name,
                            'amera_avatar_url', file_path(file_storage_engine.storage_engine_id, '/member/file'),
                            'create_date', member_group_membership.create_date,
                            'group_id', member_group_membership.group_id,
                            'online_status', CASE WHEN online_sessions.online_status IS NOT NULL THEN online_sessions.online_status ELSE 'offline' END
                        )
                    )
                ) AS members,
                count(DISTINCT file_tree_item.id) AS total_files,
                group_type,
                (
                    CASE
                        WHEN count(file_tree_item.id) = 0 THEN 0
                        ELSE
                            sum(
                                CASE
                                    WHEN left(group_files.mime_type, 5) = 'video' THEN 1
                                    ELSE 0
                                END
                            ) * count(DISTINCT file_tree_item.id) / count(file_tree_item.id)
                    END
                ) AS total_videos
            FROM member_group
            INNER JOIN member_group_membership ON member_group.id = member_group_membership.group_id
            LEFT JOIN member ON member.id = member_group_membership.member_id
            LEFT OUTER JOIN member_group_membership AS members ON members.group_id = member_group.id
            LEFT OUTER JOIN member AS membership_members ON members.member_id = membership_members.id
            LEFT OUTER JOIN online_sessions ON membership_members.id = online_sessions.member_id
            LEFT OUTER JOIN job_title ON membership_members.job_title_id = job_title.id
            LEFT OUTER JOIN member_profile ON membership_members.id = member_profile.member_id
            LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
            LEFT OUTER JOIN file_tree ON (file_tree.id = member_group.main_file_tree)
            LEFT OUTER JOIN file_tree_item ON file_tree_item.member_file_id IS NOT NULL AND file_tree_item.file_tree_id = file_tree.id
            LEFT JOIN member_file ON member_file.id = file_tree_item.member_file_id
            LEFT JOIN file_storage_engine as group_files ON group_files.id = member_file.file_id
            WHERE member_group_membership.member_id = %s AND member_group_membership.group_role = 'owner' AND group_type = %s
            {search_query if search_key else ""}
            GROUP BY member_group.id,
                    member_group_membership.member_id,
                    group_name,
                    exchange_option,
                    member_group.status,
                    member_group_membership.group_role,
                    member_group.create_date,
                    member_group.update_date,
                    member_group_membership.create_date,
                    member.first_name,
                    member.last_name,
                    member.email
            ORDER BY {sort_columns_string}
        """)

        group_list = list()

        params = (group_leader_id, group_type)

        if search_key:
            like_search_key = f"%{search_key}%"
            params = params + tuple(13 * [like_search_key])
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
                    "total_files": row[14],
                    "group_type": row[15],
                    "total_videos": row[16],
                    "members": row[13],
                    "group_leader_name": f'{row[9]} {row[10]}'
                }
                group_list.append(group)

        return group_list

    @classmethod
    def get_all_groups_by_member_id(cls, member_id, sort_params, group_type='contact', member_only=False, search_key=None):
        sort_columns_string = 'member_group.group_name ASC'
        if sort_params:
            entity_dict = {
                'group_id': 'member_group.id',
                'group_leader_id': 'gl.group_leader_id',
                'group_name': 'group_name',
                'group_exchange_option': 'exchange_option',
                'group_status': 'member_group.status',
                'group_role': 'member_group_membership.group_role',
                'group_create_date': 'member_group.create_date',
                'group_update_date': 'member_group.update_date',
                'group_join_date': 'member_group_membership.create_date',
                'group_leader_first_name': 'gl.group_leader_first_name',
                'group_leader_last_name': 'gl.group_leader_last_name',
                'group_leader_email': 'gl.group_leader_email',
                'total_member': 'total_member',
                'total_files': 'total_files',
                'total_videos': 'total_videos'
            }
            sort_columns_string = formatSortingParams(
                sort_params, entity_dict) or sort_columns_string
        search_query = ("""
        AND (
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
        """)

        query = (f"""
            WITH online_sessions AS (
                SELECT
                    member_session.member_id,
                    CASE WHEN bool_or(member_session.status = 'online' AND member_session.status is not null) = true THEN 'online' ELSE 'offline' END as online_status
                FROM  member_session 
                WHERE
                    member_session.status IN ('online', 'disconnected') AND
                    member_session.expiration_date >= current_timestamp
                GROUP BY
                    member_session.member_id
            )

            SELECT
                member_group.id as group_id,
                gl.id AS group_leader_id,
                group_name,
                exchange_option as group_exchange_option,
                member_group.status as group_status,
                member_group_membership.group_role as group_role,
                member_group.create_date as group_create_date,
                member_group.update_date as group_create_date,
                member_group_membership.create_date as group_join_date,
                gl.first_name AS group_leader_first_name,
                gl.last_name AS group_leader_last_name,
                gl.email AS group_leader_email,
                COUNT(DISTINCT(member_group_membership.member_id)) AS total_member,
                COALESCE(
                    json_agg(
                        json_build_object(
                            'id', membership_members.id,
                            'first_name', membership_members.first_name,
                            'last_name', membership_members.last_name,
                            'email', membership_members.email,
                            'company', membership_members.company_name,
                            'title', job_title.name,
                            'amera_avatar_url', file_path(file_storage_engine.storage_engine_id, '/member/file'),
                            'create_date', member_group_membership.create_date,
                            'group_id', member_group_membership.group_id,
                            'online_status', CASE WHEN online_sessions.online_status IS NOT NULL THEN online_sessions.online_status ELSE 'offline' END
                        )
                    )
                ) AS members,
                -- (SELECT json_agg(members)) as members,
                count(DISTINCT file_tree_item.id) AS total_files,
                (
                    CASE
                        WHEN count(file_tree_item.id) = 0 THEN 0
                        ELSE
                            sum(
                            CASE
                                WHEN left(group_files.mime_type, 5) = 'video' THEN 1
                                ELSE 0
                            END
                        ) * count(DISTINCT file_tree_item.id) / count(file_tree_item.id)
                END
            )  AS total_videos
            FROM member_group
            INNER JOIN member_group_membership AS gl_membership ON member_group.id = gl_membership.group_id
            INNER JOIN member AS gl ON gl.id = gl_membership.member_id AND gl_membership.group_role = 'owner'
            INNER JOIN member_group_membership ON member_group.id = member_group_membership.group_id
            INNER JOIN member_group_membership AS group_memberships ON member_group.id = group_memberships.group_id
            INNER JOIN member AS membership_members ON membership_members.id = group_memberships.member_id
            LEFT OUTER JOIN online_sessions ON membership_members.id = online_sessions.member_id
            LEFT OUTER JOIN job_title ON membership_members.job_title_id = job_title.id
            LEFT OUTER JOIN member_profile ON membership_members.id = member_profile.member_id
            LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
            LEFT OUTER JOIN file_tree ON (file_tree.id = member_group.main_file_tree)
            LEFT OUTER JOIN file_tree_item ON file_tree_item.member_file_id IS NOT NULL
            AND file_tree_item.file_tree_id = file_tree.id
            LEFT JOIN member_file ON member_file.id = file_tree_item.member_file_id
            LEFT JOIN file_storage_engine as group_files ON group_files.id = member_file.file_id
            WHERE 
                member_group_membership.member_id = %s 
                AND group_type = %s
                {"AND member_group_membership.group_role != 'owner'" if member_only else ""}
                AND member_group.status = 'active'
                {search_query if search_key else ""}

            GROUP BY member_group.id,
                    gl.id,
                    group_name,
                    exchange_option,
                    member_group.status,
                    member_group_membership.group_role,
                    member_group.create_date,
                    member_group.update_date,
                    member_group_membership.create_date,
                    gl.first_name,
                    gl.last_name,
                    gl.email
            ORDER BY {sort_columns_string}
        """)

        group_list = list()
        if not search_key:
            search_key = ""

        like_search_key = f"%{search_key}%"
        params = (member_id, group_type)

        if search_key:
            like_search_key = f"%{search_key}%"
            params = params + \
                tuple(13 * [like_search_key])

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
                    "total_files": row[14],
                    "total_videos": row[15],
                    "members": row[13],
                    "group_leader_name": f'{row[9]} {row[10]}'
                }
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

    @classmethod
    def create_expanded_group(cls, group_name, picture_file_id, pin, main_file_tree, bin_file_tree, exchange_option, group_type='contact', commit=True):
        query = ("""
            INSERT INTO member_group (group_name, picture_file_id, pin, exchange_option, main_file_tree, bin_file_tree, group_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """)

        params = (group_name, picture_file_id, pin,
                  exchange_option, main_file_tree, bin_file_tree, group_type)

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

    """
    Used only in population scripts so no need to separate project and contact groups
    """
    @classmethod
    def get_all_groups(cls):
        groups = []
        query = ("""
            SELECT
                id,
                group_leader_id,
                main_file_tree,
                bin_file_tree
            FROM member_group
        """)
        cls.source.execute(query, None)
        if cls.source.has_results():
            for (
                    group_id,
                    group_leader_id,
                    main_file_tree,
                    bin_file_tree
            ) in cls.source.cursor:
                group = {
                    "group_id": group_id,
                    "group_leader_id": group_leader_id,
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
            SELECT
                member_group.picture_file_id,
                member_group.pin,
                member_group.exchange_option,
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

    @classmethod
    def create_group_with_trees(cls, name, exchange_option, group_type, file_id=None, pin=None):
        # First we create empty file trees
        main_file_tree_id, file_tree_id = FileTreeDA().create_tree('main', 'group', True)
        bin_file_tree_id = FileTreeDA().create_tree('bin', 'group')

        # Add default folders for Drive
        default_drive_folders = settings.get('drive.default_folders')
        default_drive_folders.sort()

        for folder_name in default_drive_folders:
            FileTreeDA().create_file_tree_entry(
                tree_id=main_file_tree_id,
                parent_id=file_tree_id,
                member_file_id=None,
                display_name=folder_name
            )

        group_id = cls.create_expanded_group(group_name=name,picture_file_id=file_id, pin=pin, exchange_option=exchange_option,main_file_tree=main_file_tree_id,bin_file_tree=bin_file_tree_id,group_type=group_type)
        return group_id

    @classmethod
    def get_all_group_invitations_by_member_id(cls, member_id, is_history=False):
        groups = list()

        try:
            invited= " AND member_group_membership.status in ('invited', 'active', 'declined')"

            if not is_history:
                invited = " AND member_group_membership.status = 'invited'"

            query = f"""
                SELECT
                    member_group.id,
                    member_group_membership.status,
                    member_group_membership.create_date,
                    member_group.group_name,
                    member.id as create_user_id,
                    member.first_name,
                    member.last_name,
                    member.email,
                    file_storage_engine.storage_engine_id
                FROM member_group_membership
                INNER JOIN member_group on member_group_membership.group_id = member_group.id
                INNER JOIN member_group_membership AS mgm_leader ON mgm_leader.group_id = member_group.id AND mgm_leader.group_role = 'owner'
                INNER JOIN member ON mgm_leader.member_id = member.id
                LEFT OUTER JOIN member_profile ON member.id = member_profile.member_id
                LEFT OUTER JOIN file_storage_engine on file_storage_engine.id = member_profile.profile_picture_storage_id
                WHERE
                    member_group_membership.member_id = %s
                    {invited}
                ORDER BY member_group_membership.create_date DESC
                LIMIT 25
            """

            params = (member_id,)

            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                        id,
                        status,
                        create_date,
                        group_name,
                        create_user_id,
                        first_name,
                        last_name,
                        email,
                        storage_engine_id
                ) in cls.source.cursor:
                    mail = {
                        "id": id,
                        "status": status,
                        "create_date": create_date,
                        "group_name": group_name,
                        "create_user_id": create_user_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "amera_avatar_url": amerize_url(storage_engine_id),
                        "invitation_type": "group_invitation"
                    }
                    groups.append(mail)

            return groups
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

class GroupMembershipDA(object):
    source = source

    @classmethod
    def create_group_membership(cls, group_id, member_id, status=GroupMemberStatus.INVITED.value, group_role=GroupRole.STANDARD.value, commit=True):
        try:
            query = ("""
                INSERT INTO member_group_membership (group_id, member_id, status, group_role)
                VALUES (%s, %s, %s, %s)
                RETURNING member_id
            """)
            params = (group_id, member_id, status, group_role)
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
                INSERT INTO member_group_membership (group_id, member_id, status, group_role)
                VALUES %s
            """)

            params = [(group_id, x, GroupMemberStatus.INVITED.value,
                       GroupRole.STANDARD.value) for x in members]
            params.append((group_id, group_leader_id,
                           GroupMemberStatus.ACTIVE.value, GroupRole.OWNER.value))
            params = tuple(params)

            cls.source.execute(query, params, True)
            if commit:
                cls.source.commit()

        except Exception:
            logger.exception('UNable to bulk create group membership')
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

    @classmethod
    def get_members_without_role(cls):
        query = """
            SELECT *
            FROM member_group_membership
            WHERE group_role IS NULL
        """
        result = []
        cls.source.execute(query, None)
        if cls.source.has_results():
            memberships = cls.source.cursor.fetchall()
            for row in memberships:
                membership = {
                    "group_id": row[0],
                    "member_id": row[1],
                }
                result.append(membership)
        return result

    @classmethod
    def set_member_group_role(cls, member_id, group_id, group_role):
        query = ("""
            UPDATE member_group_membership
            SET group_role = %s
            WHERE group_id = %s AND member_id = %s
            RETURNING group_id
        """)
        params = (group_role, group_id, member_id)
        cls.source.execute(query, params)
        cls.source.commit()


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

