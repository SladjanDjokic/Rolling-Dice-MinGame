import logging

from falcon import HTTPInternalServerError

from app.util.db import source
from app.exceptions.data import HTTPBadRequest, HTTPNotFound

logger = logging.getLogger(__name__)


class MailFolderDA:
    ORIGINAL_FOLDERS = ("INBOX", "STARRED", "DRAFT", "TRASH", "SENT", "ARCHIVE",)
    source = source

    @classmethod
    def create_folder_for_member(cls, folder_name, member_id, commit=True):
        query = """
            INSERT INTO mail_folder (member_id, name) 
            VALUES (%s, %s)
            RETURNING id;
        """
        cls.source.execute(query, (member_id, folder_name))
        if cls.source.has_results():
            data = cls.source.cursor.fetchone()
            if commit:
                cls.source.commit()
            return data[0]
        else:
            logger.error(f"ERROR CREATE FOLDER MEMBER {member_id} => {folder_name}")
            return None

    @classmethod
    def create_initial_folders_for_member(cls, member_id):

        folders = cls.ORIGINAL_FOLDERS

        for eachDataGroup in folders:
            cls.create_folder_for_member(eachDataGroup, member_id)

    @classmethod
    def get_folder_id_for_member(cls, folder_name, member_id, commit=True, create=True):
        query = """
            SELECT id FROM mail_folder
            WHERE member_id = %s AND name = %s
            LIMIT 1;
        """
        cls.source.execute(query, (member_id, folder_name))
        if cls.source.has_results():
            data = cls.source.cursor.fetchone()
            return data[0]
        elif create:
            return cls.create_folder_for_member(folder_name, member_id, commit)
        else:
            raise HTTPBadRequest("server error in accessing mail folder")

    @classmethod
    def add_folder_to_mail(cls, folder_name, xref_id, member_id, commit=True):
        folder_id = cls.get_folder_id_for_member(folder_name, member_id, commit)
        check_query = """
            SELECT id FROM mail_folder
            INNER JOIN mail_folder_xref mfx on mail_folder.id = mfx.mail_folder_id
            WHERE (
                mfx.mail_xref_id = %s
                AND member_id = %s
                AND id = %s
            );
        """
        cls.source.execute(check_query, (xref_id, member_id, folder_id))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        else:
            insert = """
                INSERT INTO mail_folder_xref (mail_xref_id, mail_folder_id)
                VALUES (%s, %s)
                RETURNING mail_folder_id
            """
            cls.source.execute(insert, (xref_id, folder_id))
            if cls.source.has_results():
                if commit:
                    cls.source.commit()
                return cls.source.cursor.fetchone()[0]
            raise HTTPInternalServerError

    @classmethod
    def remove_folder_from_mail(cls, folder_name, xref_id, member_id, commit=True):
        folder_id = cls.get_folder_id_for_member(folder_name, member_id, commit, False)
        check_query = """
            DELETE FROM mail_folder_xref
            WHERE (
                mail_folder_id = %s
                AND mail_xref_id = %s
            ) RETURNING mail_xref_id;
        """
        cls.source.execute(check_query, (folder_id, xref_id))
        if cls.source.has_results():
            if commit:
                cls.source.commit()
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def remove_all_non_origin_folders_from_mail(cls, xref_id, member_id, commit=True, exceptions=None):
        if exceptions is None:
            exceptions = []
        exceptions = [str(each).upper() for each in exceptions]
        exceptions_list = "'" + ("','".join(exceptions)) + "'"
        check_query = f"""
            DELETE FROM mail_folder_xref
            WHERE (
                mail_folder_id IN (
                    SELECT id FROM mail_folder
                    WHERE (
                        member_id = %s
                        AND UPPER(name) NOT IN ('INBOX', 'SENT'{','+exceptions_list
                                                                if exceptions_list and len(exceptions_list) > 2 else ''
                                                            }))
                    )
                )
                AND mail_xref_id = %s
            ) RETURNING mail_xref_id;
        """
        cls.source.execute(check_query, (member_id, xref_id))
        if cls.source.has_results():
            if commit:
                cls.source.commit()
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def delete_all_folders(cls, xref_id, member_id, commit=True):
        check_query = """
            DELETE FROM mail_folder_xref
            WHERE (
                mail_folder_id IN (
                    SELECT id FROM mail_folder
                    WHERE (
                        member_id = %s
                    )
                )
                AND mail_xref_id = %s
            ) RETURNING mail_xref_id;
        """
        cls.source.execute(check_query, (member_id, xref_id))
        if cls.source.has_results():
            if commit:
                cls.source.commit()
            return cls.source.cursor.fetchone()[0]
        return None


class MailMemberFolder(object):
    source = source

    @classmethod
    def folder_exists(cls, member_id, folder_name):
        if str(folder_name) in MailFolderDA.ORIGINAL_FOLDERS:
            return True
        query = f"""
            SELECT EXISTS(
                SELECT id
                FROM mail_folder
                WHERE
                    name = %s
                    AND member_id = %s
            );
        """
        cls.source.execute(query, (str(folder_name).upper(), member_id))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        raise HTTPInternalServerError

    @classmethod
    def get_member_folders(cls, member_id):
        get_query = f"""
            SELECT
                id,
                name
            FROM mail_folder
            WHERE
                member_id = %s
                AND name NOT IN {MailFolderDA.ORIGINAL_FOLDERS}
            ORDER BY name
        """
        cls.source.execute(get_query, (member_id, ))
        if cls.source.has_results():
            result = []
            for (fid, name) in cls.source.cursor.fetchall():
                result.append({
                    "id": fid,
                    "name": name
                })
            return result
        return []

    @classmethod
    def cu_folder_for_member(cls, member_id, folder_name, folder_id=None):
        insert_query = """
            INSERT INTO mail_folder (member_id, name)
            VALUES (%s, %s)
            RETURNING id
        """
        update_query = """
            UPDATE mail_folder
            SET name = %s
            WHERE
                id = %s
                AND member_id = %s
        """
        if not folder_id and cls.folder_exists(member_id, folder_name):
            raise HTTPBadRequest("Folder already exists!")
        cls.source.execute(insert_query if not folder_id else update_query,
                           (member_id, folder_name) if not folder_id else (folder_name, folder_id, member_id))
        if cls.source.has_results():
            cls.source.commit()
            return folder_id if folder_id else cls.source.cursor.fetchone()[0]
        if folder_id:
            raise HTTPNotFound("Folder not found")
        else:
            raise HTTPBadRequest("Failed to create folder")

    @classmethod
    def delete_folder(cls, member_id, folder_id):
        delete_query = f"""
            DELETE FROM mail_folder
            WHERE
                id = %s
                AND member_id = %s
                AND name NOT IN {MailFolderDA.ORIGINAL_FOLDERS}
            RETURNING id
        """

        cls.source.execute(delete_query, (folder_id, member_id))
        if cls.source.has_results():
            cls.source.commit()
            return cls.source.cursor.fetchone()[0]
        raise HTTPNotFound("Folder not found")

    @classmethod
    def move_to_folder(cls, member_id, mail_id, mail_xref, folder_id):
        update_query = f"""
            UPDATE mail_xref
            SET recent_mail_folder_id = %(folder_id)s
            FROM mail_header as head
            WHERE
                head.id = mail_xref.mail_header_id
                AND head.message_locked = TRUE
                AND head.id = %(mail_id)s
                AND mail_xref.id = %(mail_xref)s
                AND mail_xref.member_id = %(member_id)s
                AND mail_xref.archived = FALSE
                AND mail_xref.deleted = FALSE
                AND NOT EXISTS(
                    SELECT * FROM mail_folder
                    WHERE
                        mail_folder.member_id = %(member_id)s
                        AND mail_folder.id = %(folder_id)s
                        AND mail_folder.name IN {MailFolderDA.ORIGINAL_FOLDERS}
                )
        """
        if folder_id == -1:
            folder_id = None
        cls.source.execute(update_query, ({
            "member_id": member_id,
            "mail_id": mail_id,
            "folder_id": folder_id,
            "mail_xref": mail_xref
        }))
        if cls.source.has_results():
            cls.source.commit()
            return folder_id
        raise HTTPNotFound(title="Invalid folder or folder cannot be changed",
                           description="Invalid folder or folder cannot be changed")
