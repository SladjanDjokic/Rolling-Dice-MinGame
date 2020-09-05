import app.util.json as json
from app.util.session import get_session_cookie, validate_session
from app.exceptions.session import InvalidSessionError, UnauthorizedSession

from app.da.country import CountryCodeDA


class CountryCodeResource(object):
    @staticmethod
    def on_get(req, resp):
        # try:
        #     session_id = get_session_cookie(req)
        #     session = validate_session(session_id)
        #     group_leader_id = session["member_id"]
        # except InvalidSessionError as err:
        #     raise UnauthorizedSession() from err
        all_country_list = CountryCodeDA().get_all_country()
        resp.body = json.dumps({
            "country": all_country_list,
            "message": "All Group",
            "success": True
        }, default_parser=json.parser)
