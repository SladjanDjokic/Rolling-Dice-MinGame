import logging
from app.util.auth import check_session
import app.util.json as json
import app.util.request as request
from app.da.newsfeeds import NewsFeedsDA
from app.da.member import MemberContactDA
from app.da.file_sharing import FileStorageDA
from operator import itemgetter

logger = logging.getLogger(__name__)


class NewsFeedsResource(object):
    @check_session
    def on_post(self, req, resp):
        member_id = req.context.auth['session']['member_id']
        try:
            (content, attachments,) = request.get_json_or_form(
                "content", "attachments", req=req)

            topic_id = NewsFeedsDA.add_new_topic(member_id, content)

            attachments = int(attachments)

            for x in range(attachments):
                file = req.get_param(f"file_{x}")
                media_file_id = FileStorageDA().put_file_to_storage(file)
                NewsFeedsDA.add_topic_attachment(topic_id, media_file_id)

            topic = NewsFeedsDA.get_topic(topic_id)

            resp.body = json.dumps({
                "topic": topic,
                "success": True,
                "description": "Post was created successfully",
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

            page_size = req.get_param_as_int('page_size')
            page_number = req.get_param_as_int('page_number')

            member_contacts = MemberContactDA.get_member_contacts(member_id, None, None)
            member_ids = [member_id,]

            for member in member_contacts["contacts"]:
                member_ids.append(member["contact_member_id"])
            
            result = NewsFeedsDA.get_topics(member_ids, page_size, page_number)
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
    def on_post_post(self, req, resp, topic_id):
        member_id = req.context.auth['session']['member_id']
        try:
            (content, attachments) = request.get_json_or_form(
                "content", "attachments", req=req) 

            post_id = NewsFeedsDA.create_post(topic_id, member_id, content)

            attachments = int(attachments)

            for x in range(attachments):
                file = req.get_param(f"file_{x}")
                media_file_id = FileStorageDA().put_file_to_storage(file)
                NewsFeedsDA.add_post_attachment(topic_id, post_id, media_file_id)

            post = NewsFeedsDA.get_post(post_id)

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