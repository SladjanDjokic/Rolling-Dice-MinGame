import os
import falcon
import mimetypes
from pathlib import Path

class StaticResource(object):
    def on_get(self, req, resp, file_name):
        # do some sanity check on the filename
        file_path = f'{os.getcwd()}/static/{file_name}'

        file = Path(file_path)
        # iv = file.suffix
        
        type = mimetypes.MimeTypes().guess_type(file_path)[0]
        resp.content_type = type
        resp.status = falcon.HTTP_200
        resp.append_header('x-amera-file', file.name)
        resp.downloadable_as = file.name
        with open(file_path, 'rb') as file:
            resp.body = file.read()
