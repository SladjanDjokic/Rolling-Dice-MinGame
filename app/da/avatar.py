from app.util.db import source
from app.util.filestorage import amerize_url


class AvatarDA(object):
    source = source

    @classmethod
    def get_avatar_url(cls, member_id):
        query = ("""
            SELECT 
                file_storage_engine.storage_engine_id as s3_avatar_url
            FROM member_profile
                LEFT OUTER JOIN file_storage_engine ON member_profile.profile_picture_storage_id = file_storage_engine.id
            WHERE member_id = %s
            """)
        params = (member_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            (s3_avatar_url,) = cls.source.cursor.fetchone()
            return amerize_url(s3_avatar_url)

    @classmethod
    def update_avatar(cls, file_storage_id, member_id):
        query = ("""
            INSERT INTO member_profile (member_id, profile_picture_storage_id)
            VALUES (%s, %s)
            ON conflict(member_id) DO UPDATE 
            SET profile_picture_storage_id = %s
        """)
        params = (member_id, file_storage_id, file_storage_id)
        cls.source.execute(query, params)
        try:
            cls.source.commit()
            return True
        except:
            return False
