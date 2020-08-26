import falcon


# ------------
# Application Errors
# ------------
# Application Error to throw when a Session Key Exists
class SessionExistsError (Exception):
    pass


# Application error to throw when the session doesn't exist,
# has expired, is invalid, or no session key passed
class InvalidSessionError (Exception):
    pass


# ------------
# HTTP Errors
# ------------
# HTTP Response Error to throw when a user is not found
class UnauthorizedSession(falcon.HTTPUnauthorized):
    def __init__(self):
        title = "Session is invalid"
        description = "This is no longer a valid session"
        super().__init__(title=title, description=description)

# ------------
# HTTP Errors
# ------------
# HTTP Response Error to throw when a permission is not allowed
class ForbiddenSession(falcon.HTTPForbidden):
    def __init__(self):
        title = "Session is invalid"
        description = "This is a session not allowed for the action"
        super().__init__(title=title, description=description)
