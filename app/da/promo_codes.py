import time
from datetime import datetime
from app.config import settings
from app.util.db import source
from app.exceptions.data import DuplicateKeyError, DataMissingError, RelationshipReferenceError
import logging
logger = logging.getLogger(__name__)


class PromoCodesDA(object):
    source = source

    @classmethod
    def check_promo_code(cls, promo_code):
        query = ("""SELECT
            id as promo_code_id, description
            FROM promo_codes
            WHERE active = true AND expiration_date > now() AND promo_code = %s;
        """)
        params = (promo_code,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            for (promo_code_id, description) in cls.source.cursor:
                code_entry = {
                    "promo_code_id": promo_code_id,
                    "description": description
                }
            return code_entry
        return None

    @classmethod
    def create_activation_entry(cls, member_id, promo_code_id):
        query = ("""INSERT INTO promo_code_activations (member_id, promo_code_id) 
            VALUES (%s, %s)
            RETURNING id;
        """)
        params = (member_id, promo_code_id)
        cls.source.execute(query, params)
        cls.source.commit()
        if cls.source.has_results():
            return True
        return None
