import logging
import json
import datetime
import app.util.request as request
import falcon

from app.events.publishers.publisher import SMSProducer, ChatProducer

logger = logging.getLogger(__name__)


class ChatView(object):
    auth = {
        'exempt_methods': ['POST']
    }

    def on_post(self, req, resp):

        # Weird way to get json dict
        data = req.media
        try:
            message = data.get('message')
            p = ChatProducer()
            p.produce([message], p.topic)
            resp.body = json.dumps(
                {"message": message,
                 "first_name": data.get('first_name')
                 }
        )

        except Exception as exc:
            logger.debug(f"EXCEPTION {exc}")
            resp.status = falcon.HTTP_400
            resp.body = str(exc)
