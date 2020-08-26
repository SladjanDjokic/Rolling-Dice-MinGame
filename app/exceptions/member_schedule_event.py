import falcon


# ------------
# Application Errors
# ------------

# ------------
# HTTP Errors
# ------------
# HTTP Response Error to throw when a setting is not found
class ScheduleEventNotFound(falcon.HTTPNotFound):
    def __init__(self, event):
        title = "Schedule Event Not Found",
        description = "The scheduled event for {} was not found".format(event)
        super().__init__(description=description)
        self._event = event

class ScheduleEventAddingFailed(falcon.HTTPUnprocessableEntity):
    def __init__(self):
        title = "Adding Schedule Event Failed"
        description = "Adding Schedule Event Failed"
        super().__init__(title=title, description=description)

    def to_dict(self, obj_type=dict):
        result = super().to_dict(obj_type)
        result["success"] = False
        return result
