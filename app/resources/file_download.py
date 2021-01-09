import logging
import mimetypes
import falcon
import app.util.json as json
import app.util.request as request
from app import settings
from app.da.file_sharing import FileStorageDA

logger = logging.getLogger(__name__)


class FileDownloadResource():

    def __init__(self):
        self.kafka_data = {"GET": {"event_type": settings.get('kafka.event_types.get.file_download'),
                                   "topic": settings.get('kafka.topics.files')
                                   },
                           }

    @staticmethod
    def on_get(req, resp, file_path):
        logger.debug('file amidala', file_path)
        type = mimetypes.MimeTypes().guess_type(file_path)[0]
        s3_resp = FileStorageDA().stream_s3_file(file_path)
        resp.content_type = type
        resp.status = falcon.HTTP_200
        resp.body = s3_resp['Body'].read()
