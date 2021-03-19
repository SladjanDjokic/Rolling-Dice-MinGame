import logging
from app.util.auth import check_session
import app.util.json as json
import app.util.request as request
from app.da.forum import ForumDA
from app.da.group import GroupDA
from app.da.file_sharing import FileStorageDA
from operator import itemgetter

logger = logging.getLogger(__name__)


class ForumResource(object):
    @check_session
    def on_post(self, req, resp, group_id=None):
        member_id = req.context.auth['session']['member_id']
        try:
            (title, content, cover_image, attachments,) = request.get_json_or_form(
                "title", "content", "cover_image", "attachments", req=req)
            # del(req.env['wsgi.file_wrapper'])

            cover_image_file_id = None
            if cover_image is not None:
                cover_image_file_id = FileStorageDA().put_file_to_storage(cover_image)

            topic_id = ForumDA.add_new_topic(group_id, member_id, title, content, cover_image_file_id)

            attachments = int(attachments)

            for x in range(attachments):
                file = req.get_param(f"file_{x}")
                media_file_id = FileStorageDA().put_file_to_storage(file)
                ForumDA.add_topic_attachment(topic_id, media_file_id)

            topic = ForumDA.get_topic(topic_id)

            resp.body = json.dumps({
                "topic": topic,
                "success": True,
                "description": "Topic was created successfully",
            }, default_parser=json.parser)
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err
    
    @check_session
    def on_get(self, req, resp, group_id=None):
        member_id = req.context.auth['session']['member_id']
        try:

            search_key = req.get_param('search_key') or ''
            page_size = req.get_param_as_int('page_size')
            page_number = req.get_param_as_int('page_number')
            
            result = ForumDA.get_topics(group_id, search_key, page_size, page_number)
            resp.body = json.dumps({
                "topics": result['topics'],
                "count": result['count'],
                "success": True,
                "description": "Topic data fetched successfully",
            }, default_parser=json.parser)
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err
    
    @check_session
    def on_get_detail(self, req, resp, topic_id=None):
        member_id = req.context.auth['session']['member_id']
        try:
            
            topic = ForumDA.get_topic_detail(topic_id)
            posts = ForumDA.get_topic_posts(topic_id)
            resp.body = json.dumps({
                "topic": topic,
                "posts": posts,
                "success": True,
                "description": "Topic data fetched successfully",
            }, default_parser=json.parser)
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err
    
    @check_session
    def on_post_post(self, req, resp):
        member_id = req.context.auth['session']['member_id']
        try:
            (topic_id, post_id, content, ) = request.get_json_or_form(
                "topic_id", "post_id", "content", req=req) 

            post_id = ForumDA.create_post(topic_id, post_id, member_id, content)
            post = ForumDA.get_post(post_id)

            resp.body = json.dumps({
                "post": post,
                "success": True,
                "description": "Post data created successfully",
            }, default_parser=json.parser)
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    @check_session
    def on_put_like(self, req, resp, post_id):
        member_id = req.context.auth['session']['member_id']
        try:
            find = ForumDA.find_member_like(post_id, member_id)
            if find == 1:
                resp.body = json.dumps({
                    "success": False,
                }, default_parser=json.parser)
            else:
                ForumDA.like_post(post_id, member_id)
                resp.body = json.dumps({
                    "success": True,
                }, default_parser=json.parser)

        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err