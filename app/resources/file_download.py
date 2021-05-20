import logging
import pathlib
from urllib.parse import unquote
import falcon

from app import settings
from app.util.auth import check_session
from app.da.file_sharing import FileStorageDA

logger = logging.getLogger(__name__)


class FileDownloadResource():

    def __init__(self):
        self.kafka_data = {"GET": {"event_type": settings.get('kafka.event_types.get.file_download'),
                                   "topic": settings.get('kafka.topics.files')
                                   },
                           }

    @check_session
    def on_get(self, req, resp, file_path):
        file_path = unquote(file_path)
        logger.debug(f'Downloading file: {file_path}')
        # file_pathlib = pathlib.Path(file_path)
        # logger.debug(f"Filename: {file_pathlib.name}")

        # storage_engine_id = FileStorageDA().get_storage_engine_id_from_key(file_path)
        # file_info = FileStorageDA().get_file_detail_by_storage_engine_id(
        #     req.context.auth['session']['member_id'],
        #     storage_engine_id
        # )
        s3_resp = FileStorageDA().stream_s3_file(file_path)
        # logger.debug(f"SE Key: {storage_engine_id}")
        # logger.debug(f"File Info: {file_info}")
        # logger.debug(f"S3 Resp: {s3_resp}")
        # Content-Disposition: attachment; filename=quot.pdf;
        # resp.set_header("Content-Disposition",
        #                 f"attachment; filename=\"{file_info['file_name']}\"")
        resp.content_type = s3_resp['ContentType']
        resp.content_length = s3_resp['ContentLength']
        resp.status = falcon.HTTP_200
        resp.stream = s3_resp['Body']
