import datetime
import json
import logging

from falcon import HTTPInternalServerError

from app.da.file_sharing import FileStorageDA
from app.da.mail_folder import MailFolderDA
from app.da.member import MemberContactDA
from app.exceptions.data import DataMissingError, HTTPBadRequest, HTTPNotFound
from app.util.db import source
from app.util.filestorage import amerize_url
from app.util.security import SECURITY_EXCHANGE_OPTIONS
from app.util.validators import receiver_dict_validator

logger = logging.getLogger(__name__)


class BaseDA(object):
    source = source


class BaseMailDA(BaseDA):
    message_locked = True
    user_folders = False
    excluded_folders = ['TRASH', 'ARCHIVE']

    @classmethod
    def folder_query(cls, member_id):
        folder_id = MailFolderDA.get_folder_id_for_member(str(cls.folder_name).upper(), member_id)
        return (f"""AND mfx.mail_folder_id = {folder_id}
                AND xref.deleted = FALSE
                AND xref.archived = FALSE
                """,
                """INNER JOIN mail_folder_xref mfx on xref.id = mfx.mail_xref_id""")

    @property
    def folder_name(self):
        raise NotImplemented

    @classmethod
    def list_after_update_query(cls, member_id):
        folder_query, folder_join = cls.folder_query(member_id)
        return f"""
            UPDATE mail_xref
            SET new_mail = FALSE
            FROM mail_xref xref
            {folder_join}
            WHERE (
                mail_xref.mail_header_id IN %s
                AND mail_xref.owner_member_id = %s
                {folder_query}
                AND xref.deleted = FALSE
            );
        """

    @classmethod
    def list_get_query(cls, start, search_query, order_query, has_folder_filter, has_member_filter, member_id):
        folder_query, folder_join = cls.folder_query(member_id)
        user_folders_query = ""

        if cls.user_folders:
            user_folders_query = f"""
                AND (xref.recent_mail_folder_id {('=' if has_folder_filter else '>')
            if has_folder_filter is not None else 'IS'} %s
                    {'OR xref.recent_mail_folder_id IS NULL' if not has_folder_filter and has_folder_filter is not None
            else ''}
                )
            """
        if has_member_filter and cls.folder_name != "Sent":
            user_folders_query += """
                 AND (
                    message_to->'amera' @> to_char(%s, '999')::jsonb
                    OR 
                    message_cc->'amera' @> to_char(%s, '999')::jsonb
                    OR xref.owner_member_id = %s
                )
            """
        if has_member_filter and cls.folder_name == "Sent":
            user_folders_query += """
                AND (
                    message_to->'amera' @> to_char(%s, '999')::jsonb
                    OR
                    message_cc->'amera' @> to_char(%s, '999')::jsonb
                    OR
                    message_bcc->'amera' @> to_char(%s, '999')::jsonb
                )
            """
        return f"""
            SELECT
                head.id,
                head.subject,
                body.message,
                head.message_ts,
                head.number_attachments,
                m.id,
                m.email,
                m.first_name,
                m.last_name,
                xref.read,
                xref.new_mail,
                prof_image_engine.storage_engine_id,
                starred,
                COUNT(head.id) OVER() AS full_count,
                head.message_to,
                head.message_cc,
                head.message_bcc,
                xref.recent_mail_folder_id
            FROM mail_header as head
            INNER JOIN mail_xref xref on head.id = xref.mail_header_id
            INNER JOIN mail_body body on head.id = body.mail_header_id
            INNER JOIN member m on m.id = xref.owner_member_id
            LEFT OUTER JOIN member_profile profile on m.id = profile.member_id
            LEFT OUTER JOIN file_storage_engine prof_image_engine on
                                                            prof_image_engine.id = profile.profile_picture_storage_id
            {folder_join}
            WHERE (
                {'head.id < %s' if start > 0 else 'head.id > %s'}
                AND xref.member_id = %s
                AND head.message_locked = %s
                {user_folders_query}
                {folder_query}
                AND (
                    {search_query}
                )
            )
            {order_query}
            LIMIT %s;
        """

    @classmethod
    def detail_get_query(cls, member_id):
        folder_query, folder_join = cls.folder_query(member_id)
        return f"""
            SELECT
                head.subject,
                body.message,
                head.message_ts,
                head.number_attachments,
                m.id,
                m.email,
                m.first_name,
                m.last_name,
                prof_image_engine.storage_engine_id,
                folder.name,
                folder.id,
                xref.read,
                xref.replied_id,
                xref.replied_ts,
                CASE
                    WHEN xref.replied_id IS NOT NULL THEN
                        reply.subject
                    ELSE ''
                END,
                CASE
                    WHEN xref.replied_id IS NOT NULL THEN
                        reply_body.message
                    ELSE ''
                END,
                starred,
                head.message_to,
                head.message_cc,
                head.message_bcc,
                xref.recent_mail_folder_id
            FROM mail_header as head
            INNER JOIN mail_xref xref on head.id = xref.mail_header_id
            INNER JOIN mail_body body on head.id = body.mail_header_id
            INNER JOIN member m on m.id = xref.owner_member_id
            LEFT OUTER JOIN member_profile profile on m.id = profile.member_id
            LEFT OUTER JOIN file_storage_engine prof_image_engine on
                                                            prof_image_engine.id = profile.profile_picture_storage_id
            INNER JOIN mail_folder_xref mfx on xref.id = mfx.mail_xref_id
            INNER JOIN mail_folder folder on mfx.mail_folder_id = folder.id
            INNER JOIN mail_header reply on (
                CASE
                    WHEN xref.replied_id IS NOT NULL THEN
                        reply.id = xref.replied_id
                    ELSE TRUE
                END
            )
            INNER JOIN mail_body reply_body on (
                CASE
                    WHEN xref.replied_id IS NOT NULL THEN
                        reply_body.mail_header_id = xref.replied_id
                    ELSE TRUE
                END
            )
            WHERE (
                head.id = %s
                AND xref.member_id = %s
                AND head.message_locked = %s
                {folder_query}
            )
            LIMIT 1;
        """

    @classmethod
    def get_reply_chain(cls, member_id, thread_id, start):
        folder_query, folder_join = cls.folder_query(member_id)
        header_query = f"""
            SELECT
                head.id,
                head.subject,
                body.message,
                head.message_ts,
                head.number_attachments,
                m.id,
                m.email,
                m.first_name,
                m.last_name,
                prof_image_engine.storage_engine_id,
                folder.name,
                folder.id,
                xref.read,
                xref.replied_id,
                xref.replied_ts,
                CASE
                    WHEN xref.replied_id IS NOT NULL THEN
                        reply.subject
                    ELSE ''
                END,
                CASE
                    WHEN xref.replied_id IS NOT NULL THEN
                        reply_body.message
                    ELSE ''
                END,
                starred,
                head.message_to,
                head.message_cc,
                head.message_bcc,
                xref.recent_mail_folder_id
            FROM mail_header as head
            INNER JOIN mail_xref xref on head.id = xref.mail_header_id
            INNER JOIN mail_body body on head.id = body.mail_header_id
            INNER JOIN member m on m.id = xref.owner_member_id
            LEFT OUTER JOIN member_profile profile on m.id = profile.member_id
            LEFT OUTER JOIN file_storage_engine prof_image_engine on
                                                            prof_image_engine.id = profile.profile_picture_storage_id
            INNER JOIN mail_folder_xref mfx on xref.id = mfx.mail_xref_id
            INNER JOIN mail_folder folder on mfx.mail_folder_id = folder.id
            INNER JOIN mail_header reply on (
                CASE
                    WHEN xref.replied_id IS NOT NULL THEN
                        reply.id = xref.replied_id
                    ELSE TRUE
                END
            )
            INNER JOIN mail_body reply_body on (
                CASE
                    WHEN xref.replied_id IS NOT NULL THEN
                        reply_body.mail_header_id = xref.replied_id
                    ELSE TRUE
                END
            )
            WHERE (
                xref.mail_thread_id = %s
                AND xref.id > %s
                AND head.message_locked = %s
                {folder_query}
            )
            LIMIT 20;
        """
        attach_query = """
            SELECT
                attach.filename,
                attach.filetype,
                attach.filesize,
                attach_storage.storage_engine_id
            FROM mail_attachment as attach
            INNER JOIN file_storage_engine attach_storage on attach.file_id = attach_storage.id
            WHERE (
                attach.mail_header_id = %s
            );
        """
        cls.source.execute(header_query, (thread_id, start, cls.message_locked))
        return_data = []
        if cls.source.has_results():
            for (
                mail_id,
                subject,
                body,
                time,
                attachments_count,
                sender_member_id,
                sender_mail,
                first_name,
                last_name,
                prof_id,
                folder_name,
                folder_id,
                read,
                reply_id,
                reply_time,
                reply_subject,
                reply_body,
                is_starred,
                receivers,
                cc,
                bcc,
                folder_id
            ) in cls.source.cursor.fetchall():
                if receivers and not type(receivers) == dict:
                    try:
                        receivers = json.loads(str(receivers))
                    except json.decoder.JSONDecodeError:
                        receivers = receivers
                if bcc and not type(bcc) == dict:
                    try:
                        bcc = json.loads(str(bcc))
                    except json.decoder.JSONDecodeError:
                        bcc = bcc
                if cc and not type(cc) == dict:
                    try:
                        cc = json.loads(str(cc))
                    except json.decoder.JSONDecodeError:
                        cc = cc
                confirmed_bcc = None
                if (sender_member_id and sender_member_id == member_id) or \
                        (receivers and "amera" in receivers and member_id in receivers["amera"]):
                    confirmed_bcc = bcc
                get_members_id = [x for x in receivers["amera"]] if receivers and "amera" in receivers else []
                get_members_id += [x for x in cc["amera"]] if cc and "amera" in cc else []
                get_members_id += [x for x in confirmed_bcc["amera"]] \
                    if confirmed_bcc and "amera" in confirmed_bcc else []
                member_infos = cls.get_members_info(get_members_id)
                data = {
                    "subject": subject,
                    "body": body,
                    "time": time,
                    "attachments_count": attachments_count,
                    "sender_member_id": sender_member_id,
                    "sender_mail": sender_mail,
                    "first_name": first_name,
                    "last_name": last_name,
                    "profile_url": amerize_url(prof_id),
                    "receivers": receivers,
                    "cc": cc,
                    "bcc": confirmed_bcc,
                    "reply": {
                        "id": reply_id,
                        "subject": reply_subject,
                        "body": reply_body,
                        "time": reply_time
                    },
                    "attachments": [],
                    "is_stared": is_starred,
                    "member_details": member_infos,
                    "folder_id": folder_id
                }

                cls.source.execute(attach_query, (mail_id,))
                if cls.source.has_results():
                    for (
                            filename,
                            filetype,
                            filesize,
                            attach_engine_id
                    ) in cls.source.cursor.fetchall():
                        data["attachments"].append({
                            "name": filename,
                            "type": filetype,
                            "size": filesize,
                            "url": amerize_url(attach_engine_id),
                        })
                elif mail_id:
                    pass
                cls.source.commit()
                return_data.append(data)
        return return_data

    @classmethod
    def get_members_info(cls, member_ids=()):
        get_member_info_query = ("""
            SELECT
                member.id as id,
                member.first_name as first_name,
                member.middle_name as middle_name,
                member.last_name as last_name,
                member.email as email,
                member.company_name as company,
                file_storage_engine.storage_engine_id as s3_avatar_url,
                member_profile.biography as biography
            FROM member
            LEFT OUTER JOIN member_profile ON member.id = member_profile.member_id
            LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
            WHERE member.id IN %s
            """)
        get_member_info_params = (tuple(member_ids),)
        cls.source.execute(get_member_info_query, get_member_info_params)
        return_data = {}
        if cls.source.has_results():
            for (
                    member_id,
                    first_name,
                    middle_name,
                    last_name,
                    email,
                    company,
                    s3_avatar_url,
                    biography
            ) in cls.source.cursor:
                return_data[member_id] = {
                    "member_id": member_id,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "email": email,
                    "company_name": company,
                    "amera_avatar_url": amerize_url(s3_avatar_url),
                    "biography": biography
                }
        return return_data

    @classmethod
    def list_folder(cls, member_id, start=-1, size=20, search=None, sort=None, order=1, filter_list=None):
        if filter_list is None:
            filter_list = {}
        search_query = "TRUE"
        search_params = []
        order_query = ""
        if search:
            search_query = """
                    (
                        UPPER(m.last_name) LIKE UPPER(%s)
                        OR UPPER(m.first_name) LIKE UPPER(%s)
                        OR UPPER(m.email) LIKE UPPER(%s)
                        OR UPPER(head.subject) LIKE UPPER(%s)
                        OR UPPER(body.message) LIKE UPPER(%s)
                    )
            """
            search_params = [search, search, search, search, search]
        if sort and not sort == 'read':
            if sort == 'rec_date':
                sort_param = 'head.message_ts'
            else:
                raise HTTPBadRequest("Sort type is not supported")
            order_query = f"""
                ORDER BY {sort_param}{' DESC' if order == -1 else ''}
            """

        if sort and sort == 'read':
            search_query += f"""
                AND xref.read = {'TRUE' if order == 1 else 'FALSE'}
            """
        header_query = cls.list_get_query(start, search_query, order_query,
                                          filter_list["folder"] >= 0 if bool(filter_list and ("folder" in filter_list))
                                          else None,
                                          bool(filter_list and ("member_id" in filter_list)),
                                          member_id)
        header_update = cls.list_after_update_query(member_id)
        folder_filter_data = []
        if cls.user_folders:
            folder_filter_data.append(filter_list["folder"] if filter_list and "folder" in filter_list else None)
        if filter_list and ("member_id" in filter_list):
            folder_filter_data.append(filter_list["member_id"])
            folder_filter_data.append(filter_list["member_id"])
            folder_filter_data.append(filter_list["member_id"])
        # # Get mail header
        cls.source.execute(header_query, (start, member_id, cls.message_locked, *folder_filter_data, *search_params,
                                          size))
        if cls.source.has_results():
            data = []
            new_mails = []
            all_count = 0
            get_members_id = []
            for (
                    header_id,
                    subject,
                    body,
                    time,
                    attachments_count,
                    sender_id,
                    sender_mail,
                    first_name,
                    last_name,
                    read,
                    new_mail,
                    prof_id,
                    is_star,
                    full_count,
                    receivers,
                    cc,
                    bcc,
                    folder_id
            ) in cls.source.cursor.fetchall():
                all_count = full_count
                if receivers and not type(receivers) == dict:
                    try:
                        receivers = json.loads(str(receivers))
                    except json.decoder.JSONDecodeError:
                        receivers = receivers
                if bcc and not type(bcc) == dict:
                    try:
                        bcc = json.loads(str(bcc))
                    except json.decoder.JSONDecodeError:
                        bcc = bcc
                if cc and not type(cc) == dict:
                    try:
                        cc = json.loads(str(cc))
                    except json.decoder.JSONDecodeError:
                        cc = cc
                confirmed_bcc = None
                if (sender_id and sender_id == member_id) or \
                        (receivers and "amera" in receivers and member_id in receivers["amera"]):
                    confirmed_bcc = bcc
                get_members_id += [x for x in receivers["amera"]] if receivers and "amera" in receivers else []
                get_members_id += [x for x in cc["amera"]] if cc and "amera" in cc else []
                get_members_id += [x for x in confirmed_bcc["amera"]] \
                    if confirmed_bcc and "amera" in confirmed_bcc else []
                data.append({
                    "mail_id": header_id,
                    "subject": subject,
                    "body": body,
                    "time": time,
                    "attachments_count": attachments_count,
                    "sender_mail": sender_mail,
                    "first_name": first_name,
                    "last_name": last_name,
                    "read": read,
                    "receivers": receivers,
                    "cc": cc,
                    "bcc": confirmed_bcc,
                    "new_mail": new_mail,
                    "profile_url": amerize_url(prof_id),
                    "is_stared": is_star,
                    "folder_id": folder_id
                })
                if new_mail:
                    new_mails.append(header_id)
            member_infos = cls.get_members_info(tuple(set(get_members_id)))
            for index in range(len(data)):
                data[index]["member_details"] = member_infos
            if len(new_mails) > 0:
                cls.source.execute(header_update, (tuple(new_mails), member_id))
                cls.source.commit()
            return data, all_count
        return [], 0

    @classmethod
    def get_mail_detail(cls, mail_id, member_id):
        folder_query, folder_join = cls.folder_query(member_id)
        header_query = cls.detail_get_query(member_id)
        attach_query = """
            SELECT
                attach.filename,
                attach.filetype,
                attach.filesize,
                attach_storage.storage_engine_id
            FROM mail_attachment as attach
            INNER JOIN file_storage_engine attach_storage on attach.file_id = attach_storage.id
            WHERE (
                attach.mail_header_id = %s
            );
        """
        header_update = f"""
            UPDATE mail_xref
            SET new_mail = FALSE, read = TRUE, read_ts=CURRENT_TIMESTAMP
            FROM mail_xref xref
            {folder_join}
            WHERE (
                mail_xref.mail_header_id = %s
                AND mail_xref.member_id = %s
                {folder_query}
                AND mail_xref.deleted = FALSE
            );
        """

        cls.source.execute(header_query, (mail_id, member_id, cls.message_locked))
        if cls.source.has_results():
            (
                subject,
                body,
                time,
                attachments_count,
                sender_member_id,
                sender_mail,
                first_name,
                last_name,
                prof_id,
                folder_name,
                folder_id,
                read,
                reply_id,
                reply_time,
                reply_subject,
                reply_body,
                is_starred,
                receivers,
                cc,
                bcc,
                folder_id
            ) = cls.source.cursor.fetchone()
            if receivers and not type(receivers) == dict:
                try:
                    receivers = json.loads(str(receivers))
                except json.decoder.JSONDecodeError:
                    receivers = receivers
            if bcc and not type(bcc) == dict:
                try:
                    bcc = json.loads(str(bcc))
                except json.decoder.JSONDecodeError:
                    bcc = bcc
            if cc and not type(cc) == dict:
                try:
                    cc = json.loads(str(cc))
                except json.decoder.JSONDecodeError:
                    cc = cc
            confirmed_bcc = None
            if (sender_member_id and sender_member_id == member_id) or \
                    (receivers and "amera" in receivers and member_id in receivers["amera"]):
                confirmed_bcc = bcc
            get_members_id = [x for x in receivers["amera"]] if receivers and "amera" in receivers else []
            get_members_id += [x for x in cc["amera"]] if cc and "amera" in cc else []
            get_members_id += [x for x in confirmed_bcc["amera"]] \
                if confirmed_bcc and "amera" in confirmed_bcc else []
            member_infos = cls.get_members_info(get_members_id)
            data = {
                "subject": subject,
                "body": body,
                "time": time,
                "attachments_count": attachments_count,
                "sender_member_id": sender_member_id,
                "sender_mail": sender_mail,
                "first_name": first_name,
                "last_name": last_name,
                "profile_url": amerize_url(prof_id),
                "receivers": receivers,
                "cc": cc,
                "bcc": confirmed_bcc,
                "reply": {
                    "id": reply_id,
                    "subject": reply_subject,
                    "body": reply_body,
                    "time": reply_time
                },
                "attachments": [],
                "is_stared": is_starred,
                "member_details": member_infos,
                "folder_id": folder_id
            }

            cls.source.execute(attach_query, (mail_id,))
            if cls.source.has_results():
                for (
                        filename,
                        filetype,
                        filesize,
                        attach_engine_id
                ) in cls.source.cursor.fetchall():
                    data["attachments"].append({
                        "name": filename,
                        "type": filetype,
                        "size": filesize,
                        "url": amerize_url(attach_engine_id),
                    })
            elif mail_id:
                pass
            if not read:
                cls.source.execute(header_update, (mail_id, member_id))
            cls.source.commit()
            return data
        return {}


    @classmethod
    def get_selectable_contacts(cls, member_id, sort_params, filter_params, search_key='', page_size=None,
                                page_number=None):
        sort_columns_string = 'first_name ASC'
        contact_dict = {
            'id': 'contact.id',
            'contact_member_id': 'contact.contact_member_id',
            'first_name': 'contact.first_name',
            'middle_name': 'member.middle_name',
            'last_name': 'contact.last_name',
            'biography': 'member_profile.biography',
            'cell_phone': 'contact.cell_phone',
            'office_phone': 'contact.office_phone',
            'home_phone': 'contact.home_phone',
            'email': 'contact.email',
            'personal_email': 'contact.personal_email',
            'company': 'member.company_name',
            'title': 'job_title.name',
            'country_code_id': 'member_location.country_code_id',
            'company_name': 'member.company_name',
            'company_phone': 'contact.company_phone',
            'company_web_site': 'contact.company_web_site',
            'company_email': 'contact.company_email',
            'company_bio': 'contact.company_bio',
            'role': 'role.name',
            'role_id': 'role.id',
            'create_date': 'contact.create_date',
            'update_date': 'contact.update_date',
            'status': 'contact.status',
            'online_status': 'member_session.status'
        }

        if sort_params:
            sort_columns_string = MemberContactDA.formatSortingParams(
                sort_params, contact_dict) or sort_columns_string

        (filter_conditions_query, filter_conditions_params) = MemberContactDA.formatFilterConditions(
            filter_params, contact_dict)
        get_contacts_params = (member_id, ) + filter_conditions_params
        contacts = list()
        get_contacts_query = (f"""
            SELECT contact.id as id,
                contact.contact_member_id as contact_member_id,
                contact.first_name as first_name,
                member.middle_name as middle_name,
                contact.last_name as last_name,
                member_profile.biography as biography,
                contact.cell_phone as cell_phone,
                contact.office_phone as office_phone,
                contact.home_phone as home_phone,
                contact.email as email,
                contact.personal_email as personal_email,
                member.company_name as company,
                job_title.name as title,
                contact.company_name as company_name,
                contact.company_phone as company_phone,
                contact.company_web_site as company_web_site,
                contact.company_email as company_email,
                contact.company_bio as company_bio,
                role.name as role,
                role.id as role_id,
                contact.create_date as create_date,
                contact.update_date as update_date,
                COALESCE(json_agg(DISTINCT member_location.*) FILTER (WHERE member_location.id IS NOT NULL), '[]') AS location_information,
                COALESCE(json_agg(DISTINCT member_contact_2.*) FILTER (WHERE member_contact_2.id IS NOT NULL), '[]') AS contact_information,
                COALESCE(json_agg(DISTINCT country_code.*) FILTER (WHERE country_code.id IS NOT NULL), '[]') AS country_code,
                COALESCE(json_agg(DISTINCT member_achievement.*) FILTER (WHERE member_achievement.id IS NOT NULL), '[]') AS achievement_information,
                file_storage_engine.storage_engine_id as s3_avatar_url,
                contact.security_exchange_option,
                contact.status,
                CASE
                    WHEN member_session.status IS NOT NULL
                    THEN member_session.status
                    ELSE 'inactive'
                END as online_status
            FROM contact
                LEFT JOIN member ON member.id = contact.contact_member_id
                LEFT OUTER JOIN role ON contact.role_id = role.id
                LEFT OUTER JOIN member_location ON member_location.member_id = contact.contact_member_id
                LEFT OUTER JOIN member_contact ON member_contact.member_id = contact.contact_member_id
                LEFT OUTER JOIN member_contact_2 ON member_contact_2.member_id = contact.contact_member_id
                LEFT OUTER JOIN country_code ON member_contact_2.device_country = country_code.id
                LEFT OUTER JOIN job_title ON member.job_title_id = job_title.id
                LEFT OUTER JOIN member_profile ON contact.contact_member_id = member_profile.member_id
                LEFT OUTER JOIN member_achievement ON member_achievement.member_id = member.id
                LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
                LEFT OUTER JOIN member_session ON
                    contact.contact_member_id = member_session.member_id AND
                    member_session.status IN ('online', 'disconnected') AND
                    member_session.expiration_date >= current_timestamp
                INNER JOIN mail_xref mx on mx.member_id = contact.member_id
                INNER JOIN mail_header mh on mx.mail_header_id = mh.id
                INNER JOIN mail_folder_xref on mx.id = mail_folder_xref.mail_xref_id
                INNER JOIN mail_folder mf on (
                        mail_folder_xref.mail_folder_id = mf.id
                        AND mf.name = '{str(cls.folder_name).upper()}'
                    )
            WHERE
                contact.member_id = %s {filter_conditions_query}
                AND
                (
                    (
                        mf.name = 'SENT'
                        AND mh.member_id = contact.member_id
                        AND
                        (
                            mh.message_to->'amera' @> to_char(contact.contact_member_id, '999')::jsonb
                            OR
                            mh.message_cc->'amera' @> to_char(contact.contact_member_id, '999')::jsonb
                            OR
                            mh.message_bcc->'amera' @> to_char(contact.contact_member_id, '999')::jsonb
                        )
                    )
                    OR
                    (
                        mf.name != 'SENT'
                        AND
                        (
                            mh.message_to->'amera' @> to_char(contact.contact_member_id, '999')::jsonb
                            OR
                            mh.message_cc->'amera' @> to_char(contact.contact_member_id, '999')::jsonb
                            OR mh.member_id = contact.contact_member_id
                        )
                    )
                )
                AND
                (
                    concat(contact.first_name, member.middle_name, contact.last_name) ILIKE %s
                    OR contact.email ILIKE %s
                    OR member_profile.biography LIKE %s
                    OR contact.cell_phone LIKE %s
                    OR contact.office_phone LIKE %s
                    OR contact.home_phone LIKE %s
                    OR contact.personal_email LIKE %s
                    OR member.company_name LIKE %s
                    OR job_title.name LIKE %s
                    OR cast(member_location.country_code_id as varchar) LIKE %s
                    OR member.company_name LIKE %s
                    OR contact.company_phone LIKE %s
                    OR contact.company_web_site LIKE %s
                    OR contact.company_email LIKE %s
                    OR contact.company_bio LIKE %s
                    OR role.name LIKE %s
                )
            GROUP BY
                contact.id,
                contact.contact_member_id,
                contact.first_name,
                member.middle_name,
                contact.last_name,
                member_profile.biography,
                contact.cell_phone,
                contact.office_phone,
                contact.home_phone,
                contact.email,
                contact.personal_email,
                member.company_name,
                job_title.name,
                contact.company_name,
                contact.company_phone,
                contact.company_web_site,
                contact.company_email,
                contact.company_bio,
                role.name,
                role.id,
                contact.create_date,
                contact.update_date,
                file_storage_engine.storage_engine_id,
                contact.status,
                member_session.status
            ORDER BY {sort_columns_string}
            """)

        like_search_key = """%{}%""".format(search_key)
        get_contacts_params = get_contacts_params + \
            tuple(16 * [like_search_key])

        countQuery = (f"""
            SELECT COUNT(*)
                FROM
                    (
                        {get_contacts_query}
                    ) src;
            """)

        count = 0
        cls.source.execute(countQuery, get_contacts_params)
        if cls.source.has_results():
            (count,) = cls.source.cursor.fetchone()

        if page_size and page_number >= 0:
            get_contacts_query += """LIMIT %s OFFSET %s"""
            offset = 0
            if page_number > 0:
                offset = page_number * page_size
            get_contacts_params = get_contacts_params + (page_size, offset)

        cls.source.execute(get_contacts_query, get_contacts_params)
        if cls.source.has_results():
            for (
                    id,
                    contact_member_id,
                    first_name,
                    middle_name,
                    last_name,
                    biography,
                    cell_phone,
                    office_phone,
                    home_phone,
                    email,
                    personal_email,
                    company,
                    title,
                    company_name,
                    company_phone,
                    company_web_site,
                    company_email,
                    company_bio,
                    role,
                    role_id,
                    create_date,
                    update_date,
                    location_information,
                    contact_information,
                    country_code,
                    achievement_information,
                    s3_avatar_url,
                    security_exchange_option,
                    status,
                    online_status
            ) in cls.source.cursor:
                contact = {
                    "id": id,
                    "contact_member_id": contact_member_id,
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "member_name": f'{first_name} {last_name}',
                    "biography": biography,
                    "cell_phone": cell_phone,
                    "office_phone": office_phone,
                    "home_phone": home_phone,
                    "email": email,
                    "personal_email": personal_email,
                    "company": company,
                    "title": title,
                    "company_name": company_name,
                    "company_phone": company_phone,
                    "company_web_site": company_web_site,
                    "company_email": company_email,
                    "company_bio": company_bio,
                    "role": role,
                    "role_id": role_id,
                    "create_date": create_date,
                    "update_date": update_date,
                    "location_information": location_information,
                    "contact_information": contact_information,
                    "country_code": country_code,
                    "achievement_information": achievement_information,
                    "amera_avatar_url": amerize_url(s3_avatar_url),
                    "security_exchange_option":
                        SECURITY_EXCHANGE_OPTIONS.get(
                            security_exchange_option, 0),
                    "status": status,
                    "online_status": online_status
                    # "city": city,
                    # "state": state,
                    # "province": province,
                    # "country": country
                }
                contacts.append(contact)
        return {
            "contacts": contacts,
            "count": count
        }


class InboxMailDa(BaseMailDA):
    folder_name = "INBOX"
    user_folders = True

    @classmethod
    def can_reply_to(cls, member_id, reply_id):
        # TODO: check query for reply
        return True

    @classmethod
    def can_forward_mail(cls, member_id, mail_id):
        # TODO: check query for forward
        return True

    @classmethod
    def forward_mail(cls, member_id, orig_mail_id, receivers_l, cc, bcc, user_folder_id, body_note):
        folder_query, folder_join = cls.folder_query(member_id)
        if not cls.can_forward_mail(member_id, orig_mail_id):
            raise HTTPBadRequest("You don't have permission for forwarding this email")
        receiver_insert_xref = """
            INSERT INTO mail_xref (member_id, owner_member_id, mail_header_id, recipient_type, message_type,
                                    new_mail, forward, forward_ts, forward_id)
            VALUES (%s, %s, %s, %s, 'internal', TRUE, TRUE, CURRENT_TIMESTAMP, %s)
            RETURNING id;
        """
        sender_insert_xref = """
            INSERT INTO mail_xref (recent_mail_folder_id, member_id, owner_member_id, mail_header_id, recipient_type,
                                    message_type, new_mail, forward, forward_ts, forward_id)
            VALUES (%s, %s, %s, %s, 'FROM', 'internal', FALSE, TRUE, CURRENT_TIMESTAMP, %s)
            RETURNING id;
        """

        header_query = f"""
            SELECT
                head.subject,
                body.message
            FROM mail_header as head
            INNER JOIN mail_xref xref on head.id = xref.mail_header_id
            INNER JOIN mail_body body on head.id = body.mail_header_id
            INNER JOIN mail_folder_xref mfx on xref.id = mfx.mail_xref_id
            WHERE (
                head.id = %s
                AND xref.recent_mail_folder_id {'=' if user_folder_id is not None else 'IS'} %s
                AND xref.member_id = %s
                AND head.message_locked = TRUE
                AND xref.deleted = FALSE
                AND xref.archived = FALSE
            )
            LIMIT 1;
        """
        attach_query = """
            SELECT
                attach.filename,
                attach.filetype,
                attach.filesize,
                attach_storage.id
            FROM mail_attachment as attach
            INNER JOIN file_storage_engine attach_storage on attach.file_id = attach_storage.id
            WHERE (
                attach.mail_header_id = %s
            );
        """
        insert_attachment = """
            INSERT INTO mail_attachment (mail_header_id, file_id, filename, filesize, filetype)
            VALUES (%s, %s, %s, %s, %s);
        """

        cls.source.execute(header_query, (orig_mail_id, user_folder_id, member_id))
        if cls.source.has_results():
            (
                subject,
                body,
            ) = cls.source.cursor.fetchone()

            extra_text = MailSettingsDA.get_reply_forward_signature(member_id)

            action_query, body_query = """
                INSERT INTO mail_header (
                    member_id,
                    subject,
                    message_to,
                    number_attachments,
                    message_locked
                ) VALUES (%s, %s, %s, %s, TRUE)
                RETURNING id;
            """, """
                INSERT INTO mail_body (member_id, message, mail_header_id)
                VALUES (%s, %s, %s);
            """

            query_data = (
                member_id, subject, json.dumps(receivers_l), 0
            )
            bod_query_data = (
                member_id, str(body) + (str(body_note) if body_note else "") + str(extra_text)
            )

            cls.source.execute(action_query, query_data)
            if cls.source.has_results():
                created_mail_id = cls.source.cursor.fetchone()[0]
                cls.source.execute(body_query, (*bod_query_data, created_mail_id))

                cls.source.execute(attach_query, (orig_mail_id,))
                if cls.source.has_results():
                    for (
                            filename,
                            filetype,
                            filesize,
                            attach_file_id
                    ) in cls.source.cursor.fetchall():
                        cls.source.execute(insert_attachment, (created_mail_id, attach_file_id,
                                                               filename, filesize, filetype))
                failed_receivers = []
                item_key = {
                    "BCC": bcc,
                    "CC": cc,
                    "TO": receivers_l
                }
                for each_key in item_key.keys():
                    if item_key[each_key] and "amera" in item_key[each_key]:
                        for each_receive in item_key[each_key]["amera"]:
                            cls.source.execute(receiver_insert_xref,
                                               (each_receive, member_id, created_mail_id, each_key, orig_mail_id))
                            if cls.source.has_results():
                                xref_id = cls.source.cursor.fetchone()[0]
                                MailFolderDA.add_folder_to_mail("INBOX", xref_id, each_receive, False)
                            else:
                                failed_receivers.append({
                                    "id": each_receive,
                                    "email": "-"
                                })
                    if item_key[each_key] and "external" in item_key[each_key]:
                        for each_receive in item_key[each_key]["external"]:
                            logger.debug("OPS! EXTERNAL")
                            # EXTERNAL SEND
                cls.source.execute(sender_insert_xref, (user_folder_id, member_id, member_id, created_mail_id,
                                                        orig_mail_id))
                if cls.source.has_results():
                    xref_id = cls.source.cursor.fetchone()[0]
                    MailFolderDA.add_folder_to_mail("SENT", xref_id, member_id, False)
                    cls.source.commit()
                    return failed_receivers
        raise HTTPInternalServerError


class DraftMailDA(BaseMailDA):
    folder_name = "DRAFT"
    message_locked = False

    @classmethod
    def can_reply_to(cls, member_id, reply_id):
        # TODO: check query for reply
        return True

    @classmethod
    def can_forward_mail(cls, member_id, mail_id):
        # TODO: check query for forward
        return True

    @classmethod
    def folder_id_is_valid(cls, member_id, folder_id):
        query = f"""
            SELECT EXISTS(
                SELECT id
                FROM mail_folder
                WHERE
                    id = %s
                    AND member_id = %s
                    AND name NOT IN {MailFolderDA.ORIGINAL_FOLDERS}
            );
        """
        cls.source.execute(query, (folder_id, member_id))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        raise HTTPInternalServerError

    @classmethod
    def cu_draft_mail_for_member(cls, member_id, subject, body, receiver=None, update=False,
                                 mail_header_id=None, reply_id=None, cc=None, bcc=None, user_folder_id=None):

        if receiver is None:
            receiver = []
        if user_folder_id == -1:
            user_folder_id = None
        if user_folder_id and not cls.folder_id_is_valid(member_id, user_folder_id):
            raise HTTPBadRequest("Folder is not valid")
        if reply_id and not cls.can_reply_to(member_id, reply_id):
            raise HTTPBadRequest("You don't have permission to reply this email")

        if update:
            if not mail_header_id:
                raise DataMissingError
            action_query, body_query, xref_query = """
                UPDATE mail_header
                SET subject = %s, message_to = %s, message_cc = %s , message_bcc = %s
                WHERE member_id = %s AND id = %s AND message_locked = FALSE
                RETURNING id;
            """, """
                UPDATE mail_body
                SET message = %s
                WHERE mail_header_id = %s;
            """, f"""
                UPDATE mail_xref
                SET recent_mail_folder_id = %s, replied = %s, replied_id = %s{', replied_ts = CURRENT_TIMESTAMP'
            if reply_id else ', replied_ts = NULL'}
                FROM mail_xref xref INNER JOIN mail_folder_xref mfx on xref.id = mfx.mail_xref_id
                WHERE (
                    mail_xref.member_id = %s
                    AND mail_xref.owner_member_id = %s
                    AND mail_xref.mail_header_id = %s
                    AND mail_xref.recipient_type = 'FROM'
                    AND mail_xref.message_type = 'internal'
                    AND mfx.mail_folder_id = %s
                    AND mail_xref.deleted = FALSE
                )
                RETURNING mail_xref.id;
            """

            query_data = (
                subject, json.dumps(receiver), json.dumps(cc) if cc else None, json.dumps(bcc) if bcc else None,
                member_id, mail_header_id
            )
            bod_query_data = (
                body,
            )
        else:
            action_query, body_query, xref_query = """
                INSERT INTO mail_header (
                    member_id,
                    subject,
                    message_to,
                    message_cc,
                    message_bcc,
                    number_attachments,
                    message_locked
                ) VALUES (%s, %s, %s, %s, %s, 0, FALSE)
                RETURNING id;
            """, """
                INSERT INTO mail_body (member_id, message, mail_header_id)
                VALUES (%s, %s, %s);
            """, """
                INSERT INTO mail_xref (recent_mail_folder_id, member_id, owner_member_id, mail_header_id,
                                        recipient_type, message_type, new_mail)
                VALUES (%s, %s, %s, %s, 'FROM', 'internal', FALSE)
                RETURNING id;
            """
            query_data = (
                member_id, subject,
                json.dumps(receiver), json.dumps(cc) if cc else None, json.dumps(bcc) if bcc else None
            )
            bod_query_data = (
                member_id, body
            )

        logger.debug(f"MEMBER: {member_id}")
        cls.source.execute(action_query, query_data)
        if cls.source.has_results():
            created_mail_id = cls.source.cursor.fetchone()[0]
            folder_id = MailFolderDA.get_folder_id_for_member("DRAFT", member_id)
            if update:
                created_mail_id = mail_header_id
                cls.source.execute(xref_query,
                                   (user_folder_id, True if reply_id else False, reply_id, member_id,
                                    member_id, created_mail_id, folder_id,))
            else:
                cls.source.execute(xref_query,
                                   (user_folder_id, member_id, member_id, created_mail_id))
                if cls.source.has_results():
                    xref_id = cls.source.cursor.fetchone()[0]
                    MailFolderDA.add_folder_to_mail("DRAFT", xref_id, member_id, False)
                else:
                    raise HTTPInternalServerError
            cls.source.execute(body_query, (*bod_query_data, created_mail_id))
            cls.source.commit()
            return created_mail_id
        raise HTTPNotFound(title="Draft not found or failed to create draft", description="")

    @classmethod
    def save_file_for_mail(cls, file_id, filename, filesize, filetype,
                           file_extension, mail_id, member_id):
        check_query = """
            SELECT id , number_attachments FROM mail_header
            WHERE id = %s AND member_id = %s AND message_locked = FALSE
            LIMIT 1;
        """
        update_query = """
            UPDATE mail_header
            SET number_attachments = %s
            WHERE id = %s AND member_id = %s AND message_locked = FALSE;
        """

        cls.source.execute(check_query, (mail_id, member_id))
        if cls.source.has_results():
            (mail_id, number_attachments) = cls.source.cursor.fetchone()
            insert = """
                INSERT INTO mail_attachment (mail_header_id, file_id, filename, filesize, filetype)
                VALUES (%s, %s, %s, %s, %s);
            """
            params = (mail_id, file_id, filename, filesize, file_extension)
            cls.source.execute(insert, params)
            header_params = (number_attachments + 1 if number_attachments
                                else 1, mail_id, member_id)
            cls.source.execute(update_query, header_params)
            if cls.source.has_results():
                cls.source.commit()
                return filename + file_extension, file_extension
            raise HTTPInternalServerError()
        raise HTTPBadRequest("Email not found")

    @classmethod
    def delete_file_for_mail(cls, file_id, mail_id, member_id):
        delete_query = """
            DELETE FROM mail_attachment
            USING mail_header
            WHERE
                mail_header.id = mail_attachment.mail_header_id
                AND file_id = %s
                AND mail_header_id = %s
                AND member_id = %s
                AND message_locked = FALSE
            RETURNING
                mail_attachment.mail_header_id,
                mail_header.number_attachments;
        """
        update_query = """
            UPDATE mail_header
            SET number_attachments = %s
            WHERE id = %s AND member_id = %s AND message_locked = FALSE;
        """

        cls.source.execute(delete_query, (file_id, mail_id, member_id))
        if cls.source.has_results():
            (head_id, number_attachments) = cls.source.cursor.fetchone()
            if head_id:
                if FileStorageDA.delete_file(file_id):
                    cls.source.execute(update_query,
                                       (number_attachments - 1 if number_attachments else 0, mail_id, member_id)
                                       )
                    if cls.source.has_results():
                        cls.source.commit()
                        return file_id
                    raise HTTPInternalServerError()
                raise HTTPBadRequest("Failed to delete file from storage")
        raise HTTPBadRequest("File or email mail not found")

    @classmethod
    def delete_draft_mail(cls, mail_id, member_id):
        delete_attachments_query = """
            DELETE FROM mail_attachment
            USING mail_header
            WHERE mail_header_id = %s AND member_id = %s AND message_locked = FALSE
            RETURNING file_id;
        """
        delete_header_query = """
            DELETE FROM mail_header
            WHERE id = %s AND member_id = %s AND message_locked = FALSE
            RETURNING id;
        """
        delete_body_query = """
            DELETE FROM mail_body
            WHERE mail_header_id = %s AND member_id = %s
            RETURNING mail_header_id
        """
        delete_xref = """
            DELETE FROM mail_xref
            WHERE (
                mail_xref.member_id = %s
                AND mail_xref.owner_member_id = %s
                AND mail_xref.mail_header_id = %s
                AND mail_xref.recipient_type = 'FROM'
                AND mail_xref.message_type = 'internal'
                AND mail_xref.new_mail = FALSE
            ) RETURNING id;
        """
        select_xref = """
            SELECT id FROM mail_xref
            WHERE (
                mail_xref.member_id = %s
                AND mail_xref.owner_member_id = %s
                AND mail_xref.mail_header_id = %s
                AND mail_xref.recipient_type = 'FROM'
                AND mail_xref.message_type = 'internal'
                AND mail_xref.new_mail = FALSE
                AND mail_xref.deleted = FALSE
                AND mail_xref.id IN (
                    SELECT mail_xref_id FROM mail_folder_xref
                    WHERE mail_folder_id = %s
                )
            ) LIMIT 1;
        """
        folder_id = MailFolderDA.get_folder_id_for_member("DRAFT", member_id)
        cls.source.execute(delete_attachments_query, (mail_id, member_id))
        if cls.source.has_results():
            failed_ids = []
            data = cls.source.cursor.fetchall()
            for (file_id,) in data:
                if not FileStorageDA.delete_file(file_id, False):
                    failed_ids.append(file_id)
            if len(failed_ids) > 0:
                logger.error(f"FAILED DELETE FILES: {failed_ids}")
        cls.source.execute(delete_body_query, (mail_id, member_id))
        if cls.source.has_results():
            cls.source.execute(select_xref, (member_id, member_id, mail_id, folder_id))
            if cls.source.has_results():
                xref_id = cls.source.cursor.fetchone()[0]
                MailFolderDA.remove_folder_from_mail("DRAFT", xref_id, member_id, False)
                cls.source.execute(delete_xref, (member_id, member_id, mail_id))
                if cls.source.has_results():
                    cls.source.execute(delete_header_query, (mail_id, member_id))
                    if cls.source.has_results():
                        cls.source.commit()
                        return mail_id
                    raise HTTPBadRequest("Failed to delete email", description="failed to delete header")
                raise HTTPBadRequest("Failed to delete email", description="failed to delete xref")
            raise HTTPBadRequest("Email not found or is not yours")
        raise HTTPBadRequest("Failed to delete email", description="failed to delete body")

    @classmethod
    def process_send_mail(cls, mail_id, member_id):

        header_query = """
            SELECT
                mail_header.subject,
                mail_header.message_to,
                mail_header.message_cc,
                mail_header.message_bcc,
                mb.message
            FROM mail_header
            INNER JOIN mail_body mb on mail_header.id = mb.mail_header_id
            WHERE mail_header.id = %s AND mail_header.member_id = %s AND mail_header.message_locked = FALSE;
        """

        update_body = """
            UPDATE mail_body
            SET message = %s
            WHERE (
                mail_header_id = %s
            ) RETURNING mail_header_id;
        """
        insert_xref = """
            INSERT INTO mail_xref (member_id, owner_member_id, mail_header_id, recipient_type, message_type,
                                    new_mail, replied_ts, replied_id, replied)
            VALUES (%s, %s, %s, %s, 'internal', TRUE, %s, %s, %s)
            RETURNING id;
        """

        finish_query = """
            UPDATE mail_header
            SET message_locked = TRUE , message_ts = CURRENT_TIMESTAMP
            WHERE id = %s AND member_id = %s AND message_locked = FALSE
            RETURNING id;
        """

        xref_update = """
            UPDATE mail_xref
            SET replied_ts = %s
            WHERE (
                member_id = %s
                AND owner_member_id = %s
                AND mail_header_id = %s
                AND recipient_type = 'FROM'
                AND message_type = 'internal'
                AND new_mail = FALSE
                AND deleted = FALSE
            ) RETURNING id;
        """

        xref_get = """
            SELECT
                replied_id
            FROM mail_xref
            INNER JOIN mail_folder_xref mfx on mail_xref.id = mfx.mail_xref_id
            WHERE (
                mail_xref.member_id = %s
                AND mail_xref.owner_member_id = %s
                AND mail_xref.mail_header_id = %s
                AND mail_xref.recipient_type = 'FROM'
                AND mail_xref.message_type = 'internal'
                AND mfx.mail_folder_id = %s
                AND mail_xref.new_mail = FALSE
                AND mail_xref.deleted = FALSE
            )
        """
        draft_folder_id = MailFolderDA.get_folder_id_for_member("DRAFT", member_id)

        # Get mail header
        cls.source.execute(xref_get, (member_id, member_id, mail_id, draft_folder_id))
        if cls.source.has_results():
            (reply_id,) = cls.source.cursor.fetchone()
            cls.source.execute(header_query, (mail_id, member_id))
            if cls.source.has_results():
                (subject, receivers, cc, bcc, body) = cls.source.cursor.fetchone()
                if not reply_id:
                    extra_text = MailSettingsDA.get_compose_signature(member_id)
                else:
                    extra_text = MailSettingsDA.get_reply_forward_signature(member_id)
                cls.source.execute(update_body, (str(body) + str(extra_text), mail_id))
                if cls.source.has_results():
                    failed_receivers = []
                    try:
                        receiver_data = json.loads(str(receivers))
                    except json.decoder.JSONDecodeError:
                        receiver_data = receivers

                    receiver_data = receiver_dict_validator(receiver_data)
                    bcc = receiver_dict_validator(bcc, False)
                    bcc = receiver_dict_validator(bcc, False)

                    item_key = {
                        "BCC": bcc,
                        "CC": cc,
                        "TO": receiver_data
                    }
                    for each_key in item_key.keys():
                        if item_key[each_key] and "amera" in item_key[each_key]:
                            for each_receive in item_key[each_key]["amera"]:
                                cls.source.execute(insert_xref, (each_receive, member_id, mail_id, each_key,
                                                                 None if not reply_id else datetime.datetime.now(),
                                                                 reply_id, bool(reply_id)))
                                if cls.source.has_results():
                                    xref_id = cls.source.cursor.fetchone()[0]
                                    MailFolderDA.add_folder_to_mail("INBOX", xref_id, each_receive, False)
                                else:
                                    failed_receivers.append({
                                        "id": each_receive,
                                        "email": "-"
                                    })
                        if item_key[each_key] and "external" in item_key[each_key]:
                            for _ in item_key[each_key]["external"]:
                                # re_member = MemberDA.get_member_by_email(each_receive) if re_member:
                                # cls.source.execute(insert_xref, (re_member["member_id"], member_id, mail_id,
                                # None if not reply_id else datetime.datetime.now(), reply_id, bool(reply_id)))
                                #
                                # if cls.source.has_results(): xref_id = cls.source.cursor.fetchone()[0]
                                # MailFolderDA.add_folder_to_mail("INBOX", xref_id, re_member["member_id"],
                                # False) else: failed_receivers.append({ "id": re_member["member_id"],
                                # "email": each_receive }) else:
                                logger.debug("OPS! EXTERNAL")
                                # EXTERNAL SEND
                    cls.source.execute(finish_query, (mail_id, member_id))
                    if cls.source.has_results():
                        cls.source.execute(xref_update, (None if not reply_id else datetime.datetime.now(),
                                                         member_id, member_id, mail_id))
                        if cls.source.has_results():
                            xref_id = cls.source.cursor.fetchone()[0]
                            MailFolderDA.add_folder_to_mail("SENT", xref_id, member_id, False)
                            MailFolderDA.remove_folder_from_mail("DRAFT", xref_id, member_id, False)
                            cls.source.commit()
                            return failed_receivers
            raise HTTPInternalServerError
        raise HTTPNotFound(title="Email not found", description="")


class StarMailDa(BaseMailDA):
    folder_name = "Starred"

    @classmethod
    def folder_query(cls, member_id):
        folder_id = MailFolderDA.get_folder_id_for_member(str(cls.folder_name).upper(), member_id)
        return (f"""AND mfx.mail_folder_id = {folder_id}
                AND xref.deleted = FALSE
                AND xref.archived = FALSE
                AND xref.starred = TRUE
                """,
                """INNER JOIN mail_folder_xref mfx on xref.id = mfx.mail_xref_id""")

    @classmethod
    def add_remove_mail_to_star(cls, mail_id, member_id, add=True):
        xref_query = f"""
            SELECT
                id
            FROM mail_xref
            WHERE (
                mail_xref.member_id = %s
                AND mail_xref.mail_header_id = %s
                AND mail_xref.deleted = FALSE
                AND mail_xref.archived = FALSE
                AND mail_xref.starred = {'FALSE' if add else 'TRUE'}
            )
        """

        xref_update = f"""
            UPDATE mail_xref
            SET
                starred = {'TRUE' if add else 'FALSE'},
                starred_ts = {'CURRENT_TIMESTAMP' if add else 'NULL'},
                archived = FALSE,
                archived_ts = NULL,
                deleted = False,
                deleted_ts = NULL
            WHERE (
                member_id = %s
                AND id = %s
            ) RETURNING id;
        """

        cls.source.execute(xref_query, (member_id, mail_id))
        if cls.source.has_results():
            xref_id = cls.source.cursor.fetchone()[0]
            if add:
                MailFolderDA.add_folder_to_mail(cls.folder_name.upper(), xref_id, member_id, False)
            else:
                MailFolderDA.remove_folder_from_mail(cls.folder_name.upper(), xref_id, member_id, False)
            cls.source.execute(xref_update, (member_id, xref_id))
            if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
            raise HTTPBadRequest("failed to add email to starred folder")
        raise HTTPBadRequest("email not found")


class TrashMailDa(BaseMailDA):
    folder_name = "Trash"

    folder_exclude_query = None

    @classmethod
    def folder_query(cls, member_id):
        folder_id = MailFolderDA.get_folder_id_for_member(str(cls.folder_name).upper(), member_id)
        return (f"""AND mfx.mail_folder_id = {folder_id}
                AND xref.deleted = TRUE
                AND xref.archived = FALSE
                """,
                """INNER JOIN mail_folder_xref mfx on xref.id = mfx.mail_xref_id""")

    @classmethod
    def add_to_trash(cls, mail_id, member_id):
        xref_query = """
            SELECT
                id
            FROM mail_xref
            WHERE (
                mail_xref.member_id = %s
                AND mail_xref.mail_header_id = %s
                AND mail_xref.deleted = FALSE
            )
        """

        xref_update = """
            UPDATE mail_xref
            SET
                deleted = TRUE,
                deleted_ts = CURRENT_TIMESTAMP,
                archived = FALSE,
                archived_ts = NULL
            WHERE (
                member_id = %s
                AND id = %s
            ) RETURNING id;
        """

        cls.source.execute(xref_query, (member_id, mail_id))
        if cls.source.has_results():
            xref_id = cls.source.cursor.fetchone()[0]
            MailFolderDA.remove_all_non_origin_folders_from_mail(xref_id, member_id, False, ["SENT"])
            MailFolderDA.add_folder_to_mail(cls.folder_name.upper(), xref_id, member_id, False)
            cls.source.execute(xref_update, (member_id, xref_id))
            if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
        raise HTTPBadRequest("Email not exists!")

    @classmethod
    def add_to_archive(cls, mail_id, member_id):
        xref_query = f"""
            SELECT
                mail_xref.id
            FROM mail_xref
            INNER JOIN mail_folder_xref mfx on mail_xref.id = mfx.mail_xref_id
            INNER JOIN mail_folder mf on mf.id = mfx.mail_folder_id
            WHERE (
                mail_xref.member_id = %s
                AND mail_xref.mail_header_id = %s
                AND mf.name = '{cls.folder_name.upper()}'
            )
        """

        xref_update = """
            UPDATE mail_xref
            SET
                archived = TRUE,
                archived_ts = CURRENT_TIMESTAMP,
                deleted = FALSE,
                deleted_ts = NULL
            WHERE (
                member_id = %s
                AND id = %s
            ) RETURNING id;
        """

        cls.source.execute(xref_query, (member_id, mail_id))
        if cls.source.has_results():
            xref_id = cls.source.cursor.fetchone()[0]
            MailFolderDA.remove_folder_from_mail(cls.folder_name.upper(), xref_id, member_id, False)  # Remove from trash
            MailFolderDA.add_folder_to_mail(ArchiveMailDa.folder_name.upper(), xref_id, member_id, False)  # Add to Archive
            cls.source.execute(xref_update, (member_id, xref_id))
            if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
        raise HTTPBadRequest("Email not exists")

    @classmethod
    def remove_from_trash(cls, mail_id, member_id):
        xref_query = """
            SELECT
                id
            FROM mail_xref
            WHERE (
                mail_xref.member_id = %s
                AND mail_xref.mail_header_id = %s
                AND mail_xref.deleted = TRUE
            )
        """

        xref_update = """
            UPDATE mail_xref
            SET deleted = FALSE , deleted_ts = NULL
            WHERE (
                member_id = %s
                AND id = %s
            ) RETURNING id;
        """

        cls.source.execute(xref_query, (member_id, mail_id))
        if cls.source.has_results():
            xref_id = cls.source.cursor.fetchone()[0]
            MailFolderDA.remove_folder_from_mail(cls.folder_name.upper(), xref_id, member_id, False)
            cls.source.execute(xref_update, (member_id, xref_id))
            if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
        raise HTTPBadRequest("Email not exists")

    @classmethod
    def delete_mail(cls, mail_id, member_id):
        xref_query = """
            DELETE FROM mail_xref
            WHERE (
                mail_xref.member_id = %s
                AND mail_xref.mail_header_id = %s
                AND mail_xref.deleted = TRUE
            )
            RETURNING id;
        """
        cls.source.execute(xref_query, (member_id, mail_id))
        if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
            cls.source.commit()
            return
        raise HTTPBadRequest("Email not exists")


class ArchiveMailDa(BaseMailDA):
    folder_name = "Archive"

    folder_exclude_query = None

    @classmethod
    def folder_query(cls, member_id):
        folder_id = MailFolderDA.get_folder_id_for_member(str(cls.folder_name).upper(), member_id)
        return (f"""AND mfx.mail_folder_id = {folder_id}
                AND xref.deleted = FALSE
                AND xref.archived = TRUE
                """,
                """INNER JOIN mail_folder_xref mfx on xref.id = mfx.mail_xref_id""")

    @classmethod
    def add_to_archive(cls, mail_id, member_id):
        xref_query = """
            SELECT
                id
            FROM mail_xref
            WHERE (
                member_id = %s
                AND mail_header_id = %s
            )
        """

        xref_update = """
            UPDATE mail_xref
            SET
                archived = TRUE,
                archived_ts = CURRENT_TIMESTAMP,
                deleted = FALSE,
                deleted_ts = NULL
            WHERE (
                member_id = %s
                AND id = %s
            ) RETURNING id;
        """

        cls.source.execute(xref_query, (member_id, mail_id))
        if cls.source.has_results():
            xref_id = cls.source.cursor.fetchone()[0]
            MailFolderDA.remove_all_non_origin_folders_from_mail(xref_id, member_id, False, ["SENT"])
            MailFolderDA.add_folder_to_mail(cls.folder_name.upper(), xref_id, member_id, False)
            cls.source.execute(xref_update, (member_id, xref_id))
            if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
        raise HTTPBadRequest("Email not exists")

    @classmethod
    def add_to_trash(cls, mail_id, member_id):
        xref_query = f"""
            SELECT
                mail_xref.id
            FROM mail_xref
            INNER JOIN mail_folder_xref mfx on mail_xref.id = mfx.mail_xref_id
            INNER JOIN mail_folder mf on mf.id = mfx.mail_folder_id
            WHERE (
                mail_xref.member_id = %s
                AND mail_xref.mail_header_id = %s
                AND mf.name = '{cls.folder_name.upper()}'
                AND mail_xref.deleted = FALSE
            )
        """

        xref_update = """
            UPDATE mail_xref
            SET
                deleted = TRUE,
                deleted_ts = CURRENT_TIMESTAMP,
                archived = FALSE,
                archived_ts = NULL
            WHERE (
                member_id = %s
                AND id = %s
            ) RETURNING id;
        """

        cls.source.execute(xref_query, (member_id, mail_id))
        if cls.source.has_results():
            xref_id = cls.source.cursor.fetchone()[0]
            MailFolderDA.remove_folder_from_mail(cls.folder_name.upper(), xref_id, member_id, False)  # Remove from trash
            MailFolderDA.add_folder_to_mail(TrashMailDa.folder_name.upper(), xref_id, member_id, False)  # Add to Archive
            cls.source.execute(xref_update, (member_id, xref_id))
            if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
        raise HTTPBadRequest("Email not exists")

    @classmethod
    def remove_from_archive(cls, mail_id, member_id):
        xref_query = """
            SELECT
                id
            FROM mail_xref
            WHERE (
                mail_xref.member_id = %s
                AND mail_xref.mail_header_id = %s
                AND mail_xref.deleted = FALSE
                AND mail_xref.archived = TRUE
            )
        """

        xref_update = """
            UPDATE mail_xref
            SET archived = FALSE , archived_ts = NULL
            WHERE (
                member_id = %s
                AND id = %s
            ) RETURNING id;
        """

        cls.source.execute(xref_query, (member_id, mail_id))
        if cls.source.has_results():
            xref_id = cls.source.cursor.fetchone()[0]
            MailFolderDA.remove_folder_from_mail(cls.folder_name.upper(), xref_id, member_id, False)
            cls.source.execute(xref_update, (member_id, xref_id))
            if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
        raise HTTPBadRequest("Email not exists")

    @classmethod
    def delete_mail(cls, mail_id, member_id):
        xref_query = """
            DELETE FROM mail_xref
            WHERE (
                mail_xref.member_id = %s
                AND mail_xref.mail_header_id = %s
                AND mail_xref.deleted = FALSE
                AND mail_xref.archived = TRUE
            )
            RETURNING id;
        """
        cls.source.execute(xref_query, (member_id, mail_id))
        if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
            cls.source.commit()
            return
        raise HTTPBadRequest("Email not exists")


class MailSettingsDA(BaseDA):

    @classmethod
    def cu_setting_signature(cls, member_id, name, content, sign_id=None, update=False):
        if not update:
            query = """
                INSERT INTO mail_signature (member_id, name, content)
                VALUES ((SELECT member_id FROM mail_setting WHERE member_id = %s), %s, %s)
                RETURNING mail_signature.id;
            """
            data = (member_id, name, content)
        else:
            query = """
                UPDATE mail_signature
                SET name  = %s, content = %s
                FROM mail_setting
                WHERE (
                    mail_signature.id = %s
                    AND mail_setting.member_id = %s
                )
                RETURNING mail_signature.id;
            """
            data = (name, content, sign_id, member_id)

        cls.source.execute(query, data)
        if cls.source.has_results():
            sign_id = cls.source.cursor.fetchone()[0]
            # TODO: TEMP. to be deleted
            query = """
                UPDATE mail_setting
                SET compose_signature = %(sign_id)s, reply_forward_signature = %(sign_id)s
                WHERE mail_setting.member_id = %(member_id)s
            """
            cls.source.execute(query, ({
                "sign_id": sign_id,
                "member_id": member_id
            }))
            if not cls.source.has_results():
                raise HTTPInternalServerError
            # TODO: END
            cls.source.commit()
            return sign_id
        raise HTTPBadRequest("Signature not found" if update else "Failed to create signature")

    @classmethod
    def setting_signature_delete(cls, member_id, sign_id):
        query = """
            DELETE FROM mail_signature
            USING mail_setting
            WHERE (
                mail_setting.member_id = %s
                AND mail_signature.id = %s
            )
            RETURNING mail_signature.id
        """

        cls.source.execute(query, (member_id, sign_id))
        if cls.source.has_results():
            sign_id = cls.source.cursor.fetchone()[0]
            cls.source.commit()
            return sign_id
        raise HTTPBadRequest("Signature not found")

    @classmethod
    def setting_signature_list(cls, member_id):
        query = """
            SELECT
                sign.id,
                sign.name,
                sign.content
            FROM mail_signature AS sign
            INNER JOIN mail_setting ms on ms.member_id = sign.member_id
            WHERE (
                ms.member_id = %s
            )
        """

        cls.source.execute(query, (member_id,))
        data = []
        if cls.source.has_results():
            for (sign_id, name, content) in cls.source.cursor.fetchall():
                data.append({
                    "id": sign_id,
                    "name": name,
                    "content": content
                })
        return data

    @classmethod
    def settings_cu(cls, member_id, default_style, grammar, spelling, autocorrect):
        query = """
            INSERT INTO mail_setting (member_id, default_style, grammar, spelling, autocorrect)
            VALUES (%(member_id)s, %(style)s, %(grammar)s, %(spell)s, %(autocorrect)s)
            ON CONFLICT ON CONSTRAINT mail_setting_pkey
            DO
                UPDATE
                SET
                    default_style = %(style)s,
                    grammar = %(grammar)s,
                    spelling = %(spell)s,
                    autocorrect = %(autocorrect)s
                WHERE mail_setting.member_id = %(member_id)s
            RETURNING member_id;
        """

        cls.source.execute(query, {
            "member_id": member_id,
            "style": default_style,
            "grammar": grammar,
            "spell": spelling,
            "autocorrect": autocorrect
        })
        if cls.source.has_results():
            m_id = cls.source.cursor.fetchone()[0]
            if m_id:
                cls.source.commit()
                return
        raise HTTPInternalServerError

    @classmethod
    def settings_get(cls, member_id):
        get_query = """
            SELECT
                default_style,
                grammar,
                spelling,
                autocorrect
            FROM mail_setting
            WHERE member_id = %(member_id)s
            LIMIT 1;
        """
        insert_query = """
            INSERT INTO mail_setting (member_id, default_style)
            VALUES (%(member_id)s,'{}')
            RETURNING
                default_style,
                grammar,
                spelling,
                autocorrect;
        """
        cls.source.execute(get_query, {
            "member_id": member_id,
        })
        if not cls.source.has_results():
            cls.source.execute(insert_query, {
                "member_id": member_id,
            })
            cls.source.commit()
        if cls.source.has_results():
            (
                default_style,
                grammar,
                spelling,
                autocorrect
            ) = cls.source.cursor.fetchone()
            return {
                "default_style": default_style,
                "grammar": grammar,
                "spelling": spelling,
                "autocorrect": autocorrect
            }
        raise HTTPInternalServerError

    @classmethod
    def get_reply_forward_signature(cls, member_id):
        get_query = """
            SELECT
                content
            FROM mail_signature
            INNER JOIN mail_setting ms on mail_signature.id = ms.reply_forward_signature
            WHERE (
                ms.member_id = %s
            )
            LIMIT 1;
        """
        cls.source.execute(get_query, (member_id,))
        if cls.source.has_results():
            content = cls.source.cursor.fetchone()[0]
            return content if content else ""
        return ""

    @classmethod
    def get_compose_signature(cls, member_id):
        get_query = """
            SELECT
                content
            FROM mail_signature
            INNER JOIN mail_setting ms on mail_signature.id = ms.compose_signature
            WHERE (
                ms.member_id = %s
            )
            LIMIT 1;
        """
        cls.source.execute(get_query, (member_id,))
        if cls.source.has_results():
            content = cls.source.cursor.fetchone()[0]
            return content if content else ""
        return ""


class SentMailDA(BaseMailDA):
    folder_name = "Sent"
    user_folders = True


class MailServiceDA(BaseDA):
    
    @classmethod
    def get_all_text_mails(cls, member_id, is_history=False):
        mails = list()

        try:
            unread= ""

            if not is_history:
                unread = " AND xref.read = false"

            query_mails = f"""
                SELECT
                    head.id,
                    head.subject,
                    body.message,
                    head.message_ts,
                    head.message_to,
                    head.message_cc,
                    head.message_bcc,
                    xref.id as xref_id,
                    xref.read,
                    xref.new_mail,
                    member.email as email,
                    member.first_name as first_name,
                    member.last_name as last_name,
                    file_path(file_storage_engine.storage_engine_id, '/member/file') as s3_avatar_url
                FROM mail_header as head
                INNER JOIN mail_xref xref on head.id = xref.mail_header_id
                INNER JOIN mail_body body on head.id = body.mail_header_id
                INNER JOIN member member on member.id = xref.owner_member_id
                LEFT OUTER JOIN member_profile profile on member.id = profile.member_id
                LEFT OUTER JOIN file_storage_engine on file_storage_engine.id = profile.profile_picture_storage_id
                WHERE
                    (
                        head.message_to->'amera' @> to_char(%s, '999')::jsonb
                        OR
                        head.message_cc->'amera' @> to_char(%s, '999')::jsonb
                        OR
                        head.message_bcc->'amera' @> to_char(%s, '999')::jsonb
                    )
                    AND
                    xref.member_id = %s  AND xref.deleted = false
                    {unread}
                ORDER BY head.message_ts DESC
                LIMIT 10
            """

            param_mails = (member_id, member_id, member_id, member_id)


            cls.source.execute(query_mails, param_mails)
            if cls.source.has_results():
                for (
                        id,
                        subject,
                        message,
                        message_ts,
                        message_to,
                        message_cc,
                        message_bcc,
                        xref_id,
                        read,
                        new_mail,
                        email,
                        first_name,
                        last_name,
                        s3_avatar_url
                ) in cls.source.cursor:
                    mail = {
                        "id": id,
                        "subject": subject,
                        "message": message,
                        "create_date": message_ts,
                        "message_to": message_to,
                        "message_cc": message_cc,
                        "message_bcc": message_bcc,
                        "xref_id": xref_id,
                        "new_mail": new_mail,
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "amera_avatar_url": s3_avatar_url,
                        "read": read,
                        "invitation_type": "text_mail"
                    }
                    mails.append(mail)

            return mails
        except Exception as e:
            logger.error(e, exc_info=True)
            return None
