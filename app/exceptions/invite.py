import falcon
import re

# ------------
# Application Errors
# ------------


# Application Error to throw when an Invite Exists
class InviteExistsError (Exception):
    pass


# Application Error to throw when an Invite Exists
class InviteDataMissingError (Exception):
    pass


# Application Error to throw when an Invite Exists
class InviteDataCorruptedError (Exception):
    pass


# Application error to throw when the inviter is not in the members table
class InviteInvalidInviterError (Exception):
    pass


# ------------
# HTTP Errors
# ------------
# HTTP Response Error to throw when invite key is not present
class InviteDataMissing(falcon.HTTPUnprocessableEntity):

    re_column_name = re.compile("null value in column[\"](.+)[\"]")

    def __init__(self, invite_data):
        title = "Invite missing information"
        description = "Invite is missing required information"

        super().__init__(title=title, description=description)

        self._fields = invite_data

    def to_dict(self, obj_type=dict):
        result = super().to_dict(obj_type)
        result["fields"] = self._fields
        return result


# HTTP Response Error to throw when invite key is not present
class InviteKeyMissing(falcon.HTTPNotFound):
    def __init__(self):
        title = "Member invite not present",
        description = "The Member invite key is missing"
        super().__init__(title=title, description=description)


# HTTP Response Error to throw when an invite is not found
class InviteNotFound(falcon.HTTPNotFound):
    def __init__(self, invite_key):
        title = "Invite Key Not Found"
        description = "The Key {} is no longer available".format(invite_key)
        super().__init__(title=title, description=description)
        self._invite_key = invite_key


# HTTP Response Error to throw when an invite has expired
class InviteExpired(falcon.HTTPGone):
    def __init__(self, invite_key):
        title = "Invite past expiration date"
        description = (
            "Invite is no longer a valid, please request a new invite"
        )
        super().__init__(title=title, description=description)


# HTTP Response Error to throw when an invite is duplicate
class InviteExists(falcon.HTTPConflict):

    def __init__(self, email):
        title = "E-mail already invited"
        description = (
            "The person you are already trying "
            "to invite has already been invited"
        )
        super().__init__(title=title, description=description)
        self._email = email

    def to_dict(self, obj_type=dict):
        result = super().to_dict(obj_type)
        result["success"] = False
        result["exists"] = True
        result["email"] = self._email
        return result


# HTTP Response Error to throw when an invite is duplicate
class InviteInvalidInviter(falcon.HTTPUnprocessableEntity):

    def __init__(self, inviter_member_id):
        title = "Invite originator invalid"
        description = (
            "Invite requested for someone "
            "that does not exist: member_id({})"
        ).format(inviter_member_id)

        super().__init__(title=title, description=description)
        self._inviter_member_id = inviter_member_id


class InviteEmailSystemFailure(falcon.HTTPInternalServerError):

    def __init__(self, email):
        title = "E-mail cannot be sent due to SMTP Server Errors"
        description = (
            "There are errors communicating with the E-Mail system. "
            "Please try to invite this person again at a later"
        )
        super().__init__(title=title, description=description)
        self._email = email

    def to_dict(self, obj_type=dict):
        result = super().to_dict(obj_type)
        result["success"] = False
        result["exists"] = True
        result["email"] = self._email
        return result
