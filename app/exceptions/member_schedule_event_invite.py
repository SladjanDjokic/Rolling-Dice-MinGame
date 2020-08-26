import falcon


# ------------
# Application Errors
# ------------

# ------------
# HTTP Errors
# ------------
# HTTP Response Error to throw when a setting is not found
class ScheduleEventInviteNotFound(falcon.HTTPNotFound):
    def __init__(self, eventinvite):
        title = "Schedule Event Invite Not Found",
        description = "The scheduled event invite for {} was not found".format(eventinvite)
        super().__init__(description=description)
        self._event = event

class ScheduleEventInviteAddingFailed(falcon.HTTPUnprocessableEntity):
    def __init__(self):
        title = "Adding Schedule Event Invite Failed"
        description = "Adding Schedule Event Invite Failed"
        super().__init__(title=title, description=description)

    def to_dict(self, obj_type=dict):
        result = super().to_dict(obj_type)
        result["success"] = False
        return result
