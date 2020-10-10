import app.util.json as json
from app.util.session import get_session_cookie, validate_session
from app.exceptions.session import InvalidSessionError, UnauthorizedSession

from app.da.country import CountryCodeDA


class CountryCodeResource(object):
    exempt_methods = ['GET']

    @staticmethod
    def on_get(req, resp):
        # try:
        #     session_id = get_session_cookie(req)
        #     session = validate_session(session_id)
        #     group_leader_id = session["member_id"]
        # except InvalidSessionError as err:
        #     raise UnauthorizedSession() from err

        # Will return countries that only have is_enabled = True
        active_country_list = CountryCodeDA().get_active_countries()
        resp.body = json.dumps({
            "data": active_country_list,
            "message": "Active countries",
            "success": True
        }, default_parser=json.parser)
