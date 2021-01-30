import falcon


# ------------
# Application Errors
# ------------

# Application Error to throw when Member Data Exists
class ForgotMemberDataMissingError (Exception):
    pass


# Application error to throw when the member refrence is not present for forgot
class ForgotInvalidMemberError (Exception):
    pass


class ForgotDuplicateDataError (Exception):
    pass


# ------------
# HTTP Errors
# ------------
# HTTP Response Error to throw when a user is not found
class MemberNotFound(falcon.HTTPNotFound):
    def __init__(self, member):
        title = "Member Not Found",
        description = "The Member {} was not found".format(member)
        super().__init__(description=description)
        self._member = member


# HTTP Response Error to throw when a user is disabled/deactivated
class MemberDisabled(falcon.HTTPForbidden):
    def __init__(self):
        title = "403 Forbidden",
        description = "Your account is disabled"
        super().__init__(title=title, description=description)

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


# HTTP Response Error to throw when an member contact is duplicate
class MemberContactExists(falcon.HTTPConflict):

    def __init__(self, email):
        description = (
            'Contact already exists'
        )
        super().__init__(description=description)
        self._email = email


class MemberPasswordMismatch(falcon.HTTPUnprocessableEntity):

    def __init__(self):
        title = "Passwords do not match"
        description = "Please make sure the passwords match"
        super().__init__(title=title, description=description)

    def to_dict(self, obj_type=dict):
        result = super().to_dict(obj_type)
        result["success"] = False
        return result


class ForgotDataNotFound(falcon.HTTPNotFound):
    def __init__(self, forgot_key):
        title = "Forgot Key Not Found",
        description = "The Forgot Key {} was not found".format(forgot_key)
        super().__init__(description=description)
        self._forgot_key = forgot_key


class ForgotKeyExpired(falcon.HTTPGone):
    def __init__(self, forgot_key):
        title = "Forgot Key Expired",
        description = "The Forgot Key {} was expired.".format(forgot_key)
        super().__init__(description=description)
        self._forgot_key = forgot_key


class ForgotKeyConflict(falcon.HTTPConflict):
    def __init__(self):
        title = "Forgot Key Conflict"
        description = "Forgot Key Already Exist!"
        super().__init__(title=title, description=description)

    def to_dict(self, obj_type=dict):
        result = super().to_dict(obj_type)
        result["success"] = False
        return result


class ForgotPassEmailSystemFailure(falcon.HTTPInternalServerError):

    def __init__(self, email):
        title = "E-mail cannot be sent due to SMTP Server Errors"
        description = (
            "There is error when communicating with the E-Mail system. "
            "Please try to reset password later"
        )
        super().__init__(title=title, description=description)
        self._email = email

    def to_dict(self, obj_type=dict):
        result = super().to_dict(obj_type)
        result["success"] = False
        result["exists"] = True
        result["email"] = self._email
        return result

# HTTP Response Error to throw when forgot key is not present


class ForgotKeyMissing(falcon.HTTPNotFound):
    def __init__(self):
        title = "Member forgot key not present",
        description = "The Member forgot key is missing"
        super().__init__(title=title, description=description)


class PasswordsConflict(falcon.HTTPConflict):
    def __init__(self):
        title = "Passwords Conflict"
        description = "Current and new passwords should be differnet"
        super().__init__(title=title, description=description)

    def to_dict(self, obj_type=dict):
        result = super().to_dict(obj_type)
        result["success"] = False
        return result
