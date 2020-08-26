import falcon


# ------------
# Application Errors
# ------------

# ------------
# HTTP Errors
# ------------
# HTTP Response Error to throw when a setting is not found
class SchedulerSettingNotFound(falcon.HTTPNotFound):
    def __init__(self, setting):
        title = "Scheduler Setting Not Found",
        description = "The scheduler setting for {} was not found".format(setting)
        super().__init__(description=description)
        self._setting = setting

class SchedulerSettingSavingFailed(falcon.HTTPUnprocessableEntity):
    def __init__(self):
        title = "Scheduler Setting Failed"
        description = "Scheduler Setting Failed"
        super().__init__(title=title, description=description)

    def to_dict(self, obj_type=dict):
        result = super().to_dict(obj_type)
        result["success"] = False
        return result
