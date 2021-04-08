import json

from app.util.db import source
import logging

logger = logging.getLogger(__name__)
from app.util.filestorage import amerize_url

from app.config import settings

class ActivityDA(object):
    source = source

    @classmethod
    def insert_activity(cls, event_key="", headers={}, req_params={},
                        req_url_params={}, req_data={}, resp_data={},
                        http_status="", session_key="", session_data={},
                        member_id="", event_type="activity", status="",
                        create_date="", topic="", referer_url="", url="", commit=True):

        insert_activity_q = (
            """
            INSERT INTO activity_trace
                (event_key, headers, request_params, request_url_params,
                request_data, response, http_status, session_key,
                session_data, member_id, event_type, status, create_date,
                topic, referer_url, url)
                Values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
        )
        params = (
                    event_key, headers, req_params, req_url_params, req_data,
                    resp_data, http_status, session_key, session_data,
                    member_id, event_type, status, create_date, topic, referer_url,
                    url
                )
        try:
            cls.source.execute(insert_activity_q, params, debug_query=False)
            if commit:
                cls.source.commit()

        except Exception as e:
            logger.error(e, exc_info=True)
            return False

    # @classmethod
    # def get_recent_activity(cls):
    #     q = """
    #         SELECT * FROM activity_status LIMIT 20
    #
    #         """
    #     try:
    #         results = cls.source.execute(q)
    #         return results
    #     except Exception as e:
    #         logger.error(e, exc_info=True)

    @classmethod
    def get_recent_activity(cls, member_id, member_email):
        mails = list()
        invitations = list()
        try:
            query_mails = """
                SELECT
                    activity_trace.id,
                    activity_trace.event_key,
                    activity_trace.event_type,
                    activity_trace.request_params,
                    activity_trace.request_url_params,
                    activity_trace.request_data,
                    activity_trace.response,
                    activity_trace.http_status,
                    activity_trace.session_key,
                    activity_trace.member_id,
                    activity_trace.event_type,
                    activity_trace.status,
                    activity_trace.create_date,
                    member.first_name as first_name,
                    member.last_name as last_name,
                    job_title.name as job_title,
                    file_path(file_storage_engine.storage_engine_id, '/member/file') as s3_avatar_url,
                    xref.read,
                    video_mail_xref.status as vmail_status,
                    video_mail.type as vmail_type,
                    video_mail.subject as vmail_subject,
                    video_mail.media_type as media_type,
                    member_group.group_name
                FROM activity_trace
                LEFT OUTER JOIN member ON member.id = activity_trace.member_id
                LEFT OUTER JOIN job_title ON job_title.id = member.job_title_id
                LEFT OUTER JOIN member_profile ON activity_trace.member_id = member_profile.member_id
                LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                LEFT OUTER JOIN mail_header ON mail_header.id = (activity_trace.request_data->>'mail_id')::int
                LEFT OUTER JOIN mail_xref xref ON mail_header.id = xref.mail_header_id AND xref.member_id = %s
                LEFT OUTER JOIN video_mail ON (video_mail.id = (activity_trace.response->'video_mail_id')::int)
                LEFT OUTER JOIN video_mail_xref ON video_mail.id = video_mail_xref.video_mail_id AND video_mail_xref.status <> 'deleted'
                LEFT OUTER JOIN member_group ON member_group.id = video_mail.group_id
                WHERE
                    (
                        activity_trace.status = 'ended'
                        AND activity_trace.http_status = '200 OK'
                        AND activity_trace.response ? 'fails'
                        AND activity_trace.request_data->'receivers'->'amera' @> %s
                    )
                    OR (
                        activity_trace.status = 'ended'
                        AND activity_trace.event_type IN ('send_contact_video_mail', 'send_group_video_mail')
                        AND activity_trace.http_status = '200 OK'
                        AND video_mail_xref.member_id = %s
                    )
                ORDER BY activity_trace.create_date DESC
                LIMIT 20
            """
            query_invitations = """
                SELECT
                    activity_trace.id,
                    activity_trace.event_key,
                    activity_trace.request_params,
                    activity_trace.request_params->>'type' as invitation_type,
                    activity_trace.member_id,
                    activity_trace.event_type,
                    activity_trace.status,
                    activity_trace.http_status,
                    activity_trace.create_date,
                    member_requester.first_name as first_name,
                    member_requester.last_name as last_name,
                    job_title.name as job_title,
                    file_path(file_storage_engine.storage_engine_id, '/member/file') as s3_avatar_url,
                    contact.status AS contact_requested_status,
                    CASE
                        WHEN add_group_membership.status IS NOT NULL THEN add_group_membership.status
                        WHEN create_group_membership.status IS NOT NULL THEN create_group_membership.status
                        ELSE NULL
                    END AS group_membership_status,
                    role.name,
                    activity_trace.response
                FROM activity_trace
                LEFT OUTER JOIN member AS member_requester ON member_requester.id = activity_trace.member_id
                LEFT OUTER JOIN member AS member_requested ON member_requested.id = %s
                LEFT OUTER JOIN job_title ON job_title.id = member_requester.job_title_id
                LEFT OUTER JOIN member_profile ON activity_trace.member_id = member_profile.member_id
                LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                LEFT OUTER JOIN contact ON
                    contact.contact_member_id = activity_trace.member_id
                    AND contact.member_id = member_requested.id
                LEFT OUTER JOIN role ON contact.role_id = role.id
                LEFT OUTER JOIN member_group_membership AS add_group_membership ON
                    add_group_membership.group_id = (activity_trace.request_params->>'groupId')::INT
                    AND add_group_membership.member_id = member_requested.id
                LEFT OUTER JOIN member_group_membership AS create_group_membership ON
                    create_group_membership.group_id = (activity_trace.response->'data'->0->'group_id')::INT
                    AND create_group_membership.member_id = member_requested.id
                WHERE
                    activity_trace.status = 'ended'
                    AND
                    activity_trace.http_status = '200 OK'
                    AND
                    (
                        (
                            request_params->>'type' = 'add-contact'
                            AND
                            member_requested.id = ANY (CONCAT('{', activity_trace.request_params->>'member_id_list', '}')::int[])
                            AND
                            contact.status = 'pending'
                        )
                        OR
                        (
                            request_params->>'type' = 'add-group-member'
                            AND
                            member_requested.email = activity_trace.request_params->>'groupMemberEmail')
                            AND
                            add_group_membership.status = 'invited'
                        OR
                        (
                            request_params->>'type' = 'create-group'
                            AND
                            (request_params->>'members')::jsonb @> to_char(member_requested.id, '999')::jsonb
                            AND
                            create_group_membership.status = 'invited'
                        )
                    )
                ORDER BY activity_trace.create_date DESC
                LIMIT 10
                """
            param_mails = (member_id, str(member_id), member_id)
            param_invitations = (str(member_id),)

            # logger.debug(query_mails)
            # logger.debug(param_mails)
            cls.source.execute(query_mails, param_mails)
            if cls.source.has_results():
                for (
                        id,
                        event_key,
                        event_type,
                        request_params,
                        request_url_params,
                        request_data,
                        response,
                        http_status,
                        session_key,
                        member_id,
                        event_type,
                        status,
                        create_date,
                        first_name,
                        last_name,
                        job_title,
                        s3_avatar_url,
                        read,
                        vmail_status,
                        vmail_type,
                        vmail_subject,
                        media_type,
                        group_name
                ) in cls.source.cursor:
                    mail = {
                        "id": id,
                        "event_key": event_key,
                        "event_type": event_type,
                        "request_params": request_params,
                        "request_url_params": request_url_params,
                        "request_data": request_data,
                        "response": response,
                        "http_status": http_status,
                        "session_key": session_key,
                        "member_id": member_id,
                        "event_type": event_type,
                        "status": status,
                        "create_date": create_date,
                        "first_name": first_name,
                        "last_name": last_name,
                        "job_title": job_title,
                        "amera_avatar_url": s3_avatar_url,
                        "read": read,
                        "vmail_status": vmail_status,
                        "vmail_type": vmail_type,
                        "vmail_subject": vmail_subject,
                        "media_type": media_type,
                        "group_name": group_name
                    }
                    mails.append(mail)

            cls.source.execute(query_invitations, param_invitations)
            if cls.source.has_results():
                for (
                        id,
                        event_key,
                        request_params,
                        invitation_type,
                        member_id,
                        event_type,
                        status,
                        http_status,
                        create_date,
                        first_name,
                        last_name,
                        job_title,
                        s3_avatar_url,
                        contact_requested_status,
                        group_membership_status,
                        role,
                        response
                ) in cls.source.cursor:
                    contact_invitaiton = {
                        "id": id,
                        "event_key": event_key,
                        "request_params": request_params,
                        "invitation_type": invitation_type,
                        "member_id": member_id,
                        "event_type": event_type,
                        "status": status,
                        "http_status": http_status,
                        "create_date": create_date,
                        "first_name": first_name,
                        "last_name": last_name,
                        "job_title": job_title,
                        "amera_avatar_url": s3_avatar_url,
                        "contact_requested_status": contact_requested_status,
                        "group_membership_status": group_membership_status,
                        "role": role,
                        "response": response,
                    }
                    invitations.append(contact_invitaiton)

            return {
                "invitations": {
                    "id"   : 2,
                    "type" : 'invitations',
                    "data" : invitations
                },
                "mails": {
                    "id"   : 3,
                    "type" : 'mails',
                    "data" : mails
                },
            }
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    @classmethod
    def get_recent_activity_users(cls, get_all=False):
        users = list()
        query = f"""
            SELECT
                member_id,
                member.first_name,
                member.last_name
            FROM activity_trace
            LEFT OUTER JOIN member ON member.id = activity_trace.member_id
            WHERE
                activity_trace.member_id IS NOT NULL
            GROUP BY
                member_id,
                member.first_name,
                member.last_name
            ORDER BY
                member.first_name,
                member.last_name
        """
        params = ()

        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                member_id,
                first_name,
                last_name
            ) in cls.source.cursor:
                user = {
                    "member_id": member_id,
                    "first_name": first_name,
                    "last_name": last_name
                }
                users.append(user)

        return users

    @classmethod
    def get_user_global_behaviour(cls, search_key, page_size=None, page_number=None, sort_params='', get_all=False, member_id=None):
        try:
            sort_columns_string = 'min(activity_trace.create_date) DESC'
            activities = list()
            if sort_params:
                activities_dict = {
                    'member_id': 'activity_trace.member_id',
                    'first_name': 'member.first_name',
                    'last_name': 'member.last_name',
                    'referer_url': 'activity_trace.referer_url',
                    # 'event_types': 'event_types', currently not sure how to sort by json_agg
                    'create_date': 'min(activity_trace.create_date)',
                }
                sort_columns_string = cls.formatSortingParams(
                    sort_params, activities_dict) or sort_columns_string

            query = (f"""
                SELECT
                    activity_trace.member_id,
                    member.first_name,
                    member.last_name,
                    activity_trace.referer_url as referer_url,
                    json_agg(DISTINCT activity_trace.event_type) as event_types,
                    min(activity_trace.create_date) as create_date
                FROM
                    activity_trace
                LEFT OUTER JOIN member ON member.id = activity_trace.member_id
                WHERE
                    {f"activity_trace.member_id = {member_id} AND " if member_id else ""}
                    activity_trace.event_type != 'attempt_validate_session'
                    AND activity_trace.referer_url IS NOT NULL
                    AND activity_trace.status = 'ended'
                    AND
                    (
                        activity_trace.referer_url LIKE %s
                        OR member.first_name LIKE %s
                        OR member.last_name LIKE %s
                    )
                GROUP BY
                    activity_trace.referer_url,
                    member.first_name,
                    member.last_name,
                    activity_trace.member_id
                ORDER BY {sort_columns_string}
            """)

            countQuery = (f"""
                SELECT COUNT(*)
                    FROM
                        (
                            SELECT
                                activity_trace.member_id,
                                member.first_name,
                                member.last_name,
                                activity_trace.referer_url as referer_url,
                                json_agg(DISTINCT activity_trace.event_type) as event_types,
                                min(activity_trace.create_date) as create_date
                            FROM
                                activity_trace
                            LEFT OUTER JOIN member ON member.id = activity_trace.member_id
                            WHERE
                                {f"activity_trace.member_id = {member_id} AND " if member_id else ""}
                                activity_trace.event_type != 'attempt_validate_session'
                                AND activity_trace.referer_url IS NOT NULL
                                AND activity_trace.status = 'ended'
                                AND
                                (
                                    activity_trace.referer_url LIKE %s
                                    OR member.first_name LIKE %s
                                    OR member.last_name LIKE %s
                                )
                            GROUP BY
                                activity_trace.referer_url,
                                member.first_name,
                                member.last_name,
                                activity_trace.member_id
                        ) src;
                """)

            like_search_key = """%{}%""".format(search_key)
            params = tuple(3 * [like_search_key])

            cls.source.execute(countQuery, params)

            count = 0
            if cls.source.has_results():
                (count,) = cls.source.cursor.fetchone()

            if page_size and page_number >= 0:
                query += """LIMIT %s OFFSET %s"""
                offset = 0
                if page_number > 0:
                    offset = page_number * page_size
                params = params + (page_size, offset)

            logger.debug(f'members behaviour params {params} {query} {search_key}, {page_size}, {page_number}, {sort_params}, {get_all}, {member_id}')

            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                        member_id,
                        first_name,
                        last_name,
                        referer_url,
                        event_types,
                        create_date
                ) in cls.source.cursor:
                    activity = {
                        "member_id": member_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "referer_url": referer_url,
                        "event_types": event_types,
                        "create_date": create_date
                    }
                    activities.append(activity)

                return {"activities": activities, "count": count}
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

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

    def get_group_drive_activity(cls, group_id, search_key, page_size=None, page_number=None, sort_params=''):
        try:
            sort_columns_string = 'a.create_date DESC'
            activities = list()
            if sort_params:
                activities_dict = {
                    'member_id': 'a.member_id',
                    'first_name': 'member.first_name',
                    'last_name': 'member.last_name',
                    # 'event_types': 'event_types', currently not sure how to sort by json_agg
                    'create_date': 'a.create_date',
                }
                sort_columns_string = cls.formatSortingParams(
                    sort_params, activities_dict) or sort_columns_string

            event_types = [settings.get(f'kafka.event_types.{method}.group_file_cloud') for method in [
                                'get', 'post', 'put', 'delete']]
            event_types = ','.join([f"'{event}'" for event in event_types])
            query = (f"""
                WITH tmp_node AS (
                        SELECT jsonb_array_elements(a2.request_data -> 'node_ids_list')::INTEGER AS node_id, a2.id AS key_id
                        FROM activity_trace a2
                        )
                SELECT a.member_id,
                    member.first_name,
                    member.last_name,
                    a.event_type,
                    a.create_date,
                    a.request_params,
                    a.request_data,
                    fti.display_name
                FROM activity_trace a
                LEFT JOIN tmp_node ON tmp_node.key_id = a.id
                LEFT JOIN file_tree_item fti ON fti.id = tmp_node.node_id
                LEFT JOIN member ON member.id = a.member_id
                WHERE
                    (
                        a.event_type IN ({event_types})
                    )
                    AND a.request_url_params->>'group_id' = %s
                    AND a.status = 'ended'
                    AND
                    (
                        member.first_name LIKE %s
                        OR member.last_name LIKE %s
                    )
                ORDER BY {sort_columns_string}
            """)

            countQuery = (f"""
                SELECT COUNT(*)
                    FROM
                        (
                            WITH tmp_node AS (
                                    SELECT jsonb_array_elements(a2.request_data -> 'node_ids_list')::INTEGER AS node_id, a2.id AS key_id
                                    FROM activity_trace a2
                                    )
                            SELECT a.member_id,
                                member.first_name,
                                member.last_name,
                                a.event_type,
                                a.create_date,
                                a.request_params,
                                a.request_data,
                                fti.display_name
                            FROM activity_trace a
                            LEFT JOIN tmp_node ON tmp_node.key_id = a.id
                            LEFT JOIN file_tree_item fti ON fti.id = tmp_node.node_id
                            LEFT JOIN member ON member.id = a.member_id
                            WHERE
                                (
                                    a.event_type IN ({event_types})
                                )
                                AND a.request_url_params->>'group_id' = %s
                                AND a.status = 'ended'
                                AND
                                (
                                    member.first_name LIKE %s
                                    OR member.last_name LIKE %s
                                )
                        ) src;
                """)

            like_search_key = """%{}%""".format(search_key)
            params = tuple([str(group_id),]) + tuple(2 * [like_search_key])

            cls.source.execute(countQuery, params)

            count = 0
            if cls.source.has_results():
                (count,) = cls.source.cursor.fetchone()

            if page_size and page_number >= 0:
                query += """LIMIT %s OFFSET %s"""
                offset = 0
                if page_number > 0:
                    offset = page_number * page_size
                params = params + (page_size, offset)


            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                        member_id,
                        first_name,
                        last_name,
                        event_type,
                        create_date,
                        request_data,
                        request_params,
                        display_name
                ) in cls.source.cursor:
                    activity = {
                        "member_id": member_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "event_type": event_type,
                        "create_date": create_date,
                        "request_data": request_data,
                        "request_params": request_params,
                        "display_name": display_name
                    }
                    activities.append(activity)
            return {"activities": activities, "count": count }
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    def get_group_calendar_activity(cls, group_id, search_key, page_size=None, page_number=None, sort_params=''):
        try:
            sort_columns_string = 'activity_trace.create_date DESC'
            activities = list()
            if sort_params:
                activities_dict = {
                    'member_id': 'activity_trace.member_id',
                    'first_name': 'member.first_name',
                    'last_name': 'member.last_name',
                    # 'event_types': 'event_types', currently not sure how to sort by json_agg
                    'create_date': 'activity_trace.create_date',
                }
                sort_columns_string = cls.formatSortingParams(
                    sort_params, activities_dict) or sort_columns_string
            event_types = [
                'kafka.event_types.post.create_event',
                'kafka.event_types.post.create_event_attachment',
                'kafka.event_types.post.calendar_event_status_update',
                'kafka.event_types.post.invite_users_to_event',
                'kafka.event_types.post.invite_single_user_event',
                'kafka.event_types.put.edit_event',
                'kafka.event_types.delete.delete_event',
                'kafka.event_types.delete.delete_event_attachment',
                'kafka.event_types.get.event_invite_response',
            ]
            event_types = [settings.get(event) for event in event_types]
            event_types = ','.join([f"'{event}'" for event in event_types])

            query = (f"""
                SELECT
                    activity_trace.member_id,
                    member.first_name,
                    member.last_name,
                    activity_trace.event_type as event_type,
                    activity_trace.create_date,
                    activity_trace.request_params
                FROM
                    activity_trace
                    LEFT JOIN member ON member.id = activity_trace.member_id
                WHERE
                    activity_trace.event_type IN ({event_types})
                    AND activity_trace.request_params ? 'event_data'
                    AND (activity_trace.request_params->>'event_data')::jsonb->>'inviteMode' = 'group'
                    AND (activity_trace.request_params->>'event_data')::jsonb->>'invitedGroup' = %s
                    AND activity_trace.status = 'ended'
                    AND
                    (
                        member.first_name LIKE %s
                        OR member.last_name LIKE %s
                    )
                ORDER BY {sort_columns_string}
            """)

            countQuery = (f"""
                SELECT
                    count(*)
                FROM
                    activity_trace
                    LEFT JOIN member ON member.id = activity_trace.member_id
                WHERE
                    activity_trace.event_type IN ({event_types})
                    AND activity_trace.request_params ? 'event_data'
                    AND (activity_trace.request_params->>'event_data')::jsonb->>'inviteMode' = 'group'
                    AND (activity_trace.request_params->>'event_data')::jsonb->>'invitedGroup' = %s
                    AND activity_trace.status = 'ended'
                    AND
                    (
                        member.first_name LIKE %s
                        OR member.last_name LIKE %s
                    )
                """)

            like_search_key = """%{}%""".format(search_key)
            params = tuple([str(group_id),]) + tuple(2 * [like_search_key])

            cls.source.execute(countQuery, params)

            count = 0
            if cls.source.has_results():
                (count,) = cls.source.cursor.fetchone()

            if page_size and page_number >= 0:
                query += """LIMIT %s OFFSET %s"""
                offset = 0
                if page_number > 0:
                    offset = page_number * page_size
                params = params + (page_size, offset)


            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                        member_id,
                        first_name,
                        last_name,
                        event_type,
                        create_date,
                        request_params
                ) in cls.source.cursor:
                    activity = {
                        "member_id": member_id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "event_type": event_type,
                        "create_date": create_date,
                        "request_params": request_params
                    }
                    activities.append(activity)
            return {"activities": activities, "count": count }
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
    
    @classmethod
    def get_invitations_by_member_id(cls, member_id, is_history=False, search_key='', page_size=None, page_number=None, sort_params=''):
        try:
            activities = list()
            sort_columns_string = 'update_date DESC'
            invitation_dict = {
                "id": 'id',
                "first_name": 'last_name',
                "last_name": 'last_name',
                "status": 'status',
                "file_name": 'file_name',
                "requester_contact_id": 'requester_contact_id',
                "create_date": 'create_date',
                "update_date": 'update_date',
            }

            if sort_params:
                sort_columns_string = cls.formatSortingParams(
                    sort_params, invitation_dict) or sort_columns_string
            
            # pending = ""

            # if not is_history:
            #     pending = " AND receiver_contact.status = 'pending'"

            empty_obj = '{}'

            query = f"""
                SELECT  id, first_name, last_name, email, status, file_name,
                        requester_contact_id, create_date, update_date, invitation_type,
                        event_name, event_type, event_description,
                        row_number() OVER (ORDER BY {sort_columns_string}) AS row_id,
                        storage_engine_id, create_user_id, file_url, host_member_info, invitations
                FROM  (
                        SELECT
                            receiver_contact.id as id,
                            member.first_name as first_name,
                            member.last_name as last_name,
                            member.email as email,
                            receiver_contact.status::text as status,
                            '' as file_name,
                            contact.id as requester_contact_id,
                            receiver_contact.create_date as create_date,
                            receiver_contact.update_date as update_date,
                            'contact_invitation' as invitation_type,
                            '' as event_name,
                            '' as event_type,
                            '' as event_description,
                            file_storage_engine.storage_engine_id,
                            member.id as create_user_id,
                            '' as file_url,
                            '{empty_obj}'::json AS host_member_info,
                            '{empty_obj}'::json AS invitations
                        FROM contact
                            INNER JOIN contact receiver_contact ON 
                                contact.contact_member_id = receiver_contact.member_id 
                            AND contact.member_id = receiver_contact.contact_member_id
                            INNER JOIN member ON contact.member_id = member.id
                            LEFT JOIN member_profile ON member.id = member_profile.member_id
                            LEFT JOIN file_storage_engine on file_storage_engine.id = member_profile.profile_picture_storage_id
                        WHERE 
                            receiver_contact.member_id = %s
                            AND
                            (
                                concat_ws(' ', member.first_name, member.last_name) iLIKE %s
                                OR concat('create year ', EXTRACT(YEAR FROM receiver_contact.update_date)) iLIKE %s
                                OR concat('create month ', EXTRACT(MONTH FROM receiver_contact.update_date)) iLIKE %s
                                OR concat('create month ', to_char(receiver_contact.update_date, 'month')) iLIKE %s
                                OR concat('create day ', EXTRACT(DAY FROM receiver_contact.update_date)) iLIKE %s
                                OR concat('create day ', to_char(receiver_contact.update_date, 'day')) iLIKE %s
                                OR concat('update year ', EXTRACT(YEAR FROM receiver_contact.update_date)) iLIKE %s
                                OR concat('update month ', EXTRACT(MONTH FROM receiver_contact.update_date)) iLIKE %s
                                OR concat('update month ', to_char(receiver_contact.update_date, 'month')) iLIKE %s
                                OR concat('update day ', EXTRACT(DAY FROM receiver_contact.update_date)) iLIKE %s
                                OR concat('update day ', to_char(receiver_contact.update_date, 'day')) iLIKE %s
                            )
                    UNION ALL
                        SELECT
                            event_sequence.id as id,
                            member.first_name as first_name,
                            member.last_name as last_name,
                            member.email as email,
                            event_invite_2.invite_status::text as status, 
                            '' as file_name,
                            0 as requester_contact_id,
                            event_sequence.create_date as create_date,
                            event_sequence.update_date as update_date,
                            'event_invitation' as invitation_type,
                            event_2.event_name::text as event_name,
                            event_2.event_type::text as event_type,
                            event_2.event_description::text as event_description,
                            file_storage_engine.storage_engine_id,
                            member.id as create_user_id,
                            '' as file_url,
                            json_build_object(
                                'host_member_id', member.id,
                                'first_name', member.first_name,
                                'middle_name', member.middle_name,
                                'last_name', member.last_name
                            ) AS host_member_info,
                            json_agg(json_build_object(
                                'invite_id', invitations.id,
                                'invite_member_id', invitations.invite_member_id,
                                'first_name', invited_member.first_name,
                                'middle_name', invited_member.middle_name,
                                'last_name', invited_member.last_name
                            )) AS invitations

                        FROM event_sequence
                            INNER JOIN event_2 on event_2.sequence_id = event_sequence.id
                            INNER JOIN event_invite_2 on event_invite_2.event_id = event_2.id
                            INNER JOIN member ON event_2.host_member_id = member.id
                            LEFT OUTER JOIN event_invite_2 AS invitations ON invitations.event_id = event_2.id
                            LEFT OUTER JOIN member AS invited_member ON invitations.invite_member_id = invited_member.id
                            LEFT JOIN member_profile ON member.id = member_profile.member_id
                            LEFT JOIN file_storage_engine on file_storage_engine.id = member_profile.profile_picture_storage_id
                        WHERE
                            event_invite_2.invite_member_id = %s
                            AND
                            event_2.event_status='Active'
                            AND
                            event_invite_2.invite_status != 'Recurring'
                            AND
                            event_2.group_id is NULL
                            AND
                            (
                                concat_ws(' ', member.first_name, member.last_name) iLIKE %s
                                OR concat('create year ', EXTRACT(YEAR FROM event_sequence.update_date)) iLIKE %s
                                OR concat('create month ', EXTRACT(MONTH FROM event_sequence.update_date)) iLIKE %s
                                OR concat('create month ', to_char(event_sequence.update_date, 'month')) iLIKE %s
                                OR concat('create day ', EXTRACT(DAY FROM event_sequence.update_date)) iLIKE %s
                                OR concat('create day ', to_char(event_sequence.update_date, 'day')) iLIKE %s
                                OR concat('update year ', EXTRACT(YEAR FROM event_sequence.update_date)) iLIKE %s
                                OR concat('update month ', EXTRACT(MONTH FROM event_sequence.update_date)) iLIKE %s
                                OR concat('update month ', to_char(event_sequence.update_date, 'month')) iLIKE %s
                                OR concat('update day ', EXTRACT(DAY FROM event_sequence.update_date)) iLIKE %s
                                OR concat('update day ', to_char(event_sequence.update_date, 'day')) iLIKE %s
                            )
                        GROUP BY
                            event_sequence.id,
                            event_invite_2.invite_status,
                            event_sequence.create_date,
                            event_2.event_name,
                            event_2.event_type,
                            event_2.event_description,
                            member.id,
                            member.first_name,
                            member.last_name,
                            member.email,
                            file_storage_engine.storage_engine_id
                    UNION ALL
                        SELECT
                            file_share.id as id,
                            create_user.first_name as first_name,
                            create_user.last_name as last_name,
                            create_user.email as email,
                            '' as status,
                            member_file.file_name as file_name,
                            0 as requester_contact_id,
                            file_share.create_date as create_date,
                            file_share.update_date as update_date,
                            'drive_share' as invitation_type,
                            '' as event_name,
                            '' as event_type,
                            '' as event_description,
                            file_storage_engine.storage_engine_id,
                            create_user.id as create_user_id,
                            file.storage_engine_id as file_url,
                            '{empty_obj}'::json AS host_member_info,
                            '{empty_obj}'::json AS invitations
                        FROM member
                            INNER JOIN file_tree on member.main_file_tree = file_tree.id
                            INNER JOIN file_tree_item on file_tree.id = file_tree_item.file_tree_id
                            INNER JOIN file_share on file_share.target_node = file_tree_item.id
                            INNER JOIN member_file on member_file.id = file_tree_item.member_file_id
                            INNER JOIN member create_user ON member_file.member_id = create_user.id
                            LEFT JOIN member_profile ON create_user.id = member_profile.member_id
                            LEFT JOIN file_storage_engine on file_storage_engine.id = member_profile.profile_picture_storage_id
                            LEFT JOIN file_storage_engine file on file.id = member_file.file_id
                        WHERE
                            member.id = %s
                            AND
                            (
                                concat_ws(' ', create_user.first_name, create_user.last_name) iLIKE %s
                                OR concat('create year ', EXTRACT(YEAR FROM file_share.update_date)) iLIKE %s
                                OR concat('create month ', EXTRACT(MONTH FROM file_share.update_date)) iLIKE %s
                                OR concat('create month ', to_char(file_share.update_date, 'month')) iLIKE %s
                                OR concat('create day ', EXTRACT(DAY FROM file_share.update_date)) iLIKE %s
                                OR concat('create day ', to_char(file_share.update_date, 'day')) iLIKE %s
                                OR concat('update year ', EXTRACT(YEAR FROM file_share.update_date)) iLIKE %s
                                OR concat('update month ', EXTRACT(MONTH FROM file_share.update_date)) iLIKE %s
                                OR concat('update month ', to_char(file_share.update_date, 'month')) iLIKE %s
                                OR concat('update day ', EXTRACT(DAY FROM file_share.update_date)) iLIKE %s
                                OR concat('update day ', to_char(file_share.update_date, 'day')) iLIKE %s
                            )
                    ) as results
                ORDER BY {sort_columns_string}
            """

            like_search_key = f"%{search_key}%"
            params = (member_id,) + (like_search_key,)*11
            params = params * 3

            countQuery = f"SELECT COUNT(*) FROM ({query}) src"

            cls.source.execute(countQuery, params)

            count = 0
            if cls.source.has_results():
                (count,) = cls.source.cursor.fetchone()

            if page_size and page_number >= 0:
                query += "LIMIT %s OFFSET %s"
                offset = 0
                if page_number > 0:
                    offset = page_number * page_size
                params = params + (page_size, offset)

            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                        id,
                        first_name,
                        last_name,
                        email,
                        status,
                        file_name,
                        requester_contact_id,
                        create_date,
                        update_date,
                        invitation_type,
                        event_name,
                        event_type,
                        event_description,
                        row_id,
                        storage_engine_id,
                        create_user_id,
                        file_url,
                        host_member_info,
                        invitations
                ) in cls.source.cursor:
                    activity = {
                        "id": id,
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "status": status,
                        "file_name": file_name,
                        "requester_contact_id": requester_contact_id,
                        "create_date": create_date,
                        "update_date": update_date,
                        "invitation_type": invitation_type,
                        "event_name": event_name,
                        "event_type": event_type,
                        "event_description": event_description,
                        "row_id": row_id,
                        "amera_avatar_url": amerize_url(storage_engine_id),
                        "create_user_id": create_user_id,
                        "file_url": amerize_url(file_url),
                        "host_member_info": host_member_info,
                        "invitations": invitations
                    }
                    activities.append(activity)

            return {
                'invitations' : activities,
                'count': count
            }
        except Exception as e:
            logger.error(e, exc_info=True)
            return None


    @classmethod
    def get_group_invitations_by_member_id(cls, member_id, is_history=False, search_key='', page_size=None, page_number=None, sort_params=''):
        try:
            invitations = list()
            sort_columns_string = 'update_date DESC'
            invitation_dict = {
                "id": "id",
                "status": "status",
                "name": "name",
                "event_type": "event_type",
                "first_name": "first_name",
                "last_name": "last_name",
                "email": "email",
                "storage_engine_id": "storage_engine_id",
                "create_user_id": "create_user_id",
                "description": "description",
                "group_id": "group_id",
                "group_name": "group_name",
                "group_info": "group_info",
                "create_date": "create_date",
                "update_date": "update_date"
            }

            if sort_params:
                sort_columns_string = cls.formatSortingParams(
                    sort_params, invitation_dict) or sort_columns_string
            
            invited= " AND member_group_membership.status in ('invited', 'active', 'declined')"
            if not is_history:
                invited = " AND member_group_membership.status = 'invited'"

            query = f"""
                SELECT id, status, event_name, event_type, first_name, last_name, email,
                        storage_engine_id, create_user_id, event_description, group_id,
                        group_name, group_info, create_date, update_date, invitation_type,
                        row_number() OVER (ORDER BY {sort_columns_string}) AS row_id
                FROM (
                        SELECT
                            member_group.id as id,
                            member_group_membership.status::text as status,
                            '' as event_name,
                            '' as event_type,
                            member.first_name as first_name,
                            member.last_name as last_name,
                            member.email as email,
                            file_storage_engine.storage_engine_id as storage_engine_id,
                            member.id as create_user_id,
                            '' as event_description,
                            member_group.id as group_id,
                            member_group.group_name as group_name,
                            jsonb_build_object(
                                'group_id', member_group.id,
                                'group_name', member_group.group_name,
                                'group_leader_id', member_group.group_leader_id
                            ) AS group_info,
                            member_group_membership.create_date as create_date,
                            member_group_membership.update_date as update_date,
                            'group_invitation' as invitation_type 
                        FROM member_group_membership
                            INNER JOIN member_group on member_group_membership.group_id = member_group.id
                            INNER JOIN member ON member_group.group_leader_id = member.id
                            LEFT JOIN member_profile ON member.id = member_profile.member_id
                            LEFT JOIN file_storage_engine on file_storage_engine.id = member_profile.profile_picture_storage_id
                        WHERE
                            member_group_membership.member_id = %s 
                            {invited}
                            AND
                            (
                                concat_ws(' ', member.first_name, member.last_name) iLIKE %s
                                OR concat('create year ', EXTRACT(YEAR FROM member_group_membership.create_date)) iLIKE %s
                                OR concat('create month ', EXTRACT(MONTH FROM member_group_membership.create_date)) iLIKE %s
                                OR concat('create month ', to_char(member_group_membership.create_date, 'month')) iLIKE %s
                                OR concat('create day ', EXTRACT(DAY FROM member_group_membership.create_date)) iLIKE %s
                                OR concat('create day ', to_char(member_group_membership.create_date, 'day')) iLIKE %s
                                OR concat('update year ', EXTRACT(YEAR FROM member_group_membership.update_date)) iLIKE %s
                                OR concat('update month ', EXTRACT(MONTH FROM member_group_membership.update_date)) iLIKE %s
                                OR concat('update month ', to_char(member_group_membership.update_date, 'month')) iLIKE %s
                                OR concat('update day ', EXTRACT(DAY FROM member_group_membership.update_date)) iLIKE %s
                                OR concat('update day ', to_char(member_group_membership.update_date, 'day')) iLIKE %s
                            )
                    UNION
                        SELECT
                            event_invite_2.id as id,
                            event_invite_2.invite_status::text as status,
                            event_2.event_name as event_name,
                            event_2.event_type::text as event_type,
                            member.first_name as first_name,
                            member.last_name as last_name,
                            member.email as email, 
                            file_storage_engine.storage_engine_id as storage_engine_id,
                            member.id as create_user_id,
                            event_2.event_description as event_description,
                            member_group.id as group_id,
                            member_group.group_name as group_name,
                            jsonb_build_object(
                                'group_id', member_group.id,
                                'group_name', member_group.group_name,
                                'group_leader_id', member_group.group_leader_id
                            ) AS group_info,
                            event_invite_2.create_date as create_date,
                            event_invite_2.update_date as update_date,
                            'event_invitation' as invitation_type 
                        FROM event_invite_2
                        INNER JOIN event_2 on event_invite_2.event_id = event_2.id
                        INNER JOIN member_group ON event_2.group_id = member_group.id
                        INNER JOIN member ON event_2.host_member_id = member.id
                        LEFT JOIN member_profile ON member.id = member_profile.member_id
                        LEFT JOIN file_storage_engine on file_storage_engine.id = member_profile.profile_picture_storage_id
                        WHERE
                            event_invite_2.invite_member_id = %s AND event_2.event_status='Active'
                            AND
                            (
                                concat_ws(' ', member.first_name, member.last_name) iLIKE %s
                                OR concat('create year ', EXTRACT(YEAR FROM event_invite_2.create_date)) iLIKE %s
                                OR concat('create month ', EXTRACT(MONTH FROM event_invite_2.create_date)) iLIKE %s
                                OR concat('create month ', to_char(event_invite_2.create_date, 'month')) iLIKE %s
                                OR concat('create day ', EXTRACT(DAY FROM event_invite_2.create_date)) iLIKE %s
                                OR concat('create day ', to_char(event_invite_2.create_date, 'day')) iLIKE %s
                                OR concat('update year ', EXTRACT(YEAR FROM event_invite_2.update_date)) iLIKE %s
                                OR concat('update month ', EXTRACT(MONTH FROM event_invite_2.update_date)) iLIKE %s
                                OR concat('update month ', to_char(event_invite_2.update_date, 'month')) iLIKE %s
                                OR concat('update day ', EXTRACT(DAY FROM event_invite_2.update_date)) iLIKE %s
                                OR concat('update day ', to_char(event_invite_2.update_date, 'day')) iLIKE %s
                            )
                ) as results
                ORDER BY {sort_columns_string}
            """

            like_search_key = f"%{search_key}%"
            params = (member_id,) + (like_search_key,)*11
            params = params * 2

            countQuery = f"SELECT COUNT(*) FROM ({query}) src"

            cls.source.execute(countQuery, params)

            count = 0
            if cls.source.has_results():
                (count,) = cls.source.cursor.fetchone()

            if page_size and page_number >= 0:
                query += "LIMIT %s OFFSET %s"
                offset = 0
                if page_number > 0:
                    offset = page_number * page_size
                params = params + (page_size, offset)

            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                        id,
                        status,
                        event_name,
                        event_type,
                        first_name,
                        last_name,
                        email,
                        storage_engine_id,
                        create_user_id,
                        event_description,
                        group_id,
                        group_name,
                        group_info,
                        create_date,
                        update_date,
                        invitation_type,
                        row_id
                ) in cls.source.cursor:
                    invitation = {
                        "id": id,
                        "status": status,
                        "event_name": event_name,
                        "event_type": event_type,
                        "first_name": first_name,
                        "last_name": last_name,
                        "email": email,
                        "amera_avatar_url": amerize_url(storage_engine_id),
                        "create_user_id": create_user_id,
                        "event_description": event_description,
                        "group_id": group_id,
                        "group_name": group_name,
                        "group_info": group_info,
                        "create_date": create_date,
                        "update_date": update_date,
                        "invitation_type": invitation_type,
                        "row_id": row_id
                    }
                    invitations.append(invitation)

            return {
                'group_invitations' : invitations,
                'count': count
            }
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    @classmethod 
    def get_mail_activities_by_member_id(cls, member_id, is_history=False, search_key='', page_size=None, page_number=None, sort_params=''):
        try:
            activities = list()
            sort_columns_string = 'update_date DESC'
            mail_dict = {
                "id": "id",
                "status": "status",
                "name": "name",
                "event_type": "event_type",
                "first_name": "first_name",
                "last_name": "last_name",
                "email": "email",
                "storage_engine_id": "storage_engine_id",
                "create_user_id": "create_user_id",
                "description": "description",
                "group_id": "group_id",
                "group_name": "group_name",
                "group_info": "group_info",
                "create_date": "create_date",
                "update_date": "update_date"
            }

            if sort_params:
                sort_columns_string = cls.formatSortingParams(
                    sort_params, mail_dict) or sort_columns_string
            
            # unread = ""
            # mail_type = ""

            # if not is_history:
            #     unread = """ AND xref.read = false AND xref.deleted = false AND xref.owner_member_id <> %s"""
            #     param_mails = (member_id, member_id)

            # if not is_history:
            #     unread = " AND xref.status = 'unread'" #for media mails

            # if mail_type:
            #     mail_type = f" AND head.type = {mail_type}"

            empty_obj = '{}'

            query = f"""
                        SELECT id, subject, message, message_ts, message_to, message_cc, message_bcc, 
                            type, media_type, xref_id, status, create_date, update_date, mail_url, email, first_name, 
                            last_name, sender_id, read, new_mail, deleted, group_id, group_name, s3_avatar_url,
                            invitation_type, row_number() OVER (ORDER BY {sort_columns_string}) AS row_id
                        FROM (
                                SELECT
                                    head.id as id,
                                    head.subject as subject,
                                    body.message,
                                    head.message_ts::text as message_ts,
                                    head.message_to,
                                    head.message_cc,
                                    head.message_bcc,
                                    '' as type,
                                    '' as media_type,
                                    xref.id as xref_id,
                                    '' as status,
                                    head.message_ts as create_date,
                                    head.message_ts as update_date,
                                    '' as mail_url,
                                    member.email as email,
                                    member.first_name as first_name,
                                    member.last_name as last_name,
                                    member.id as sender_id,
                                    xref.read,
                                    xref.new_mail,
                                    xref.deleted,
                                    -1 as group_id,
                                    '' as group_name,
                                    file_path(file_storage_engine.storage_engine_id, '/member/file') as s3_avatar_url,
                                    'text_mail' as invitation_type 
                                FROM mail_header as head
                                INNER JOIN mail_xref xref on head.id = xref.mail_header_id
                                INNER JOIN mail_body body on head.id = body.mail_header_id
                                INNER JOIN member member on member.id = xref.owner_member_id
                                LEFT OUTER JOIN member_profile profile on member.id = profile.member_id
                                LEFT OUTER JOIN file_storage_engine on file_storage_engine.id = profile.profile_picture_storage_id
                                WHERE
                                    xref.member_id = %s
                                    AND
                                    (
                                        concat_ws(' ', member.first_name, member.last_name) iLIKE %s
                                        OR concat('create year ', EXTRACT(YEAR FROM head.message_ts)) iLIKE %s
                                        OR concat('create month ', EXTRACT(MONTH FROM head.message_ts)) iLIKE %s
                                        OR concat('create month ', to_char(head.message_ts, 'month')) iLIKE %s
                                        OR concat('create day ', EXTRACT(DAY FROM head.message_ts)) iLIKE %s
                                        OR concat('create day ', to_char(head.message_ts, 'day')) iLIKE %s
                                        OR concat('update year ', EXTRACT(YEAR FROM head.message_ts)) iLIKE %s
                                        OR concat('update month ', EXTRACT(MONTH FROM head.message_ts)) iLIKE %s
                                        OR concat('update month ', to_char(head.message_ts, 'month')) iLIKE %s
                                        OR concat('update day ', EXTRACT(DAY FROM head.message_ts)) iLIKE %s
                                        OR concat('update day ', to_char(head.message_ts, 'day')) iLIKE %s
                                    )
                            UNION
                                SELECT
                                    head.id as id,
                                    head.subject as subject,
                                    '' as message,
                                    '' as message_ts,
                                    '{empty_obj}'::jsonb as message_to,
                                    '{empty_obj}'::jsonb as message_cc,
                                    '{empty_obj}'::jsonb as message_bcc,
                                    head.type::text as type,
                                    head.media_type::text as media_type,
                                    xref.id as xref_id,
                                    xref.status::text AS status,
                                    head.create_date as create_date,
                                    head.update_date as update_date,
                                    mail_storage.storage_engine_id as mail_url,
                                    member.email as email,
                                    member.first_name as first_name,
                                    member.last_name as last_name,
                                    member.id as sender_id,
                                    false as read,
                                    false as new_mail,
                                    false as deleted,
                                    member_group.id as group_id,
                                    member_group.group_name,
                                    file_storage_engine.storage_engine_id as s3_avatar_url,
                                    'media_mail' as invitation_type
                                FROM video_mail as head
                                INNER JOIN  file_storage_engine mail_storage on mail_storage.id = head.video_storage_id
                                INNER JOIN video_mail_xref xref on head.id = xref.video_mail_id
                                INNER JOIN member member on member.id = head.message_from
                                LEFT OUTER JOIN member_profile profile on member.id = profile.member_id
                                LEFT OUTER JOIN file_storage_engine on file_storage_engine.id = profile.profile_picture_storage_id
                                LEFT OUTER JOIN member_group on member_group.id = head.group_id
                                WHERE
                                    xref.member_id = %s
                                    AND
                                    (
                                        concat_ws(' ', member.first_name, member.last_name) iLIKE %s
                                        OR concat('create year ', EXTRACT(YEAR FROM head.create_date)) iLIKE %s
                                        OR concat('create month ', EXTRACT(MONTH FROM head.create_date)) iLIKE %s
                                        OR concat('create month ', to_char(head.create_date, 'month')) iLIKE %s
                                        OR concat('create day ', EXTRACT(DAY FROM head.create_date)) iLIKE %s
                                        OR concat('create day ', to_char(head.create_date, 'day')) iLIKE %s
                                        OR concat('update year ', EXTRACT(YEAR FROM head.update_date)) iLIKE %s
                                        OR concat('update month ', EXTRACT(MONTH FROM head.update_date)) iLIKE %s
                                        OR concat('update month ', to_char(head.update_date, 'month')) iLIKE %s
                                        OR concat('update day ', EXTRACT(DAY FROM head.update_date)) iLIKE %s
                                        OR concat('update day ', to_char(head.update_date, 'day')) iLIKE %s
                                    )
                        ) as results
                        ORDER BY {sort_columns_string}
                    """

            like_search_key = f"%{search_key}%"
            params = (member_id,) + (like_search_key,)*11
            params = params * 2

            countQuery = f"SELECT COUNT(*) FROM ({query}) src"

            cls.source.execute(countQuery, params)

            count = 0
            if cls.source.has_results():
                (count,) = cls.source.cursor.fetchone()

            if page_size and page_number >= 0:
                query += "LIMIT %s OFFSET %s"
                offset = 0
                if page_number > 0:
                    offset = page_number * page_size
                params = params + (page_size, offset)

            cls.source.execute(query, params)
            if cls.source.has_results():
                for (
                        id,
                        subject,
                        message,
                        message_ts,
                        message_to,
                        message_cc,
                        message_bcc,
                        type,
                        media_type,
                        xref_id,
                        status,
                        create_date,
                        update_date,
                        mail_url,
                        email,
                        first_name,
                        last_name,
                        sender_id,
                        read,
                        new_mail,
                        deleted,
                        group_id,
                        group_name,
                        s3_avatar_url,
                        invitation_type,
                        row_id
                ) in cls.source.cursor: 
                    activity = { 
                        "id"             : id,
                        "subject"        : subject,
                        "message"        : message,
                        "message_ts"     : message_ts,
                        "message_to"     : message_to,
                        "message_cc"     : message_cc,
                        "message_bcc"    : message_bcc,
                        "type"           : type,
                        "media_type"     : media_type,
                        "xref_id"        : xref_id,
                        "status"         : status,
                        "create_date"    : create_date,
                        "update_date"    : update_date,
                        "mail_url"       : mail_url,
                        "email"          : email,
                        "first_name"     : first_name,
                        "last_name"      : last_name,
                        "sender_id"      : sender_id,
                        "read"           : read,
                        "new_mail"       : new_mail,
                        "deleted"        : deleted,
                        "group_id"       : group_id,
                        "group_name"     : group_name,
                        "s3_avatar_url"  : s3_avatar_url,
                        "invitation_type": invitation_type,
                        "row_id"         : row_id
                    } 
                    activities.append(activity)

            return {
                'activities' : activities,
                'count': count
            }
        except Exception as e:
            logger.error(e, exc_info=True)
            return None