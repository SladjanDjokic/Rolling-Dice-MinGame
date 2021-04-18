import falcon

class NotEnoughCompanyPrivileges(falcon.HTTPBadRequest):
    def __init__(self):
        title = "Not enough company privileges"
        description = "There was a problem validating your Company role privliges for this action"
        super().__init__(title=title, description=description)