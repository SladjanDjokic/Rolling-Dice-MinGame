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


# Application error to throw when the session is forbidden of access,
class ForbiddenSessionError (Exception):
    pass


# ------------
# HTTP Errors
# ------------
# HTTP Response Error to throw when credentials supplied are invalid
class InvalidLogin(falcon.HTTPBadRequest):
    def __init__(self):
        title = "Invalid sign in attempt"
        description = "There was a problem processing your sign in information"
        super().__init__(title=title, description=description)


# HTTP Response Error to throw when credentials supplied are invalid
class InvalidSession(falcon.HTTPBadRequest):
    def __init__(self):
        title = "Referenced session is invalid"
        description = "There was a problem processing your request with the given session"
        super().__init__(title=title, description=description)


# HTTP Response Error to throw when a user is not found
class UnauthorizedLogin(falcon.HTTPUnauthorized):
    def __init__(self):
        title = "Sign in is invalid"
        description = "There was a problem validating your sign in credentials"
        super().__init__(title=title, description=description)


# HTTP Response Error to throw when a user is not found
class UnauthorizedSession(falcon.HTTPUnauthorized):
    def __init__(self):
        title = "Session is invalid"
        description = "Your session is no longer valid. Please sign in again"
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
