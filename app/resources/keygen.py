import os
import uuid
import pathlib
from urllib.parse import urlparse
from io import StringIO
import sys
import logging

from imsecure.image_secure import ImageSecure
from imsecure.entropy import eta
from imsecure.biastests import check_odd_bias, check_odd_even_run, check_repeats, distro, save_to_bin
import app.util.json as json
from app.da.file_sharing import FileStorageDA
from app.util.filestorage import s3fy_filekey
from app.exceptions.file_sharing import FileNotFound
from app.exceptions.keygen import IMSecureError

logger = logging.getLogger(__name__)

from app import settings


class Capturing(list):
    def __enter__(self):
        self._stdout = sys.stdout
        sys.stdout = self._stringio = StringIO()
        return self

    def __exit__(self, *args):
        self.extend(self._stringio.getvalue().splitlines())
        del self._stringio    # free up some memory
        sys.stdout = self._stdout


def get_image_info(image_file, pin="000000", factor="", keysize=256, mode="lowxor",
                 ratio=1000, compress=False, ncount=1, verbose=0, demo=False):

    print("Mode: {}".format(mode))
    print("Pin: {}".format(pin))

    secure = ImageSecure(image_file, pin, factor, keysize=keysize,
                         mode=mode, compress=compress, ncount=ncount,
                         ratio=ratio, verbose=verbose)
    #secure.test_incr()
    keys = ['color_count', 'color_per_row', 'color_ratio', 'colorsize', 'columns', 
            'pixelsize', 'rotateby', 'rows', 'size', 'pixelsize', 
            'orient']
    # 'im', 'pixelsize'
    return {
        key: getattr(secure, key) for key in keys
    }


def call_key_gen(image_file, pin="000000", factor="", keysize=256, mode="lowxor",
                 ratio=1000, compress=False, ncount=1, verbose=1, frombytes=False, imagedata=None):
    
    print("Mode: {}".format(mode))
    print("Pin: {}".format(pin))

    secure = ImageSecure(image_file, pin, factor, keysize=keysize,
        mode=mode, compress=compress, ncount=ncount,
        ratio=ratio, verbose=verbose, frombytes=frombytes, imagedata=imagedata)

    with Capturing() as output:
        #secure.test_incr()
        key = secure.harvest()
        saved = secure.save_to_file()
        entropy = eta(key)

        #simple stupid bias tests
        check_odd_bias(key, verbose=True)
        check_odd_even_run(key, verbose=True)
        check_repeats(key, 1, verbose=True)
        distro(bytes(key))
    
    saved = pathlib.Path(saved)

    return output, key, saved, entropy, secure
    
    # key = secure.harvest()
    # keydata = f'{bytes(key).hex()}'  #result is bytes, want a hex string
    # return keydata
    


class KeyGenFileUpload(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.keygen_file_upload'),
                                    "topic": settings.get('kafka.topics.keygen')
                                    },
                           "GET": {"event_type": settings.get('kafka.event_types.get.keygen_file_upload'),
                                   "topic": settings.get('kafka.topics.keygen')
                                   },
                           }

    auth = {
        'exempt_methods': ['POST']
    }

    def on_post(self, req, resp):
        image = req.get_param('image', required=True)
        pin = req.get_param('pin', required=True)
        factor = req.get_param('factor', default='')
        keysize = req.get_param('keysize', default=256)
        ncount = req.get_param('ncount', default=1)
        ratio = req.get_param('ratio', default=1000)

        # Read image as binary
        raw = image.file.read()
        # Retrieve filename
        filename = image.filename

        temp = uuid.uuid4().hex
        filename = '/tmp/{}-{}'.format(temp, filename)

        image_file = pathlib.Path(filename)
        image_file.write_bytes(raw)

        secure = get_image_info(
            image_file=image_file,
            pin=pin,
            factor=factor,
            keysize=keysize,
            ncount=ncount,
            ratio=ratio)

        print("Secure: {}".format(secure))

        resp.body = json.dumps({
            "filename": image_file.name,
            "secure": secure
        })

    def on_get(self, req, resp):
        file = req.get_param('file', required=True)

        file = pathlib.Path('/tmp/{}'.format(file))
        binary = file.read_bytes()
        resp.body = binary


class KeyGenResource(object):

    def __init__(self):
        self.kafka_data = {
            "POST": {
                "event_type": settings.get('kafka.event_types.post.keygen_resource_crud'),
                "topic": settings.get('kafka.topics.keygen')
            },
            "GET": {
                "event_type": settings.get('kafka.event_types.get.keygen_resource_crud'),
                "topic": settings.get('kafka.topics.keygen')
            },
        }

    auth = {
        'exempt_methods': ['POST']
    }

    def on_post(self, req, resp):
        pin = req.get_param('pin', required=True)
        filename = req.get_param('filename', required=True)
        factor = req.get_param('factor', default='0')
        keysize = req.get_param('keysize', default=256)
        ncount = req.get_param('ncount', default=4)
        ratio = req.get_param('ratio', default=30)

        try:
            keysize=int(keysize)
        except:
            keysize=256    

        filename = '/tmp/{}'.format(filename)
        image_file = pathlib.Path(filename)

        output, key, saved, entropy, secure = call_key_gen(
            image_file=image_file,
            pin=pin,
            factor=factor,
            keysize=keysize,
            ncount=ncount,
            ratio=ratio)

        resp.body = json.dumps({
            "filename": image_file.name,
            "output": output,
            "key": key,
            "saved": saved.name,
            "entropy": entropy
        })

    def on_get(self, req, resp):
        file = req.get_param('file', required=True)

        file = pathlib.Path('/tmp/{}'.format(file))
        binary = file.read_bytes()
        resp.body = binary

    def on_post_file(self, req, resp):
        image = req.get_param('image', required=True)
        pin = req.get_param('pin', required=True)
        factor = req.get_param('factor', default='0')
        keysize = req.get_param_as_int('keysize', default=256)
        ncount = req.get_param_as_int('ncount', default=4)
        ratio = req.get_param_as_int('ratio', default=30)

        try:
            keysize=int(keysize)
        except:
            keysize=256

        # Read image as binary
        raw = image.file.read()
        # Retrieve filename
        filename = image.filename

        temp = uuid.uuid4().hex
        filename = '/tmp/{}-{}'.format(temp, filename)

        image_file = pathlib.Path(filename)
        image_file.write_bytes(raw)

        try:

            output, key, saved, entropy, secure = call_key_gen(
                image_file=image_file,
                pin=pin,
                factor=factor,
                keysize=keysize,
                ncount=ncount,
                ratio=ratio)

            resp.body = json.dumps({
                "filename": image_file.name,
                "output": output,
                "key": key,
                "saved": saved.name,
                "entropy": entropy
            })
        except Exception as e:
            raise IMSecureError

    def on_post_storage(self, req, resp):
        storage_id = req.get_param('storage_id', required=True)
        pin = req.get_param('pin', required=True)
        factor = req.get_param('factor', default='0')
        keysize = req.get_param_as_int('keysize', default=256)
        ncount = req.get_param_as_int('ncount', default=4)
        ratio = req.get_param_as_int('ratio', default=30)

        try:
            keysize=int(keysize)
        except:
            keysize=256

        file_info = FileStorageDA.get_file_storage_by_storage_id(storage_id)
        if not file_info:
            raise FileNotFound()
        
        item_path = urlparse(file_info['file_location']).path
        item_key = s3fy_filekey(item_path)
        s3resp = FileStorageDA.stream_s3_file(item_key)

        try:

            output, key, saved, entropy, secure = call_key_gen(
                image_file="",
                pin=pin,
                factor=factor,
                keysize=keysize,
                ncount=ncount,
                ratio=ratio,
                frombytes=True,
                imagedata=s3resp['Body'].read()
            )

            resp.body = json.dumps({
                "filename": pathlib.Path(item_path).name,
                "output": output,
                "key": key,
                "saved": saved.name,
                "entropy": entropy
            })

        except Exception as e:
            raise IMSecureError
