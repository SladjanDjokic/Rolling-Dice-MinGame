import logging
import datetime
from app.util.db import source, formatSortingParams
from app.util.filestorage import amerize_url

logger = logging.getLogger(__name__)


class NewsFeedsDA(object):
    source = source

    @classmethod
    def add_new_topic(cls, member_id, topic_content, commit=True):
        query = """INSERT INTO news_topic 
            (member_id, topic_content)
            VALUES (%s, %s)
            RETURNING id
        """
        params = (member_id, topic_content)
        try:
            cls.source.execute(query, params, debug_query=False)
            topic_id = cls.source.get_last_row_id()

            if commit:
                cls.source.commit()
            return topic_id

        except Exception as e:
            logger.error(e, exc_info=True)
            return None
    
    @classmethod
    def add_topic_attachment(cls, news_topic_id, news_file_id, commit=True):
        query = """INSERT INTO news_media 
            (news_topic_id, news_file_id)
            VALUES (%s, %s)
            RETURNING id
        """
        params = (news_topic_id, news_file_id)
        
        try:
            cls.source.execute(query, params, debug_query=False)
            if commit:
                cls.source.commit()

        except Exception as e:
            logger.error(e, exc_info=True)
            return False
    
    @classmethod
    def add_post_attachment(cls, news_topic_id, news_post_id, news_file_id, commit=True):
        query = """INSERT INTO news_media 
            (news_topic_id, news_post_id, news_file_id)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        params = (news_topic_id, news_post_id, news_file_id)
        
        try:
            cls.source.execute(query, params, debug_query=False)
            if commit:
                cls.source.commit()

        except Exception as e:
            logger.error(e, exc_info=True)
            return False

    @classmethod
    def get_topics(cls, members=[], page_size=None, page_number=None):

        logger.debug(f"members=>{members}")
        

        query = (f"""
            SELECT
                nt.id as topic_id,
                nt.topic_content,
                nt.create_date,
                nt.member_id,
                topic_creator.first_name,
                topic_creator.last_name,
                topic_creator_avatar.storage_engine_id as amera_avatar_url,
                COALESCE(json_agg(json_build_object(
                    'file_id', nm.id,
                    'file_path', file_path(fse.storage_engine_id, '/member/file'),
                    'file_size', fse.file_size_bytes,
                    'mime_type', fse.mime_type
                )) FILTER (WHERE nm.id IS NOT NULL), '[]') AS attachments,
                COALESCE(json_agg(reply.*) FILTER (WHERE reply.post_id IS NOT NULL), '[]') AS replies
            FROM news_topic as nt
            LEFT OUTER JOIN member as topic_creator ON topic_creator.id = nt.member_id
            LEFT OUTER JOIN member_profile as topic_creator_profile ON topic_creator_profile.member_id = nt.member_id
            LEFT OUTER JOIN file_storage_engine as topic_creator_avatar ON topic_creator_avatar.id = topic_creator_profile.profile_picture_storage_id
            LEFT OUTER JOIN news_media as nm ON nm.news_topic_id = nt.id AND nm.news_post_id IS NULL
            LEFT OUTER JOIN file_storage_engine AS fse ON nm.news_file_id = fse.id
            LEFT OUTER JOIN (
              SELECT
                np.id as post_id,
                np.news_topic_id,
                np.member_id,
                post_creator.first_name,
                post_creator.last_name,
                file_path(post_creator_avatar.storage_engine_id, '/member/file') as amera_avatar_url,
                np.post_content,
                np.post_status,
                np.create_date,
                COALESCE(json_agg(json_build_object(
                    'file_id', pnm.id,
                    'file_path', file_path(pfse.storage_engine_id, '/member/file'),
                    'file_size', pfse.file_size_bytes,
                    'mime_type', pfse.mime_type
                )) FILTER (WHERE pnm.id IS NOT NULL), '[]') AS attachments
              FROM news_post as np
              LEFT OUTER JOIN member as post_creator ON post_creator.id = np.member_id
              LEFT OUTER JOIN member_profile as post_creator_profile ON post_creator_profile.member_id = np.member_id
              LEFT OUTER JOIN file_storage_engine as post_creator_avatar ON post_creator_avatar.id = post_creator_profile.profile_picture_storage_id
              LEFT OUTER JOIN news_media as pnm ON pnm.news_topic_id = np.news_topic_id AND pnm.news_post_id = np.id
              LEFT OUTER JOIN file_storage_engine AS pfse ON pnm.news_file_id = pfse.id
              GROUP BY
                np.id,
                np.news_topic_id,
                np.member_id,
                post_creator.first_name,
                post_creator.last_name,
                post_creator_avatar.storage_engine_id,
                np.post_content,
                np.post_status,
                np.create_date
              ORDER BY
                np.create_date ASC
            ) as reply on reply.news_topic_id = nt.id
            {'WHERE nt.member_id in %s' if len(members) > 0 else ''}
            GROUP BY
                nt.id,
                nt.topic_content,
                nt.create_date,
                nt.member_id,
                topic_creator.first_name,
                topic_creator.last_name,
                topic_creator_avatar.storage_engine_id
            ORDER BY
                nt.create_date DESC
        """)

        params = []
        if len(members) > 0:
            params.append(tuple(members))

        countQuery = f"""
            SELECT
                COUNT(DISTINCT nt.id)
            FROM news_topic as nt
            {'WHERE nt.member_id in %s' if len(members) > 0 else ''}
        """
        cls.source.execute(countQuery, tuple(params))

        count = 0
        if cls.source.has_results():
            (count,) = cls.source.cursor.fetchone()

        if count > 0 and page_size and page_number >= 0:
            query += """LIMIT %s OFFSET %s"""
            offset = 0
            if page_number > 0:
                offset = page_number * page_size
            params = params + (page_size, offset)

        topics = []
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (
                topic_id,
                topic_content,
                create_date,
                member_id,
                first_name,
                last_name,
                amera_avatar_url,
                attachments,
                replies
            ) in cls.source.cursor:
                topic = {
                    "topic_id": topic_id,
                    "topic_content": topic_content,
                    "create_date": create_date,
                    "member_id": member_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "amera_avatar_url": amera_avatar_url,
                    "attachments": attachments,
                    "replies": replies
                }

                topics.append(topic)
        
        return {
            "topics": topics,
            "count": count
        }
    
    @classmethod
    def get_topic(cls, topic_id):

        query = """
            SELECT
                nt.id as topic_id,
                nt.topic_content,
                nt.create_date,
                nt.member_id,
                topic_creator.first_name,
                topic_creator.last_name,
                topic_creator_avatar.storage_engine_id as amera_avatar_url,
                COALESCE(json_agg(json_build_object(
                    'file_id', nm.id,
                    'file_path', file_path(fse.storage_engine_id, '/member/file'),
                    'file_size', fse.file_size_bytes,
                    'mime_type', fse.mime_type
                )) FILTER (WHERE nm.id IS NOT NULL), '[]') AS attachments,
                COALESCE(json_agg(reply.*) FILTER (WHERE reply.post_id IS NOT NULL), '[]') AS replies
            FROM news_topic as nt
            LEFT OUTER JOIN member as topic_creator ON topic_creator.id = nt.member_id
            LEFT OUTER JOIN member_profile as topic_creator_profile ON topic_creator_profile.member_id = nt.member_id
            LEFT OUTER JOIN file_storage_engine as topic_creator_avatar ON topic_creator_avatar.id = topic_creator_profile.profile_picture_storage_id
            LEFT OUTER JOIN news_media as nm ON nm.news_topic_id = nt.id AND nm.news_post_id IS NULL
            LEFT OUTER JOIN file_storage_engine AS fse ON nm.news_file_id = fse.id
            LEFT OUTER JOIN (
              SELECT
                np.id as post_id,
                np.news_topic_id,
                np.member_id,
                post_creator.first_name,
                post_creator.last_name,
                file_path(post_creator_avatar.storage_engine_id, '/member/file') as amera_avatar_url,
                np.post_content,
                np.post_status,
                np.create_date,
                COALESCE(json_agg(json_build_object(
                    'file_id', pnm.id,
                    'file_path', file_path(pfse.storage_engine_id, '/member/file'),
                    'file_size', pfse.file_size_bytes,
                    'mime_type', pfse.mime_type

                )) FILTER (WHERE pnm.id IS NOT NULL), '[]') AS attachments
              FROM news_post as np
              LEFT OUTER JOIN member as post_creator ON post_creator.id = np.member_id
              LEFT OUTER JOIN member_profile as post_creator_profile ON post_creator_profile.member_id = np.member_id
              LEFT OUTER JOIN file_storage_engine as post_creator_avatar ON post_creator_avatar.id = post_creator_profile.profile_picture_storage_id
              LEFT OUTER JOIN news_media as pnm ON pnm.news_topic_id = np.news_topic_id AND pnm.news_post_id = np.id
              LEFT OUTER JOIN file_storage_engine AS pfse ON pnm.news_file_id = pfse.id
              GROUP BY
                np.id,
                np.news_topic_id,
                np.member_id,
                post_creator.first_name,
                post_creator.last_name,
                post_creator_avatar.storage_engine_id,
                np.post_content,
                np.post_status,
                np.create_date
              ORDER BY
                np.create_date ASC
            ) as reply on reply.news_topic_id = nt.id
            WHERE
                nt.id = %s
            GROUP BY
                nt.id,
                nt.topic_content,
                nt.create_date,
                nt.member_id,
                topic_creator.first_name,
                topic_creator.last_name,
                topic_creator_avatar.storage_engine_id
          """

        params = (topic_id,)

        cls.source.execute(query, params)

        if cls.source.has_results():
            (
                topic_id,
                topic_content,
                create_date,
                member_id,
                first_name,
                last_name,
                amera_avatar_url,
                attachments,
                replies
            ) = cls.source.cursor.fetchone()

            topic = {
                "topic_id": topic_id,
                "topic_content": topic_content,
                "create_date": create_date,
                "member_id": member_id,
                "first_name": first_name,
                "last_name": last_name,
                "amera_avatar_url": amera_avatar_url,
                "attachments": attachments,
                "replies": replies
            }

            return topic
        
        return None

    @classmethod
    def create_post(cls, topic_id, member_id, content, commit=True):
        query = """INSERT INTO news_post 
            (news_topic_id, member_id, post_content)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        params = (topic_id, member_id, content)
        try:
            cls.source.execute(query, params)
            post_id = cls.source.get_last_row_id()

            if commit:
                cls.source.commit()
            return post_id

        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    @classmethod
    def get_post(cls, post_id):
        query = """
            SELECT 
                np.id as post_id,
                np.news_topic_id,
                np.member_id,
                member.first_name,
                member.last_name,
                file_storage_engine.storage_engine_id as amera_avatar_url,
                np.post_content,
                np.create_date,
                COALESCE(json_agg(json_build_object(
                        'file_id', nm.id,
                        'file_path', file_path(fse.storage_engine_id, '/member/file'),
                        'file_size', fse.file_size_bytes,
                        'mime_type', fse.mime_type
                )) FILTER (WHERE nm.id IS NOT NULL), '[]') AS attachments
            FROM news_post np
            LEFT JOIN member ON member.id = member_id
            LEFT JOIN member_profile ON member.id = member_profile.member_id
            LEFT JOIN file_storage_engine ON file_storage_engine.id = member_profile.profile_picture_storage_id
            LEFT OUTER JOIN news_media as nm ON nm.news_post_id = np.id
            LEFT OUTER JOIN file_storage_engine AS fse ON nm.news_file_id = fse.id
            WHERE np.id = %s
            GROUP BY
                np.id,
                np.news_topic_id,
                np.member_id,
                member.first_name,
                member.last_name,
                file_storage_engine.storage_engine_id,
                np.post_content,
                np.create_date
        """
        params = (post_id,)
        try:
            cls.source.execute(query, params)
            if cls.source.has_results():
                (
                    post_id,
                    news_topic_id,
                    member_id,
                    first_name,
                    last_name,
                    amera_avatar_url,
                    post_content,
                    create_date,
                    attachments    
                ) = cls.source.cursor.fetchone()

                post = {
                    "post_id": post_id,
                    "news_topic_id": news_topic_id,
                    "member_id": member_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "amera_avatar_url": amerize_url(amera_avatar_url),
                    "post_content": post_content,
                    "create_date": create_date,
                    "attachments": attachments
                }

                return post
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

