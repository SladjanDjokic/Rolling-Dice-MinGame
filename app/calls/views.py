import logging
import json
import datetime
import app.util.request as request
import falcon

from app.da.member import MemberDA
from app.events.publishers.publisher import CallingProducer, SMSProducer

logger = logging.getLogger(__name__)


class IncomingCallView(object):
    """
       {
            "call_id":"FK00000001-TU00000044",
           "call_url":"https://conference.ameraiot.com/FK00000001-TU00000044",
           "caller_id":1,
           "callee_id":44
        }
    """
    auth = {
        'exempt_methods': ['POST']
    }

    def on_post(self, req, resp):
        """
        Post call notification. Sends to Kafka where consumer will push to SSE server

        """
        # Weird way to get json dict
        data = req.media
        try:
            # TODO Start time? Use unix epoch time?
            # TODO Error handling for db or kafka errors!
            caller = MemberDA().get_member(data.get('caller_id'))
            callee = MemberDA().get_member(data.get('callee_id'))
            # Format payload using account dict
            caller_name = f"{caller.get('first_name')} {caller.get('last_name')}"
            callee_name = f"{callee.get('first_name')} {callee.get('last_name')}"

            payload = dict(type="person",
                           call_id=data.get('call_id'),
                           call_url=data.get('call_url'),
                           participants=[caller_name, callee_name],
                           caller_id=data.get('caller_id'),
                           caller_name=caller.get('first_name'),
                           callee_id = data.get('callee_id')
                           )
            payload['event_name'] = f"Call from {caller_name}"

            p = CallingProducer()
            p.produce([json.dumps(payload)])
            resp.status = falcon.HTTP_200
            resp.body = json.dumps(payload)
        except Exception as exc:
            logger.debug(f"EXCEPTION {exc}")
            resp.status = falcon.HTTP_500