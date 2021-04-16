import logging
import datetime
from app.util.db import source, formatSortingParams
from app.util.filestorage import amerize_url

logger = logging.getLogger(__name__)


class ForumDA(object):
    source = source

    @classmethod
    def add_new_topic(cls, group_id, member_id, topic_title, topic_content, cover_image_file_id, commit=True):
        query = """INSERT INTO forum_topic 
            (group_id, member_id, topic_title, topic_content, cover_image_file_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        params = (group_id, member_id, topic_title, topic_content, cover_image_file_id)
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
    def add_topic_attachment(cls, forum_topic_id, media_file_id, commit=True):
        query = """INSERT INTO forum_media 
            (forum_topic_id, media_file_id)
            VALUES (%s, %s)
            RETURNING id
        """
        params = (forum_topic_id, media_file_id)
        
        try:
            cls.source.execute(query, params, debug_query=False)
            if commit:
                cls.source.commit()

        except Exception as e:
            logger.error(e, exc_info=True)
            return False
    
    @classmethod
    def add_post_attachment(cls, forum_topic_id, forum_post_id, media_file_id, commit=True):
        query = """INSERT INTO forum_media 
            (forum_topic_id, forum_post_id, media_file_id)
            VALUES (%s, %s, %s)
            RETURNING id
        """
        params = (forum_topic_id, forum_post_id, media_file_id)
        
        try:
            cls.source.execute(query, params, debug_query=False)
            if commit:
                cls.source.commit()

        except Exception as e:
            logger.error(e, exc_info=True)
            return False

    @classmethod
    def get_topics(cls, group_id, search_key, members=[], sort_params=None, page_size=None, page_number=None):
        sort_columns_string = 'ft.create_date DESC'
        forum_dict = {
            'create_date'    : 'ft.create_date'
        }

        logger.debug(f"members=>{members}")
        
        if sort_params:
            sort_columns_string = formatSortingParams(sort_params, forum_dict) or sort_columns_string

        query = (f"""
            SELECT
                ft.id as topic_id,
                ft.topic_title,
                ft.topic_content,
                ft.create_date,
                fse.storage_engine_id as cover_image_url,
                fse.file_size_bytes as cover_image_size,
                COUNT(DISTINCT fp.id) as comments
            FROM forum_topic as ft
            LEFT OUTER JOIN forum_post as fp ON ft.id = fp.forum_topic_id AND fp.parent_post_id is NULL
            LEFT OUTER JOIN file_storage_engine as fse ON fse.id = ft.cover_image_file_id
            WHERE
                group_id = %s
                {'AND ft.topic_title like %s' if search_key and len(search_key) > 0 else ''}
                {'AND fp.member_id in %s' if len(members) > 0 else ''}
            GROUP BY
                ft.id,
                ft.topic_title,
                ft.topic_content,
                ft.create_date,
                ft.cover_image_file_id,
                fse.storage_engine_id,
                file_size_bytes
            ORDER BY {sort_columns_string}
        """)
        like_search_key = """%{}%""".format(search_key)
        params = [group_id]
        if len(search_key) > 0:
            params.append(search_key)
        if len(members) > 0:
            params.append(tuple(members))

        countQuery = f"""
            SELECT
                COUNT(DISTINCT ft.id)
            FROM forum_topic as ft
            LEFT OUTER JOIN forum_post as fp ON ft.id = fp.forum_topic_id AND fp.parent_post_id is NULL
            WHERE
                group_id = %s
                {'AND ft.topic_title like %s' if search_key and len(search_key) > 0 else ''}
                {'AND fp.member_id in %s' if len(members) > 0 else ''}
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
                topic_title,
                topic_content,
                create_date,
                cover_image_url,
                cover_image_size,
                comments
            ) in cls.source.cursor:
                topic = {
                    "topic_id": topic_id,
                    "topic_title": topic_title,
                    "topic_content": topic_content,
                    "create_date": create_date,
                    "cover_image_url": amerize_url(cover_image_url),
                    "cover_image_size": cover_image_size,
                    "comments": comments
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
                ft.id as topic_id,
                ft.topic_title,
                ft.topic_content,
                ft.create_date,
                fse.storage_engine_id as cover_image_url,
                fse.file_size_bytes as cover_image_size,
                COUNT(DISTINCT fp.id) as comments
            FROM forum_topic as ft
            LEFT OUTER JOIN forum_post as fp ON ft.id = fp.forum_topic_id AND fp.parent_post_id is NULL
            LEFT OUTER JOIN file_storage_engine as fse ON fse.id = ft.cover_image_file_id
            WHERE
                ft.id = %s
            GROUP BY
                ft.id,
                ft.topic_title,
                ft.topic_content,
                ft.create_date,
                ft.cover_image_file_id,
                fse.storage_engine_id,
                file_size_bytes
        """
        params = (topic_id,)

        cls.source.execute(query, params)

        if cls.source.has_results():
            (
                topic_id,
                topic_title,
                topic_content,
                create_date,
                cover_image_url,
                cover_image_size,
                comments
            ) = cls.source.cursor.fetchone()

            topic = {
                "topic_id": topic_id,
                "topic_title": topic_title,
                "topic_content": topic_content,
                "create_date": create_date,
                "cover_image_url": amerize_url(cover_image_url),
                "cover_image_size": cover_image_size,
                "comments": comments
            }

            return topic
        
        return None

    @classmethod
    def get_topic_detail(cls, topic_id):
        query = """
            SELECT
                ft.id as topic_id,
                ft.topic_title,
                ft.topic_content,
                ft.member_id as member_id,
                ft.create_date,
                member.first_name as first_name,
                member.last_name as last_name,
                cover_image.storage_engine_id as cover_image_url,
                member_avatar.storage_engine_id as amera_avatar_url,
                member_profile.biography as biography,
                COALESCE(json_agg(json_build_object(
                    'forum_media_id', fm.id,
                    'forum_topic_id', fm.forum_topic_id,
                    'forum_post_id', fm.forum_post_id,
                    'file_path', file_path(fse.storage_engine_id, '/member/file'),
                    'file_size', fse.file_size_bytes
                )) FILTER (WHERE fm.id IS NOT NULL), '[]') AS attachments
            FROM forum_topic ft
            LEFT JOIN member ON member.id = ft.member_id
            LEFT JOIN member_profile ON member.id = member_profile.member_id
            LEFT OUTER JOIN file_storage_engine as cover_image ON cover_image.id = ft.cover_image_file_id
            LEFT OUTER JOIN file_storage_engine as member_avatar ON member_avatar.id = member_profile.profile_picture_storage_id
            LEFT OUTER JOIN forum_media as fm ON fm.forum_topic_id = ft.id AND fm.forum_post_id IS NULL
            LEFT OUTER JOIN file_storage_engine AS fse ON fm.media_file_id = fse.id
            WHERE ft.id = %s
            GROUP BY
                ft.id,
                ft.member_id,
                ft.create_date,
                member.first_name,
                member.last_name,
                cover_image.storage_engine_id,
                member_avatar.storage_engine_id,
                member_profile.biography
        """
        params = (topic_id,)
        
        cls.source.execute(query, params)
        if cls.source.has_results():
            (
                topic_id,
                topic_title,
                topic_content,
                member_id,
                create_date,
                first_name,
                last_name,
                cover_image_url,
                amera_avatar_url,
                biography,
                attachments
            ) = cls.source.cursor.fetchone()

            return {
                "topic_id": topic_id,
                "topic_title": topic_title,
                "topic_content": topic_content,
                "member_id": member_id,
                "create_date": create_date,
                "first_name": first_name,
                "last_name": last_name,
                "cover_image_url": amerize_url(cover_image_url),
                "amera_avatar_url": amerize_url(amera_avatar_url),
                "biography": biography,
                "attachments": attachments
            }

        return None

    @classmethod
    def get_topic_posts(cls, topic_id):
        query = """
            WITH RECURSIVE post_tree
                (post_id, forum_topic_id, parent_post_id, member_id, post_content, post_status, create_date, level )
            AS ( 
                SELECT
                    id as post_id, 
                    forum_topic_id, 
                    parent_post_id, 
                    member_id, 
                    post_content,
                    post_status,
                    create_date, 
                    1
                FROM forum_post
                WHERE parent_post_id is NULL AND forum_topic_id = %s 

                UNION ALL
                SELECT
                    fp.id as post_id, 
                    fp.forum_topic_id, 
                    fp.parent_post_id, 
                    fp.member_id, 
                    fp.post_content,
                    fp.post_status,
                    fp.create_date,
                    pt.level+1
                FROM forum_post fp, post_tree pt
                WHERE fp.parent_post_id = pt.post_id
            )
            SELECT
                post_tree.post_id,
                post_tree.forum_topic_id,
                post_tree.parent_post_id,
                post_tree.member_id,
                member.first_name,
                member.last_name,
                member_avatar.storage_engine_id as amera_avatar_url,
                post_tree.post_content,
                post_tree.post_status,
                post_tree.create_date,
                post_tree.level,
                COUNT(DISTINCT fpl.*) as likes,
                COALESCE(json_agg(json_build_object(
                    'forum_media_id', fm.id,
                    'forum_topic_id', fm.forum_topic_id,
                    'forum_post_id', fm.forum_post_id,
                    'file_path', file_path(fse.storage_engine_id, '/member/file'),
                    'file_size', fse.file_size_bytes
                )) FILTER (WHERE fm.id IS NOT NULL), '[]') AS attachments
            FROM post_tree
            LEFT JOIN member ON member.id = post_tree.member_id
            LEFT OUTER JOIN member_profile ON member_profile.member_id = member.id
            LEFT OUTER JOIN file_storage_engine as member_avatar ON member_avatar.id = member_profile.profile_picture_storage_id 
            LEFT OUTER JOIN forum_post_like as fpl ON post_tree.post_id = fpl.forum_post_id
            LEFT OUTER JOIN forum_media as fm ON fm.forum_topic_id = post_tree.forum_topic_id AND fm.forum_post_id = post_tree.post_id
            LEFT OUTER JOIN file_storage_engine AS fse ON fm.media_file_id = fse.id
            WHERE level > 0
            GROUP BY
                post_tree.post_id,
                post_tree.forum_topic_id,
                post_tree.parent_post_id,
                post_tree.member_id,
                member.first_name,
                member.last_name,
                member_avatar.storage_engine_id,
                post_tree.post_content,
                post_tree.post_status,
                post_tree.create_date,
                post_tree.level
            ORDER BY level, parent_post_id, create_date
        """
        params = (topic_id, )

        posts = []        
        cls.source.execute(query, params, debug_query=True)
        logger.debug("okay cool")
        if cls.source.has_results():
            for (
                    post_id,
                    forum_topic_id,
                    parent_post_id,
                    member_id,
                    first_name,
                    last_name,
                    amera_avatar_url,
                    post_content,
                    post_status,
                    create_date,
                    level,
                    likes,
                    attachments
            ) in cls.source.cursor:

                post = {
                    "post_id": post_id,
                    "forum_topic_id": forum_topic_id,
                    "parent_post_id": parent_post_id,
                    "member_id": member_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "amera_avatar_url": amerize_url(amera_avatar_url),
                    "post_content": post_content,
                    "post_status": post_status,
                    "create_date": create_date,
                    "level": level,
                    "likes": likes,
                    "attachments": attachments
                }

                posts.append(post)
        
        return posts

    @classmethod
    def create_post(cls, topic_id, parent_post_id, member_id, content, commit=True):
        query = """INSERT INTO forum_post 
            (forum_topic_id, parent_post_id, member_id, post_content)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """
        params = (topic_id, parent_post_id, member_id, content)
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
                fp.id as post_id,
                fp.forum_topic_id,
                fp.parent_post_id,
                fp.member_id,
                member.first_name,
                member.last_name,
                file_storage_engine.storage_engine_id as amera_avatar_url,
                fp.post_content,
                fp.create_date,
                COUNT(DISTINCT fpl.*) as likes,
                COALESCE(json_agg(json_build_object(
                        'forum_media_id', fm.id,
                        'forum_topic_id', fm.forum_topic_id,
                        'forum_post_id', fm.forum_post_id,
                        'file_path', file_path(fse.storage_engine_id, '/member/file'),
                        'file_size', fse.file_size_bytes
                    )) FILTER (WHERE fm.id IS NOT NULL), '[]') AS attachments
            FROM forum_post fp
            LEFT JOIN member ON member.id = member_id
            LEFT JOIN member_profile ON member.id = member_profile.member_id
            LEFT JOIN file_storage_engine ON file_storage_engine.id = member_profile.profile_picture_storage_id
            LEFT OUTER JOIN forum_post_like as fpl ON fp.id = fpl.forum_post_id
            LEFT OUTER JOIN forum_media as fm ON fm.forum_post_id = fp.id
            LEFT OUTER JOIN file_storage_engine AS fse ON fm.media_file_id = fse.id
            WHERE fp.id = %s
            GROUP BY
                fp.id,
                fp.forum_topic_id,
                fp.parent_post_id,
                fp.member_id,
                member.first_name,
                member.last_name,
                file_storage_engine.storage_engine_id,
                fp.post_content,
                fp.create_date
        """
        params = (post_id,)
        try:
            cls.source.execute(query, params)
            if cls.source.has_results():
                (
                    post_id,
                    forum_topic_id,
                    parent_post_id,
                    member_id,
                    first_name,
                    last_name,
                    amera_avatar_url,
                    post_content,
                    create_date,
                    likes,
                    attachments    
                ) = cls.source.cursor.fetchone()

                post = {
                    "post_id": post_id,
                    "forum_topic_id": forum_topic_id,
                    "parent_post_id": parent_post_id,
                    "member_id": member_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "amera_avatar_url": amerize_url(amera_avatar_url),
                    "post_content": post_content,
                    "create_date": create_date,
                    "likes": likes,
                    "attachments": attachments   
                }

                return post
        except Exception as e:
            logger.error(e, exc_info=True)
            return None

    @classmethod
    def find_member_like(cls, post_id, member_id):
        query = """
            SELECT COUNT(*)
            FROM forum_post_like
            WHERE forum_post_id = %s AND member_id = %s
        """
        params = (post_id, member_id)

        cls.source.execute(query, params)

        count = 0
        if cls.source.has_results():
            (count,) = cls.source.cursor.fetchone()

        return count

    @classmethod
    def like_post(cls, post_id, member_id):
        query = """
            INSERT INTO forum_post_like
            (forum_post_id, member_id)
            VALUES (%s, %s)
        """
        params = (post_id, member_id)

        cls.source.execute(query, params)
        cls.source.commit()

