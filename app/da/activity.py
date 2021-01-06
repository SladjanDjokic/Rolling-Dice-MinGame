import json

from app.util.db import source
import logging

logger = logging.getLogger(__name__)
from app.util.filestorage import amerize_url


class ActivityDA(object):
    source = source

    @classmethod
    def insert_activity(cls, event_key="", headers={}, req_params={},
                        req_url_params={}, req_data={}, resp_data={},
                        http_status="", session_key="", session_data={},
                        member_id="", event_type="activity", status="",
                        create_date="", commit=True):

        insert_activity_q = (
            """
            INSERT INTO activity_trace
                (event_key, headers, request_params, request_url_params,
                request_data, response, http_status, session_key, 
                session_data, member_id, event_type, status, create_date)
                Values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
        )
        params = (
                    event_key, headers, req_params, req_url_params, req_data,
                    resp_data, http_status, session_key, session_data,
                    member_id, event_type, status, create_date
                )
        try:
            cls.source.execute(insert_activity_q, params)
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
    def get_recent_acticities(cls, member_id, member_email):
        mails = list()
        invitations = list()
        try:
            query_mails = """
                SELECT 
                    activity_trace.id,
                    activity_trace.event_key,
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
                    file_storage_engine.storage_engine_id as s3_avatar_url
                FROM activity_trace
                LEFT OUTER JOIN member ON member.id = activity_trace.member_id
                LEFT OUTER JOIN job_title ON job_title.id = member.job_title_id
                LEFT OUTER JOIN member_profile ON activity_trace.member_id = member_profile.member_id
                LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                WHERE
                    activity_trace.event_type='activity' 
                    AND 
                    (json_typeof(activity_trace.request_data)::text <> 'null' AND json_typeof(activity_trace.response)::text <> 'null')
                    AND
                    activity_trace.response::jsonb ? 'fails'
                    AND
                    EXISTS (
                        SELECT FROM json_array_elements(activity_trace.request_data->'receivers'->'amera') pil
                            WHERE (pil)::text = %s
                    )
                    ORDER BY activity_trace.create_date DESC
                    LIMIT 10
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
                    file_storage_engine.storage_engine_id as s3_avatar_url,
                    contact.status AS contact_requested_status,
                    member_group_membership.status AS group_membership_status
                FROM activity_trace
                LEFT OUTER JOIN member AS member_requester ON member_requester.id = activity_trace.member_id
                LEFT OUTER JOIN member AS member_requested ON member_requested.id = %s
                LEFT OUTER JOIN job_title ON job_title.id = member_requester.job_title_id
                LEFT OUTER JOIN member_profile ON activity_trace.member_id = member_profile.member_id
                LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                LEFT OUTER JOIN contact ON contact.contact_member_id = activity_trace.member_id AND contact.member_id = member_requested.id
                LEFT OUTER JOIN member_group_membership ON member_group_membership.group_id = (activity_trace.request_params->>'groupId')::INT AND member_group_membership.member_id = member_requested.id
                WHERE
                    activity_trace.event_type='activity'
                    AND
                    (activity_trace.request_params::text <> '{}'::text AND activity_trace.response::text <> 'null')
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
                            member_group_membership.status = 'invited'
                        OR
                        (
                            request_params->>'type' = 'create-group'
                            AND
                            (request_params->>'members')::jsonb @> to_char(member_requested.id, '999')::jsonb
                        )
                    )
                    ORDER BY activity_trace.create_date DESC
                    LIMIT 10
                """
            param_mails = (str(member_id), )
            param_invitations = (str(member_id),)
            
            cls.source.execute(query_mails, param_mails)
            if cls.source.has_results():
                for (
                        id,
                        event_key,
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
                        s3_avatar_url
                ) in cls.source.cursor:
                    mail = {
                        "id": id,
                        "event_key": event_key,
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
                        "amera_avatar_url": amerize_url(s3_avatar_url)
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
                        group_membership_status
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
                        "amera_avatar_url": amerize_url(s3_avatar_url),
                        "contact_requested_status": contact_requested_status,
                        "group_membership_status": group_membership_status
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