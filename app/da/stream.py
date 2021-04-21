from app.util.security import SECURITY_EXCHANGE_OPTIONS
import logging
import datetime
from urllib import parse

from app.util.db import source
from app.util.config import settings
from app.util.filestorage import amerize_url


logger = logging.getLogger(__name__)


class StreamMediaDA(object):
    source = source

    @classmethod
    def create_stream_media(cls, member_id, title, description, category, stream_file_id, type, thumbnail, duration):
        try:
            types = [int(type)]

            query = """
                INSERT INTO stream_media (member_id, title, description, category, stream_file_id, type, thumbnail, duration)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """
            params = (member_id, title, description, category, stream_file_id, types, thumbnail, f'PT{duration}S')

            cls.source.execute(query, params)

            cls.source.commit()

            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                media = {
                    "id": result[0],
                    "user_id": result[1],
                    "title": result[2],
                    "description": result[3],
                    "type": result[10],
                    "create_date": result[8],
                    "update_date": result[9],
                    "category": result[11],
                    "duration": result[12]
                }
                return media

            return None
        except Exception as e:
            logger.debug(e)

    @classmethod
    def get_stream_medias(cls, member_id, types, categories):
        try:
            if len(types) < 1 and len(categories) < 1:
                return []
            where = ""
            params = ()
            for index, category in enumerate(categories):
                type = types[index]
                where += "(stream_media.category = %s AND stream_media.type @> %s::INTEGER[])"
                params += (category, [type],)
                if index < len(categories) - 1:
                    where += " OR "
                else:
                    where = f" AND ({where})"

            query = f"""
                SELECT
                    stream_media.id,
                    stream_media.title,
                    stream_media.description,
                    stream_media.category,
                    stream_media.type,
                    stream_media.create_date,
                    stream_media.update_date,
                    member.id as user_id,
                    member.email,
                    member.first_name,
                    member.last_name,
                    file_storage_engine.storage_engine_id as video_url,
                    stream_media.duration,
                    thumbnail.storage_engine_id as thumbnail_url
                FROM stream_media
                INNER JOIN member ON stream_media.member_id = member.id
                INNER JOIN file_storage_engine ON stream_media.stream_file_id = file_storage_engine.id
                LEFT JOIN file_storage_engine as thumbnail ON stream_media.thumbnail = thumbnail.id
                WHERE
                    stream_media.stream_status = 'active'
                    {where}
                GROUP BY
                    stream_media.id,
                    stream_media.title,
                    stream_media.description,
                    stream_media.category,
                    stream_media.type,
                    stream_media.create_date,
                    stream_media.update_date,
                    member.id,
                    member.email,
                    member.first_name,
                    member.last_name,
                    file_storage_engine.storage_engine_id,
                    thumbnail.storage_engine_id
                ORDER BY stream_media.update_date desc
                """

            medias = []
            cls.source.execute(query, params)

            if cls.source.has_results():
                for (
                    id,
                    title,
                    description,
                    category,
                    type,
                    create_date,
                    update_date,
                    user_id,
                    email,
                    first_name,
                    last_name,
                    video_url,
                    duration,
                    thumbnail_url
                ) in cls.source.cursor:
                    media = {
                        "id": id,
                        "title": title,
                        "description": description,
                        "category": category,
                        "type": type,
                        "create_date": create_date,
                        "update_date": update_date,
                        "user_id": user_id,
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "video_url": amerize_url(video_url),
                        "duration": duration,
                        "thumbnail_url": amerize_url(thumbnail_url)
                    }

                    medias.append(media)
            return medias
        except Exception as e:
            logger.debug(e)

    @classmethod
    def update_stream_media_status(cls, media_id, media_status):
        try:
            where = ""
            params = (media_status, media_id,)

            query = f"""
                UPDATE stream_media SET
                    stream_status = %s
                WHERE 
                    id = %s
                    {where}
                RETURNING id
            """
            cls.source.execute(query, params)
            cls.source.commit()

            id = None
            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                id = result[0]
            return id
        except Exception as e:
            logger.debug(e)

    @classmethod
    def update_stream_media_info(cls, id, title, type, category, description):
        try:
            params = (title, [int(type)], category, description, id )

            query = f"""
                UPDATE stream_media SET
                    title = %s,
                    type = %s,
                    category = %s,
                    description = %s
                WHERE 
                    id = %s
                RETURNING *
            """
            cls.source.execute(query, params)
            cls.source.commit()

            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                media = {
                    "id": result[0],
                    "user_id": result[1],
                    "title": result[2],
                    "description": result[3],
                    "type": result[10],
                    "create_date": result[8],
                    "update_date": result[9],
                    "category": result[11]
                }
                return media
            return None
        except Exception as e:
            logger.debug(e)


class StreamTypeDA(object):
    source = source

    @classmethod
    def get_stream_types(cls):
        try:

            query = """
                SELECT
                    id,
                    name
                FROM stream_media_type
                ORDER BY name
            """

            cls.source.execute(query, None)
            cls.source.commit()

            types = []

            if cls.source.has_results():
                for (
                    id,
                    name
                ) in cls.source.cursor:
                    type = {
                        "id": id,
                        "name": name
                    }

                    types.append(type)
            return types
        except Exception as e:
            logger.debug(e)


class StreamCategoryDA(object):
    source = source

    @classmethod
    def get_stream_category(cls):
        try:

            query = """
                SELECT
                    id,
                    name
                FROM stream_media_category
                ORDER BY id
            """

            cls.source.execute(query, None)
            cls.source.commit()

            categories = []

            if cls.source.has_results():
                for (
                    id,
                    name
                ) in cls.source.cursor:
                    category = {
                        "id": id,
                        "name": name
                    }

                    categories.append(category)
            return categories
        except Exception as e:
            logger.debug(e)