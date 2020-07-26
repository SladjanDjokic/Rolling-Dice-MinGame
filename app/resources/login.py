import uuid
import falcon
import app.util.json as json

from datetime import datetime, timedelta, timezone

from app.config import settings
import app.util.request as request
from app.util.session import set_session_cookie
from app.da.session import SessionDA
from app.exceptions.session import SessionExistsError


class MemberLoginResource(object):

    auth = {
        'exempt_methods': ['POST']
    }

    def on_post(self, req, resp):

        (username, password) = request.get_json_or_form(
            "username", "password", req=req)

        if not username or not password:
            raise falcon.HTTPError("400",
                                   title="Invalid Login",
                                   description="No Login Data Sent")

        member = SessionDA.auth(username, password)

        if not member:
            raise falcon.HTTPUnauthorized(title="Invalid Login",
                                          description="Invalid credentials")

        expiration_seconds = settings.get("web.session_expiration")
        expiration_datetime = datetime.now(timezone.utc) + timedelta(
            seconds=expiration_seconds
        )

        # TODO: Refactor with a better pattern (one or the other):
        # * pregenerated session_id keys
        # * generate session_id keys from username, salts, etc
        while True:
            try:
                session_id = uuid.uuid4().hex
                SessionDA.create_session(
                    member, session_id, expiration_datetime
                )
                break
            except SessionExistsError:
                continue

        set_session_cookie(resp, session_id, expiration_datetime)

        resp.body = json.dumps({
            "session_id": session_id
        })

    def on_get(self, req, resp):
        resp.body = json.dumps({
            "session": req.context
        })
