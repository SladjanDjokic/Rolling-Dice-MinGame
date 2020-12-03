from app.config import settings

from cryptography.hazmat.primitives.twofactor.totp import TOTP
from cryptography.hazmat.primitives.hashes import SHA1
from cryptography.hazmat.backends import default_backend

import os
import time


def get_totp():
    key = os.urandom(20)
    timeout = 30
    token_time = time.time()
    totp_length = settings.get("services.twilio.totp_length")
    totp = TOTP(key, totp_length, SHA1(), timeout,
                backend=default_backend())
    token = totp.generate(int(token_time)).decode('utf8')
    return token, token_time
