import uuid
import falcon
import app.util.json as json
import app.util.request as request
from app.da.session import SessionDA
from app.exceptions.session import SessionExistsError


class MemberLogoutResource(object):

    auth = {
        'exempt_methods': ['POST']
    }

    def on_post(self, req, resp):

        (username, session_id) = request.get_json_or_form(
            "username", "session_id", req=req)

        if not username or not session_id:
            raise falcon.HTTPError("400",
                                   title="Unauthorized Actions",
                                   description="You are not allowed to logout this session!")

        while True:
            try:
                SessionDA.delete_session(
                    session_id
                )
                break
            except SessionExistsError:
                continue

        resp.body = json.dumps({
        })

    def on_get(self, req, resp):
        resp.body = json.dumps({
        })
