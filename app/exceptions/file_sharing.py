import falcon


# ------------
# Application Errors
# ------------

# Application Error when unable to store file in storage
class FileStorageUploadError (Exception):
    pass


# ------------
# HTTP Errors
# ------------
class FileShareExists(falcon.HTTPConflict):

    def __init__(self):
        description = (
            'Files shared already!'
        )
        super().__init__(description=description)

    def to_dict(self, obj_type=dict):
        result = super().to_dict(obj_type)
        result["success"] = False
        result["exists"] = True
        return result


class FileNotFound(falcon.HTTPNotFound):
    def __init__(self):
        description = "File Not found"
        super().__init__(description=description)


# "Unable to create member_file_entry"
class FileUploadCreateException(falcon.HTTPUnprocessableEntity):
    def __init__(self):
        description = "Unable to create file in system"
        super().__init__(description=description)
