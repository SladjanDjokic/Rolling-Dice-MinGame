import datetime
import io
import json
import logging
import os
import sys

from falcon import HTTPBadRequest, HTTPInternalServerError, HTTPNotFound

from app.da.file_sharing import FileStorageDA
from app.da.mail_folder import MailFolderDA
from app.da.member import MemberDA
from app.exceptions.data import DataMissingError
from app.util.db import source
from app.util.filestorage import amerize_url

logger = logging.getLogger(__name__)


class BaseDA(object):
    source = source


class BaseMailDA(BaseDA):
    message_locked = True
    excluded_folders = ['trash', 'archive']

    @classmethod
    def folder_query(cls, member_id):
        folder_id = MailFolderDA.get_folder_id_for_member(cls.folder_name, member_id)
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
                AND mail_xref.member_id = %s
                {folder_query}
                AND xref.deleted = FALSE
            );
        """

    @classmethod
    def list_get_query(cls, start, search_query, order_query, member_id):
        folder_query, folder_join = cls.folder_query(member_id)
        return f"""
            SELECT
                head.id,
                head.subject,
                body.message,
                head.message_ts,
                m.email,
                m.first_name,
                m.last_name,
                xref.read,
                xref.new_mail,
                prof_image_engine.storage_engine_id,
                starred,
                COUNT(head.id) OVER() AS full_count
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
                starred
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
    def list_folder(cls, member_id, start=-1, size=20, search=None, sort=None, order=1):
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
                raise HTTPBadRequest
            order_query = f"""
                ORDER BY {sort_param}{' DESC' if order == -1 else ''}
            """

        if sort and sort == 'read':
            search_query += f"""
                AND xref.read = {'TRUE' if order == 1 else 'FALSE'}
            """
        header_query = cls.list_get_query(start, search_query, order_query, member_id)
        header_update = cls.list_after_update_query(member_id)
        # # Get mail header
        cls.source.execute(header_query, (start, member_id, cls.message_locked,
                                          *search_params, size))
        if cls.source.has_results():
            data = []
            new_mails = []
            all_count = 0
            for (
                    header_id,
                    subject,
                    body,
                    time,
                    sender_mail,
                    first_name,
                    last_name,
                    read,
                    new_mail,
                    prof_id,
                    is_star,
                    full_count
            ) in cls.source.cursor.fetchall():
                all_count = full_count
                data.append({
                    "mail_id": header_id,
                    "subject": subject,
                    "body": body,
                    "time": time.isoformat() if time else None,
                    "sender_mail": sender_mail,
                    "first_name": first_name,
                    "last_name": last_name,
                    "read": read,
                    "new_mail": new_mail,
                    "profile_url": amerize_url(prof_id),
                    "is_stared": is_star
                })
                if new_mail:
                    new_mails.append(header_id)
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
                is_starred
            ) = cls.source.cursor.fetchone()

            data = {
                "subject": subject,
                "body": body,
                "time": time.isoformat() if time else None,
                "sender_member_id": sender_member_id,
                "sender_mail": sender_mail,
                "first_name": first_name,
                "last_name": last_name,
                "profile_url": amerize_url(prof_id),
                "reply": {
                    "id": reply_id,
                    "subject": reply_subject,
                    "body": reply_body,
                    "time": reply_time.isoformat() if reply_time else None
                },
                "attachments": [],
                "is_stared": is_starred,
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


class InboxMailDa(BaseMailDA):

    folder_name = "INBOX"

    @classmethod
    def can_reply_to(cls, member_id, reply_id):
        # TODO: check query for reply
        return True

    @classmethod
    def can_forward_mail(cls, member_id, mail_id):
        # TODO: check query for forward
        return True

    @classmethod
    def forward_mail(cls, member_id, orig_mail_id, receivers_l):
        folder_query, folder_join = cls.folder_query(member_id)
        if not cls.can_forward_mail(member_id, orig_mail_id):
            raise HTTPBadRequest
        failed_receivers = []
        receiver_insert_xref = """
            INSERT INTO mail_xref (member_id, owner_member_id, mail_header_id, recipient_type, message_type,
                                    new_mail, forward, forward_ts, forward_id)
            VALUES (%s, %s, %s, 'TO', 'internal', TRUE, TRUE, CURRENT_TIMESTAMP, %s)
            RETURNING id;
        """
        sender_insert_xref = """
            INSERT INTO mail_xref (member_id, owner_member_id, mail_header_id, recipient_type, message_type,
                                    new_mail, forward, forward_ts, forward_id)
            VALUES (%s, %s, %s, 'FROM', 'internal', FALSE, TRUE, CURRENT_TIMESTAMP, %s)
            RETURNING id;
        """

        header_query = f"""
            SELECT
                head.subject,
                body.message
            FROM mail_header as head
            INNER JOIN mail_xref xref on head.id = xref.mail_header_id
            INNER JOIN mail_body body on head.id = body.mail_header_id
            {folder_join}
            WHERE (
                head.id = %s
                AND xref.member_id = %s
                AND head.message_locked = TRUE
                AND xref.deleted = FALSE
                {folder_query}
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

        cls.source.execute(header_query, (orig_mail_id, member_id))
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
                    message_from,
                    message_to,
                    number_attachments,
                    message_locked
                ) VALUES (%s, %s, %s, %s, %s, TRUE)
                RETURNING id;
            """, """
                INSERT INTO mail_body (member_id, message, mail_header_id)
                VALUES (%s, %s, %s);
            """

            query_data = (
                member_id, subject, member_id, json.dumps(receivers_l), 0
            )
            bod_query_data = (
                member_id, str(body) + str(extra_text)
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

                for receive in receivers_l:
                    reci_mem = MemberDA.get_member_by_email(receive)
                    if reci_mem:
                        cls.source.execute(receiver_insert_xref,
                                           (reci_mem["member_id"], member_id, created_mail_id, orig_mail_id))
                        if cls.source.has_results():
                            xref_id = cls.source.cursor.fetchone()[0]
                            MailFolderDA.add_folder_to_mail("inbox", xref_id, reci_mem["member_id"], False)
                        else:
                            failed_receivers.append({
                                "id": reci_mem["member_id"],
                                "email": receive
                            })
                    else:
                        logger.debug("OPS! EXTERNAL")
                        # EXTERNAL SEND
                        pass
                cls.source.execute(sender_insert_xref, (member_id, member_id, created_mail_id,
                                                        orig_mail_id))
                if cls.source.has_results():
                    xref_id = cls.source.cursor.fetchone()[0]
                    MailFolderDA.add_folder_to_mail("sent", xref_id, member_id, False)
                    cls.source.commit()
                    return failed_receivers
        raise HTTPInternalServerError


class DraftMailDA(BaseMailDA):

    folder_name = "draft"
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
    def cu_draft_mail_for_member(cls, member, subject, body, receiver=None, files_list=None, update=False,
                                 mail_header_id=None, reply_id=None):

        if files_list is None:
            files_list = []
        if receiver is None:
            receiver = []

        if reply_id and not cls.can_reply_to(member["member_id"], reply_id):
            raise HTTPBadRequest

        if update:
            if not mail_header_id:
                raise DataMissingError
            action_query, body_query, xref_query = """
                UPDATE mail_header
                SET subject = %s, message_to = %s, number_attachments = %s
                WHERE member_id = %s AND id = %s AND message_locked = FALSE
                RETURNING id;
            """, """
                UPDATE mail_body 
                SET message = %s
                WHERE mail_header_id = %s;
            """, f"""
                UPDATE mail_xref
                SET replied = %s, replied_id = %s{', replied_ts = CURRENT_TIMESTAMP'
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
                subject, json.dumps(receiver), len(files_list), member["member_id"], mail_header_id
            )
            bod_query_data = (
                body,
            )
        else:
            action_query, body_query, xref_query = """
                INSERT INTO mail_header (
                    member_id,
                    subject,
                    message_from,
                    message_to,
                    number_attachments,
                    message_locked
                ) VALUES (%s, %s, %s, %s, %s, FALSE)
                RETURNING id;
            """, """
                INSERT INTO mail_body (member_id, message, mail_header_id)
                VALUES (%s, %s, %s);
            """, """
                INSERT INTO mail_xref (member_id, owner_member_id, mail_header_id, recipient_type, message_type,
                                        new_mail)
                VALUES (%s, %s, %s, 'FROM', 'internal', FALSE)
                RETURNING id;
            """
            query_data = (
                member["member_id"], subject, member["email"], json.dumps(receiver), len(files_list)
            )
            bod_query_data = (
                member["member_id"], body
            )

        logger.debug(f"MEMBER: {member}")
        cls.source.execute(action_query, query_data)
        if cls.source.has_results():
            created_mail_id = cls.source.cursor.fetchone()[0]
            folder_id = MailFolderDA.get_folder_id_for_member("draft", member["member_id"])
            if update:
                created_mail_id = mail_header_id
                cls.source.execute(xref_query, (True if reply_id else False, reply_id, member["member_id"],
                                                member["member_id"], created_mail_id, folder_id,))
            else:
                cls.source.execute(xref_query, (member["member_id"], member["member_id"], created_mail_id))
                if cls.source.has_results():
                    xref_id = cls.source.cursor.fetchone()[0]
                    MailFolderDA.add_folder_to_mail("draft", xref_id, member["member_id"], False)
                else:
                    raise HTTPInternalServerError
            cls.source.execute(body_query, (*bod_query_data, created_mail_id))
            cls.source.commit()
            return created_mail_id
        raise HTTPNotFound

    @classmethod
    def save_file_for_mail(cls, file_id, file, mail_id, member_id):
        check_query = """
            SELECT id , number_attachments FROM mail_header
            WHERE id = %s AND member_id = %s AND message_locked = FALSE
            LIMIT 1;
        """

        cls.source.execute(check_query, (mail_id, member_id))
        if cls.source.has_results():
            (mail_id, number_attachments) = cls.source.cursor.fetchone()
            insert = """
                INSERT INTO mail_attachment (mail_header_id, file_id, filename, filesize, filetype)
                VALUES (%s, %s, %s, %s, %s);
            """
            if type(file.file) == io.BufferedRandom:
                size = os.fstat(file.file.fileno()).st_size
            elif type(file.file) == io.BytesIO:
                size = sys.getsizeof(file.file)
            else:
                logger.error(f"FAILED TO ALLOCATE FILE SIZE WITH TYPE {type(file.file)}")
                logger.debug(f"{file.file}")
                raise HTTPInternalServerError
            tmp, file_extension = os.path.splitext(file.filename)
            tmp, filename = os.path.split(file.filename)
            cls.source.execute(insert, (mail_id, file_id, filename, size, file_extension[1:]))
            cls.source.commit()
            return filename + file_extension, file_extension
        else:
            raise HTTPBadRequest()

    @classmethod
    def delete_file_for_mail(cls, file_id, mail_id, member_id):
        delete_query = """
            DELETE FROM mail_attachment
            USING mail_header
            WHERE file_id = %s AND mail_header_id = %s AND member_id = %s AND message_locked = FALSE;
        """

        cls.source.execute(delete_query, (file_id, mail_id, member_id))
        if FileStorageDA.delete_file(file_id):
            cls.source.commit()
            return file_id
        raise HTTPBadRequest()

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
        folder_id = MailFolderDA.get_folder_id_for_member("draft", member_id)
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
                MailFolderDA.remove_folder_from_mail("draft", xref_id, member_id, False)
                cls.source.execute(delete_xref, (member_id, member_id, mail_id))
                if cls.source.has_results():
                    cls.source.execute(delete_header_query, (mail_id, member_id))
                    if cls.source.has_results():
                        cls.source.commit()
                        return mail_id
        raise HTTPBadRequest()

    @classmethod
    def process_send_mail(cls, mail_id, member_id):

        header_query = """
            SELECT mail_header.subject, mail_header.message_to, mb.message FROM mail_header
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
            VALUES (%s, %s, %s, 'TO', 'internal', TRUE, %s, %s, %s)
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
        draft_folder_id = MailFolderDA.get_folder_id_for_member("draft", member_id)

        # Get mail header
        cls.source.execute(xref_get, (member_id, member_id, mail_id, draft_folder_id))
        if cls.source.has_results():
            (reply_id,) = cls.source.cursor.fetchone()
            cls.source.execute(header_query, (mail_id, member_id))
            if cls.source.has_results():
                (subject, receivers, body) = cls.source.cursor.fetchone()
                if not reply_id:
                    extra_text = MailSettingsDA.get_compose_signature(member_id)
                else:
                    extra_text = MailSettingsDA.get_reply_forward_signature(member_id)
                cls.source.execute(update_body, (str(body)+str(extra_text), mail_id))
                if cls.source.has_results():

                    failed_receivers = []
                    receivers_list = json.loads(str(receivers))
                    receiver_data = receivers_list
                    for each_receive in receiver_data["amera"]:
                        cls.source.execute(insert_xref, (each_receive, member_id, mail_id,
                                                         None if not reply_id else datetime.datetime.now(),
                                                         reply_id, bool(reply_id)))

                        if cls.source.has_results():
                            xref_id = cls.source.cursor.fetchone()[0]
                            MailFolderDA.add_folder_to_mail("Inbox", xref_id, each_receive, False)
                        else:
                            failed_receivers.append({
                                "id": each_receive,
                            })
                    for each_receive in receiver_data["external"]:
                        # re_member = MemberDA.get_member_by_email(each_receive)
                        # if re_member:
                        #     cls.source.execute(insert_xref, (re_member["member_id"], member_id, mail_id,
                        #                                      None if not reply_id else datetime.datetime.now(),
                        #                                      reply_id, bool(reply_id)))
                        #
                        #     if cls.source.has_results():
                        #         xref_id = cls.source.cursor.fetchone()[0]
                        #         MailFolderDA.add_folder_to_mail("Inbox", xref_id, re_member["member_id"], False)
                        #     else:
                        #         failed_receivers.append({
                        #             "id": re_member["member_id"],
                        #             "email": each_receive
                        #         })
                        # else:
                        logger.debug("OPS! EXTERNAL")
                        # EXTERNAL SEND
                    cls.source.execute(finish_query, (mail_id, member_id))
                    if cls.source.has_results():
                        cls.source.execute(xref_update, (None if not reply_id else datetime.datetime.now(),
                                                         member_id, member_id, mail_id))
                        if cls.source.has_results():
                            xref_id = cls.source.cursor.fetchone()[0]
                            MailFolderDA.add_folder_to_mail("sent", xref_id, member_id, False)
                            MailFolderDA.remove_folder_from_mail("draft", xref_id, member_id, False)
                            cls.source.commit()
                            return failed_receivers
            raise HTTPInternalServerError
        raise HTTPNotFound


class StarMailDa(BaseMailDA):

    folder_name = "Starred"

    @classmethod
    def folder_query(cls, member_id):
        folder_id = MailFolderDA.get_folder_id_for_member(cls.folder_name, member_id)
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
                MailFolderDA.add_folder_to_mail(cls.folder_name, xref_id, member_id, False)
            else:
                MailFolderDA.remove_folder_from_mail(cls.folder_name, xref_id, member_id, False)
            cls.source.execute(xref_update, (member_id, xref_id))
            if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
        raise HTTPBadRequest


class TrashMailDa(BaseMailDA):

    folder_name = "Trash"

    folder_exclude_query = None

    @classmethod
    def folder_query(cls, member_id):
        folder_id = MailFolderDA.get_folder_id_for_member(cls.folder_name, member_id)
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
            MailFolderDA.remove_all_non_origin_folders_from_mail(xref_id, member_id, False, ["sent"])
            MailFolderDA.add_folder_to_mail(cls.folder_name, xref_id, member_id, False)
            cls.source.execute(xref_update, (member_id, xref_id))
            if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
        raise HTTPBadRequest

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
                AND UPPER(mf.name) = '{cls.folder_name.upper()}'
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
            MailFolderDA.remove_folder_from_mail(cls.folder_name, xref_id, member_id, False)    # Remove from trash
            MailFolderDA.add_folder_to_mail(ArchiveMailDa.folder_name, xref_id, member_id, False)    # Add to Archive
            cls.source.execute(xref_update, (member_id, xref_id))
            if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
        raise HTTPBadRequest

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
            MailFolderDA.remove_folder_from_mail(cls.folder_name, xref_id, member_id, False)
            cls.source.execute(xref_update, (member_id, xref_id))
            if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
        raise HTTPBadRequest

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
        if cls.source.has_results():
            if cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
        raise HTTPBadRequest


class ArchiveMailDa(BaseMailDA):

    folder_name = "Archive"

    folder_exclude_query = None

    @classmethod
    def folder_query(cls, member_id):
        folder_id = MailFolderDA.get_folder_id_for_member(cls.folder_name, member_id)
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
            MailFolderDA.remove_all_non_origin_folders_from_mail(xref_id, member_id, False, ["sent"])
            MailFolderDA.add_folder_to_mail(cls.folder_name, xref_id, member_id, False)
            cls.source.execute(xref_update, (member_id, xref_id))
            if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
        raise HTTPBadRequest

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
                AND UPPER(mf.name) = UPPER('{cls.folder_name}')
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
            MailFolderDA.remove_folder_from_mail(cls.folder_name, xref_id, member_id, False)    # Remove from trash
            MailFolderDA.add_folder_to_mail(TrashMailDa.folder_name, xref_id, member_id, False)    # Add to Archive
            cls.source.execute(xref_update, (member_id, xref_id))
            if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
        raise HTTPBadRequest

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
            MailFolderDA.remove_folder_from_mail(cls.folder_name, xref_id, member_id, False)
            cls.source.execute(xref_update, (member_id, xref_id))
            if cls.source.has_results() and cls.source.cursor.fetchone()[0]:
                cls.source.commit()
                return
        raise HTTPBadRequest

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
        raise HTTPBadRequest


class MailSettingsDA(BaseDA):

    @classmethod
    def cu_setting_signature(cls, member_id, name, content, sign_id=None, update=False):
        if not update:
            query = """
                INSERT INTO mail_signature (mail_setting_id, name, content)
                VALUES ((SELECT id FROM mail_setting WHERE member_id = %s), %s, %s)
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
            return sign_id
        raise HTTPBadRequest

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
            return sign_id
        raise HTTPBadRequest

    @classmethod
    def setting_signature_list(cls, member_id):
        query = """
            SELECT 
                sign.id,
                sign.name,
                sign.content
            FROM mail_signature AS sign
            INNER JOIN mail_setting ms on ms.member_id = sign.mail_setting_id
            WHERE (
                ms.member_id = %s
            )
        """

        cls.source.execute(query, (member_id, ))
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
            VALUES (%(member_id)s, %(style)s, %(grammer)s, $(spell)s, $(autocorrect)s)
            ON CONFLICT ON CONSTRAINT mail_setting_pkey
            DO
                UPDATE
                SET default_style = %(style)s, grammar = %(grammar)s, spelling = $(spell)s, autocorrect = $(autocorrect)s
                WHERE member_id = %(member_id)s
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
        cls.source.execute(get_query, (member_id, ))
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
        cls.source.execute(get_query, (member_id, ))
        if cls.source.has_results():
            content = cls.source.cursor.fetchone()[0]
            return content if content else ""
        return ""


class SentMailDA(BaseDA):

    folder_name = "Sent"
