import logging
from datetime import timezone, datetime
from uuid import UUID

import app.util.json as json
import app.util.request as request
from app.util.auth import check_session
from app import settings
from app.da.file_sharing import FileStorageDA
from app.da.stream import StreamMediaDA, StreamCategoryDA, StreamTypeDA

from app.util.filestorage import amerize_url

logger = logging.getLogger(__name__)


class StreamResource(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.create_event_attachment'),
                                    "topic": settings.get('kafka.topics.calendar')
                                    },
                           "GET": {"event_type": settings.get('kafka.event_types.delete.delete_event_attachment'),
                                      "topic": settings.get('kafka.topics.calendar')
                                      },
                           }

    @check_session
    def on_get(self, req, resp):
        member = req.context.auth["session"]
        member_id = member["member_id"]
        types = req.get_param_as_list("types")
        categories = req.get_param_as_list("categories")

        if len(types) == len(categories):
            data = StreamMediaDA.get_stream_medias(member_id, types, categories)
        else:
            data = None

        if data is not None:
            resp.body = json.dumps({
                "data": data,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Could not get video file",
                "success": False
            }, default_parser=json.parser)

    @check_session
    def on_post(self, req, resp):
        file = req.get_param("file")
        title = req.get_param("title")
        description = req.get_param("description")
        category = req.get_param("category")
        type = req.get_param("type")
        thumbnail = req.get_param("thumbnail")
        duration = req.get_param("duration")
        member = req.context.auth["session"]
        member_id = member["member_id"]

        storage_file_id = FileStorageDA().put_file_to_storage(file)

        # thumbnail
        thumbnail_storage_file_id = FileStorageDA().put_file_to_storage(thumbnail)

        # save stream media
        file_data = StreamMediaDA.create_stream_media(
            member_id, title, description, category, storage_file_id, type, thumbnail_storage_file_id, duration
        )

        file_detail = FileStorageDA().get_file_detail(member, storage_file_id)
        thumbnail_detail = FileStorageDA().get_file_detail(member, thumbnail_storage_file_id)

        if file_data is not None:
            file_data['video_url'] = amerize_url(file_detail['file_location'])
            file_data['thumbnail_url'] = amerize_url(thumbnail_detail['file_location'])
            file_data['email'] = file_detail['member_email']
            file_data['first_name'] = file_detail['member_first_name']
            file_data['last_name'] = file_detail['member_last_name']

            resp.body = json.dumps({
                "data": file_data,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Could not save file",
                "success": False
            }, default_parser=json.parser)

    @check_session
    def on_delete(self, req, resp, id):
        
        deleted_id = StreamMediaDA().update_stream_media_status(id, 'delete')

        if deleted_id is not None:
            resp.body = json.dumps({
                "data": deleted_id,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Could not delete video file",
                "success": False
            }, default_parser=json.parser)

    @check_session
    def on_put(self, req, resp, id):
        title = req.get_param("title")
        description = req.get_param("description")
        category = req.get_param("category")
        type = req.get_param("type")
        
        data = StreamMediaDA().update_stream_media_info(id, title, type, category, description)

        if data is not None:
            resp.body = json.dumps({
                "data": data,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Could not Update video info",
                "id": id,
                "title": title,
                "success": False
            }, default_parser=json.parser)


class StreamCategoryResource(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.create_event_attachment'),
                                    "topic": settings.get('kafka.topics.calendar')
                                    },
                           "GET": {"event_type": settings.get('kafka.event_types.delete.delete_event_attachment'),
                                      "topic": settings.get('kafka.topics.calendar')
                                      },
                           }

    @check_session
    def on_get(self, req, resp):

        data = StreamCategoryDA.get_stream_category()

        if data is not None:
            resp.body = json.dumps({
                "data": data,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Could not get categories",
                "success": False
            }, default_parser=json.parser)


class StreamTypeResource(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.create_event_attachment'),
                                    "topic": settings.get('kafka.topics.calendar')
                                    },
                           "GET": {"event_type": settings.get('kafka.event_types.delete.delete_event_attachment'),
                                      "topic": settings.get('kafka.topics.calendar')
                                      },
                           }

    @check_session
    def on_get(self, req, resp):

        data = StreamTypeDA.get_stream_types()

        if data is not None:
            resp.body = json.dumps({
                "data": data,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Could not get types",
                "success": False
            }, default_parser=json.parser)