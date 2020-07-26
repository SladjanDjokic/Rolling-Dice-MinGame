import falcon


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
        title="File Not Found",
        description="File Not found"
        super().__init__(description=description)