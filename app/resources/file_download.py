import logging
import mimetypes
import falcon
import app.util.json as json
import app.util.request as request
from app.da.file_sharing import FileStorageDA

logger = logging.getLogger(__name__)


class FileDownloadResource():

    def on_get(self, req, resp, file_path):
        type = mimetypes.MimeTypes().guess_type(file_path)[0]
        s3_resp = FileStorageDA().stream_s3_file(file_path)
        logger.debug('Luke', s3_resp)
        resp.content_type = type
        resp.status = falcon.HTTP_200
        resp.body = s3_resp['Body'].read()
