import falcon


# ------------
# Application Errors
# ------------
# Application Error to throw when Member Avatar is not found
class MemberAvatarNotFoundError (Exception):
    pass


# ------------
# HTTP Errors
# ------------
# HTTP Response Error to throw when a user is not found
class MemberAvatarNotFound(falcon.HTTPNotFound):
    def __init__(self, member_id):
        title = "Member Avatar Not Found",
        description = f"The Avatar for member: {member_id} was not found"
        super().__init__(description=description)
        self._member = member_id
