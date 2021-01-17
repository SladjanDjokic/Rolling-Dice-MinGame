import logging
import json
import datetime
import app.util.request as request
import falcon

from app.da.member import MemberDA
from app.events.publishers.publisher import CallingProducer, SMSProducer
from app.config import settings
from app.da.group import GroupMembershipDA

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

    def __init__(self):
        self.p = CallingProducer()
        self.kafka_data = {"POST": {"event_type": None,
                                    "topic": None
                                    },
                           }

    auth = {
        'exempt_methods': ['POST']
    }

    def on_post(self, req, resp):
        """
        Post call notification. Sends to Kafka where consumer will push to SSE server

        """
        data = req.media
        if data.get('reply_type'):
            # Incoming Accept/Decline Reply for Person/Group Call
            # Simply route json to eventserver with reply_type since json already formed
            self.p.produce([json.dumps(data)])
            resp.body = json.dumps({})
            resp.status = falcon.HTTP_200

        elif data.get('group_id'):
            if data.get('reply_type'):
                # TODO How to handle reply type
                pass
            else:
                # TODO consider moving this to consumer instead of api
                logger.debug("### GROUP CALL")
                # Get all group members other than leader
                group_members = GroupMembershipDA.get_members_by_group_id(int(data.get('group_id')))
                caller_id = int(data.get('caller_id'))

                # Just in case member is the leader - do a separate query. Fix this later
                caller = MemberDA().get_member(data.get('caller_id'))
                caller_name = f"{caller.get('first_name')} {caller.get('last_name')}"
                participants = [caller_name]
                try:
                    group_call_info = []
                    for member in group_members:
                        if member.get('member_id') == caller_id:
                            continue
                        participants.append(f"{member.get('first_name')} {member.get('last_name')}")

                    # Create call data for each member
                    for member in group_members:
                        if member.get('member_id') == caller_id:
                            continue
                        # TODO Start time? Use unix epoch time?
                        payload = dict(type="group",
                                       call_id=data.get('call_id'),
                                       call_url=data.get('call_url'),
                                       participants=participants,
                                       caller_id=caller_id,
                                       caller_name=caller.get('first_name'),
                                       callee_id=member.get('member_id')
                                       )
                        payload['event_name'] = f"Call from {caller_name}"
                        group_call_info.append(json.dumps(payload))
                        resp.status = falcon.HTTP_200
                        resp.body = json.dumps(payload)

                    # produce all call info for each member. Excluding leader
                    self.p.produce(group_call_info)
                    resp.body = json.dumps({})
                    resp.status = falcon.HTTP_200
                except Exception as e:
                    logger.error(e, exc_info=True)
                    resp.status = falcon.HTTP_500
        else:
            # Incoming Person Call
            try:
                # TODO Start time? Use unix epoch time?
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

                self.p.produce([json.dumps(payload)])
                resp.status = falcon.HTTP_200
                resp.body = json.dumps(payload)
            except Exception as exc:
                logger.error(f"EXCEPTION {exc}", exc_info=True)
                resp.status = falcon.HTTP_500