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
    def get_activity_invitations(cls, member_id, member_email):
        invitations = list()
        try:
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

            param_invitations = (str(member_id),)

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

            return invitations

        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    @classmethod
    def get_activity_message(cls, member_id, member_email):
        mails = list()

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
                    contact_video_mail.read as vmail_read
                FROM activity_trace
                LEFT OUTER JOIN member ON member.id = activity_trace.member_id
                LEFT OUTER JOIN job_title ON job_title.id = member.job_title_id
                LEFT OUTER JOIN member_profile ON activity_trace.member_id = member_profile.member_id
                LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                LEFT OUTER JOIN mail_header ON mail_header.id = (activity_trace.request_data->>'mail_id')::int
                LEFT OUTER JOIN mail_xref xref ON mail_header.id = xref.mail_header_id AND xref.member_id = %s
                LEFT OUTER JOIN contact_video_mail ON contact_video_mail.id = (activity_trace.response->>'mail_id')::int
                WHERE
                    (
                        activity_trace.response ? 'fails'
                        AND
                        activity_trace.request_data->'receivers'->'amera' @> %s
                    ) OR
                    (
                        activity_trace.status = 'ended'
                        AND
                        (activity_trace.request_url_params->>'receiver')::int = %s
                    )
                ORDER BY activity_trace.create_date DESC
                LIMIT 10
            """
            param_mails = (member_id, str(member_id), member_id)


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
                        vmail_read
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
                        "vmail_read": vmail_read
                    }
                    mails.append(mail)

            return mails
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
