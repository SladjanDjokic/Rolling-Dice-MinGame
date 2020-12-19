import logging

from falcon import HTTPInternalServerError

from app.util.db import source
from app.exceptions.data import HTTPBadRequest


logger = logging.getLogger(__name__)


class MailFolderDA:
    source = source

    @classmethod
    def create_folder_for_member(cls, folder_name, member_id, commit=True):
        query = """
            INSERT INTO mail_folder (member_id, name) 
            VALUES (%s, UPPER(%s))
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

        folders = (
            ("Inbox",),
            ("Starred", ),
            ("Drafts", ),
            ("Trash", ),
            ("Sent", ),
            ("Archive", ),
        )

        for eachDataGroup in folders:
            cls.create_folder_for_member(eachDataGroup[0], member_id)

    @classmethod
    def get_folder_id_for_member(cls, folder_name, member_id, commit=True, create=True):
        query = """
            SELECT id FROM mail_folder
            WHERE member_id = %s AND UPPER(name) = UPPER(%s)
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
