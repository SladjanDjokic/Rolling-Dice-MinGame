import logging

import app.util.json as json
import app.util.request as request
from app.util.session import get_session_cookie, validate_session
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
from app.da.member_schedule_event import MemberScheduleEventDA
from app.da.member import MemberDA
from app.da.member_schedule_event_invite import MemberScheduleEventInviteDA
from app.da.file_sharing import FileStorageDA
from app.exceptions.member import MemberNotFound
from app.exceptions.member_schedule_event import ScheduleEventAddingFailed

logger = logging.getLogger(__name__)


class MemberScheduleEventResource(object):
    @staticmethod
    def on_get(req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            event_host_member_id = session["member_id"]

            search_time_start = req.get_param('search_time_start')
            search_time_end = req.get_param('search_time_end')
            schedule_events = MemberScheduleEventDA.get_events_full(event_host_member_id, search_time_start,
                                                                    search_time_end)

            resp.body = json.dumps({
                "data": schedule_events,
                "success": True
            }, default_parser=json.parser)

        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

    @staticmethod
    def on_post(req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            event_host_member_id = session["member_id"]
            (event_name, event_type, event_datetime_start,
             event_datetime_end, event_location_address, event_location_postal,
             event_recurrence, event_invite_to_list_str, event_duration_all_day) = request.get_json_or_form(
                "event_name", "event_type", "event_datetime_start",
                "event_datetime_end", "event_location_address", "event_location_postal",
                "event_recurrence", "event_invite_to_list", "event_duration_all_day", req=req)

            member = MemberDA().get_member(event_host_member_id)
            if not member:
                raise MemberNotFound(member)

            file = req.get_param('event_image')
            # logger.debug("event_image: {}".format(file))

            event_image = None
            if (file is not None) and hasattr(file, 'filename'):
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
                "event_invite_to_list": event_invite_to_list_str,
                "event_duration_all_day": event_duration_all_day
            }

            event_id = MemberScheduleEventDA().add(**set_params)

            if not event_id:
                raise ScheduleEventAddingFailed()

            event_invite_to_list = None
            available_member_list = None
            event_invite_ids = None

            if event_invite_to_list_str:
                event_invite_to_list = json.loads(event_invite_to_list_str)
                # logger.debug("event_invite_to_list: {}".format(event_invite_to_list))

                available_member_list = MemberDA().extractAvailableMembers(event_invite_to_list)
                # logger.debug("set_params: {}".format(available_member_list))

                set_params = {
                    "event_id": event_id,
                    "event_invite_to_list": available_member_list
                }

                event_invite_ids = MemberScheduleEventInviteDA().addMultiple(**set_params)

            event = MemberScheduleEventDA().get_event_by_id(event_id)

            resp.body = json.dumps({
                "data": event,
                "invite_required": event_invite_to_list,
                "invite_available": available_member_list,
                "invite_sent_ID": event_invite_ids,
                "description": "Event has been scheduled successfully!",
                "success": True
            }, default_parser=json.parser)

        except InvalidSessionError as err:
            raise UnauthorizedSession() from err
