import logging
import falcon
import app.util.json as json
import app.util.request as request
from app.util.auth import check_session

from app.da.page_settings import PageSettingsDA

logger = logging.getLogger(__name__)


class PageSettingsResource(object):
    @check_session
    def on_get(self, req, resp):
        try:
            member_id = req.context.auth['session']['member_id']
            result = PageSettingsDA().get_member_page_settings(member_id)

            if result:
                resp.body = json.dumps({
                    'success': True,
                    'data': result,
                    'message': "Page Settings loaded successfully."
                }, default_parser=json.parser)
            else:
                resp.body = json.dumps({
                    'success': False,
                    'data': [],
                    'message': "No result"
                }, default_parser=json.parser)

        except:
            logger.exception('Failed to get member page settings.')
            resp.status = falcon.HTTP_500

    @check_session
    def on_post(self, req, resp):
        try:
            (page_type, view_type, page_size, sort_order) = request.get_json_or_form(
                "page_type", "view_type", "page_size", "sort_order", req=req)

            member_id = req.context.auth['session']['member_id']

            data = PageSettingsDA().create_member_page_settings(member_id, page_type, view_type, page_size, sort_order)

            if data:
                resp.body = json.dumps({
                    'success': True,
                    'data': data,
                    'message': "Page Settings created successfully."
                }, default_parser=json.parser)
            else:
                resp.body = json.dumps({
                    'success': False,
                    'data': {},
                    'message': "Failed to create page settings"
                }, default_parser=json.parser)

        except:
            logger.exception('Failed to create member page settings.')
            resp.status = falcon.HTTP_500


    @check_session
    def on_put(self, req, resp):
        member_id = req.context.auth['session']['member_id']
        try:
            (id, page_type, view_type,
                page_size, sort_order) = request.get_json_or_form(
                "id", "page_type", "view_type",
                "page_size", "sort_order", req=req)

            data = PageSettingsDA().update_member_page_settings(
                id, member_id, page_type, view_type, page_size, sort_order)

            if data:
                resp.body = json.dumps({
                    'success': True,
                    'data': data,
                    'message': "Page Settings updated successfully."
                }, default_parser=json.parser)
            else:
                resp.body = json.dumps({
                    'success': False,
                    'data': {},
                    'message': "Failed to update page settings"
                }, default_parser=json.parser)

        except:
            logger.exception('Failed to update member page settings.')
            resp.status = falcon.HTTP_500
