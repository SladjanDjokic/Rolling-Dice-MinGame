from app.util.db import source


class RolesDA(object):
    source = source

    @classmethod
    def get_all_roles(cls):
        roles_list = list()
        get_all_roles_query = ("""
            SELECT
                id,
                name
            FROM role
        """)
        get_all_roles_params = (None, )
        cls.source.execute(get_all_roles_query, get_all_roles_params)
        if cls.source.has_results():
            for (
                    id,
                    name
            ) in cls.source.cursor:
                role = {
                    "id": id,
                    "name": name
                }
                roles_list.append(role)
        return roles_list
