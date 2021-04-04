import logging
from app.util.auth import check_session
import app.util.json as json
import app.util.request as request
import uuid
from app.da.password import PasswordDA
from app.da.file_sharing import FileStorageDA
from operator import itemgetter
import falcon

logger = logging.getLogger(__name__)


class PasswordResource(object):
    @check_session
    def on_post(self, req, resp):
        member_id = req.context.auth['session']['member_id']
        try:
            (name, website, type, username, password) = request.get_json_or_form(
                "name", "website", "type", "username", "password", req=req)
            # del(req.env['wsgi.file_wrapper'])

            icon = FileStorageDA.put_favicon(website)
            password_id = PasswordDA.add_new_password(member_id, name, website, type, username, password, icon)

            password = PasswordDA.get_password(password_id)

            resp.body = json.dumps({
                "data": password,
                "success": True,
                "description": "Password was saved successfully",
            }, default_parser=json.parser)
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err
    
    @check_session
    def on_get(self, req, resp):
        member_id = req.context.auth['session']['member_id']
        try:

            search_key = req.get_param('search_key') or ''
            page_size = req.get_param_as_int('page_size')
            page_number = req.get_param_as_int('page_number')

            result = PasswordDA.get_passwords(member_id, search_key, page_size, page_number)
            resp.body = json.dumps({
                "data": result['passwords'],
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
    def on_put_detail(self, req, resp, password_id):
        member_id = req.context.auth['session']['member_id']
        try:
            (name, website, type, username, password) = request.get_json_or_form(
                "name", "website", "type", "username", "password", req=req) 

            icon = FileStorageDA.put_favicon(website)
            PasswordDA.update_password(password_id, name, website, type, username, password, icon)
            password = PasswordDA.get_password(password_id)

            resp.body = json.dumps({
                "data": password,
                "success": True,
                "description": "Password was updated successfully",
            }, default_parser=json.parser)
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            })
            logger.exception(err)
            raise err

    @check_session
    def on_delete_detail(self, req, resp, password_id):
        member_id = req.context.auth['session']['member_id']
        try:
            PasswordDA.delete_password(password_id)
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

    # @check_session
    # def on_get_favicon(self, req, resp, password_id):
    #     member_id = req.context.auth['session']['member_id']
    #     try:
    #         password = PasswordDA.get_password(password_id)
    #         if password["icon"] is not None
    @check_session
    def on_get_favicon(self, req, resp, password_id):
        password = PasswordDA.get_password(password_id)
        s3_resp = FileStorageDA().favicon_stream_s3_file(password)
        resp.content_type = s3_resp['ContentType']
        resp.content_length = s3_resp['ContentLength']
        resp.status = falcon.HTTP_200
        resp.stream = s3_resp['Body']
