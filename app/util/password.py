import os
import datetime
import errno
from urllib.parse import urlparse, urljoin
from app.config import settings
import requests
import favicon
import logging

logger = logging.getLogger(__name__)

# The safe_open helper lets us handle opening non existent folders

def get_largest_favicon(url):
    try:
        icons = favicon.get(url)
        icon = icons[0]

        response = requests.get(icon.url, stream=True)
        # file_path = f'{os.getcwd()}/static/favicon.{icon.format}'
        # with open(file_path, 'wb') as image:
        #     for chunk in response.iter_content(1024):
        #         image.write(chunk)
        # return file_path
        response.raise_for_status()
        return response
    except Exception as err:
      logger.debug(f"favicon error:{err}")
      return None