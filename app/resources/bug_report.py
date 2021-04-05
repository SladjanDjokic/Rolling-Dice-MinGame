from app.util.auth import check_session
import logging

import app.util.json as json
import app.util.request as request
from app.util.session import get_session_cookie, validate_session
from app.exceptions.session import InvalidSessionError, UnauthorizedSession

from app.da.bug_report import BugReportDA
from app.da.file_sharing import FileStorageDA, FileTreeDA

logger = logging.getLogger(__name__)


class BugReportResource(object):
    @check_session
    def on_post(self, req, resp):
        try:
            (
                description, redux_state, browser_info, file,
                file_name, file_size, file_iv, current_url
            ) = request.get_json_or_form(
                "description", "redux_state", "browser_info", "file",
                "file_name", "file_size", "file_iv", "current_url",
                req=req
            )
            member_id = req.context.auth["session"]["member_id"]

            referer_url = req.headers.get('REFERER') 

            if not current_url:
                current_url = referer_url

            member_file_id = None
            if file != '':
                storage_file_id = FileStorageDA().put_file_to_storage(file)
                member_file_id = FileTreeDA().create_member_file_entry(
                    file_id=storage_file_id,
                    file_name=file_name,
                    member_id=member_id,
                    status="available",
                    file_size_bytes=file_size,
                    iv=file_iv
                )

            report_id = BugReportDA.create(
                member_id, description, redux_state,
                member_file_id, browser_info, referer_url,
                current_url
            )

            if report_id:
                resp.body = json.dumps({
                    "success": True,
                    "id": report_id
                })
            else:
                resp.body = json.dumps({
                    "success": False,
                })
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

    @check_session
    def on_get(self, req, resp):
        try:
            get_all = req.get_param_as_bool('get_all')
            search_key = req.get_param('search_key') or ''
            page_size = req.get_param_as_int('page_size')
            page_number = req.get_param_as_int('page_number')
            sort_params = req.get_param('sort')
            member_id = req.get_param('member_id')

            if get_all and req.context.auth["session"]["user_type"] != 'administrator':
                raise falcon.HTTPForbidden(description="Not enough permissions")


            result = BugReportDA().get_global_user_bug_reports(search_key, page_size, page_number, sort_params, get_all, member_id)
            
            if result:
                resp.body = json.dumps({
                    'success': True,
                    'data': result['bug_reports'],
                    'count': result['count'],
                    'message': "Bug reports loaded successfully."
                }, default_parser=json.parser)
            else:
                resp.body = json.dumps({
                    'success': False,
                    'data': [],
                    'count': 0,
                    'message': "No result"
                }, default_parser=json.parser)

        except:
            logger.exception('Failed to bug report users.')
            resp.status = falcon.HTTP_500

class BugReportUsersResource(object):
    @check_session
    def on_get(self, req, resp):
        try:
            get_all = req.get_param_as_bool('get_all')
            if get_all and req.context.auth["session"]["user_type"] != 'administrator':
                raise falcon.HTTPForbidden(description="Not enough permissions")

            result = BugReportDA().get_bug_report_users()
            
            if result:
                resp.body = json.dumps({
                    'success': True,
                    'data': result,
                    'message': "Got Users."
                }, default_parser=json.parser)
            else:
                resp.body = json.dumps({
                    'success': False,
                    'data': [],
                    'message': "Failed to get Users!"
                }, default_parser=json.parser)

        except:
            logger.exception('Failed to bug report users.')
            resp.status = falcon.HTTP_500
            