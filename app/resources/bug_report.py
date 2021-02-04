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
