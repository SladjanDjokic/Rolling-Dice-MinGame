import json

from app.util.db import source
import logging

logger = logging.getLogger(__name__)


class ActivityDA(object):
    source = source

    @classmethod
    def insert_activity(cls, event_key="", headers={}, req_params={},
                        req_url_params={}, req_data={}, resp_data={},
                        http_status="", session_key="", session_data={},
                        member_id="", event_type="activity", status="",
                        create_date="", commit=True):

        insert_activity_q = (
            """
            INSERT INTO activity_trace
                (event_key, headers, request_params, request_url_params,
                request_data, response, http_status, session_key, 
                session_data, member_id, event_type, status, create_date)
                Values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """
        )
        params = (
                    event_key, headers, req_params, req_url_params, req_data,
                    resp_data, http_status, session_key, session_data,
                    member_id, event_type, status, create_date
                )
        try:
            cls.source.execute(insert_activity_q, params)
            if commit:
                cls.source.commit()

        except Exception as e:
            logger.error(e, exc_info=True)
            return False

    # @classmethod
    # def get_recent_activity(cls):
    #     q = """
    #         SELECT * FROM activity_status LIMIT 20
    #
    #         """
    #     try:
    #         results = cls.source.execute(q)
    #         return results
    #     except Exception as e:
    #         logger.error(e, exc_info=True)
