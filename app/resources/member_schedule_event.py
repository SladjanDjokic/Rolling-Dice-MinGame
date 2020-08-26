import logging
import json
from datetime import datetime
from pytz import timezone

import app.util.json as json
import app.util.request as request
from app.util.session import get_session_cookie, validate_session
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
from app.da.member_schedule_event import MemberScheduleEventDA
from app.da.member import MemberDA
from app.da.member_schedule_event_invite import MemberScheduleEventInviteDA
from app.da.file_sharing import FileStorageDA, ShareFileDA
from app.exceptions.member import MemberNotFound
from app.exceptions.member_schedule_event import ScheduleEventAddingFailed

logger = logging.getLogger(__name__)


class MemberScheduleEventResource(object):

    def on_post(self, req, resp):

        [event_host_member_id] = request.get_json_or_form("event_host_member_id", req=req)
        [search_time_start] = request.get_json_or_form("search_time_start", req=req)
        [search_time_end] = request.get_json_or_form("search_time_end", req=req)
                      
        schedule_events = MemberScheduleEventDA.get_events_full(event_host_member_id, search_time_start, search_time_end)

        resp.body = json.dumps({
            "data": schedule_events,
            "success": True
        })
   

class MemberScheduleEventAddResource(object):
    def on_post(self, req, resp):

        (event_name, event_host_member_id, event_type, event_datetime_start, event_datetime_end,
                 event_location_address, event_location_postal, event_recurrence, event_invite_to_list_str) = request.get_json_or_form(
            "event_name", "event_host_member_id", "event_type", "event_datetime_start", "event_datetime_end", 
            "event_location_address", "event_location_postal", "event_recurrence", "event_invite_to_list", req=req)

        member = MemberDA().get_member(event_host_member_id)
        if not member:
            raise MemberNotFound(member_id)

        file = req.get_param('event_image')
        #logger.debug("event_image: {}".format(file))

        event_image = None
        if (file != None) and hasattr(file, 'filename'):
            file_id = FileStorageDA().store_file_to_storage(file)
            status = 'available'
            event_image = FileStorageDA().create_member_file_entry(
                file_id, file.filename, event_host_member_id, status, 'EventImage')
              
        set_params = {
            "event_name": event_name,
            "event_host_member_id": event_host_member_id,
            "event_type": event_type,
            "event_datetime_start": event_datetime_start,
            "event_datetime_end": event_datetime_end,
            "event_location_address": event_location_address, 
            "event_location_postal": event_location_postal, 
            "event_recurrence": event_recurrence,      
            "event_image": event_image,
            "event_invite_to_list":event_invite_to_list_str
        }
        
        event_id = MemberScheduleEventDA().add(**set_params)
        
        if not event_id:
            raise ScheduleEventAddingFailed()

        event_invite_to_list = None
        available_member_list = None
        event_invite_IDs = None
        
        if event_invite_to_list_str:
            event_invite_to_list = json.loads(event_invite_to_list_str)
            #logger.debug("event_invite_to_list: {}".format(event_invite_to_list))

            available_member_list = MemberDA().extractAvailableMembers(event_invite_to_list)        
            #logger.debug("set_params: {}".format(available_member_list))

            set_params = {
                "event_id": event_id,
                "event_invite_to_list": available_member_list   
            }       
            
            event_invite_IDs = MemberScheduleEventInviteDA().addMultiple(**set_params)

        resp.body = json.dumps({
            "data": event_id,
            "invite_required": event_invite_to_list,
            "invite_available": available_member_list,
            "invite_sent_ID": event_invite_IDs,
            "description": "Event has been scheduled successfully!",
            "success": True
        })
