import app.util.json as json
from app.da.role import RolesDA


class RolesResource(object):
    @staticmethod
    def on_get(req, resp):
        all_roles = RolesDA().get_all_roles()
        resp.body = json.dumps({
            "role": all_roles,
            "message": "All roles list",
            "success": True
        }, default_parser=json.parser)
