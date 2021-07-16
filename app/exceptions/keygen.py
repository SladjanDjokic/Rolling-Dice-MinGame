import falcon


class IMSecureError(falcon.HTTPBadRequest):
    def __init__(self):
        title = "Imsecure error"
        description = "There was a problem while generating key"
        super().__init__(title=title, description=description)