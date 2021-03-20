import falcon


class ProjectMemberNotFound(falcon.HTTPBadRequest):
    def __init__(self):
        title = "Project member not found"
        description = "There was a problem validating your participation in this project"
        super().__init__(title=title, description=description)


class NotEnoughPriviliges(falcon.HTTPBadRequest):
    def __init__(self):
        title = "Not enough project privileges"
        description = "There was a problem validating your project privileges for this action"
        super().__init__(title=title, description=description)


class ContractDoesNotBelongProject(falcon.HTTPBadRequest):
    def __init__(self):
        title = "Specified contract does not belong to this project"
        description = "There was a problem validating the reference of the specified contract to this project"
        super().__init__(title=title, description=description)
