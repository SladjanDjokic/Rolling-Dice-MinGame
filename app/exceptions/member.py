import falcon


# ------------
# Application Errors
# ------------

# ------------
# HTTP Errors
# ------------
# HTTP Response Error to throw when a user is not found
class MemberNotFound(falcon.HTTPNotFound):
    def __init__(self, member):
        title="Member Not Found",
        description="The Member {} was not found".format(member)
        super().__init__(description=description)
        self._member = member


# HTTP Response Error to throw when an invite is duplicate
class MemberExists(falcon.HTTPConflict):

    def __init__(self, email):
        description = (
            'Member already exists'
        )
        super().__init__(description=description)
        self._email = email

    def to_dict(self, obj_type=dict):
        result = super().to_dict(obj_type)
        result["success"] = False
        result["exists"] = True
        result["email"] = self._email
        return result

# HTTP Response Error to throw when member data missing
class MemberDataMissing(falcon.HTTPUnprocessableEntity):

    def __init__(self):
        title = "Missing information"
        description = "Please provide required information"
        super().__init__(title=title, description=description)

    def to_dict(self, obj_type=dict):
        result = super().to_dict(obj_type)
        result["success"] = False
        return result