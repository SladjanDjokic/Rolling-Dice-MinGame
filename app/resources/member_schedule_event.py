import logging
import requests
import os
import io
import cgi

from requests.models import HTTPError

import app.util.json as json
import app.util.request as request
from app import settings
from app.util.session import get_session_cookie, validate_session
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
from app.da.member_event import MemberEventDA
from app.da.member_schedule_event import MemberScheduleEventDA
from app.da.member import MemberDA, MemberContactDA, MemberVideoMailDA, MemberInfoDA
from app.da.group import GroupDA
from app.da.country import CountryCodeDA
from app.da.location import LocationDA
from app.da.file_sharing import FileStorageDA, FileTreeDA
from app.da.member_schedule_event_invite import MemberScheduleEventInviteDA
from app.da.file_sharing import FileStorageDA
from app.da.project import ProjectDA

from app.util.auth import check_session
from app.exceptions.member import MemberNotFound
from app.exceptions.member_schedule_event import ScheduleEventAddingFailed
from app.exceptions.file_sharing import FileShareExists, FileNotFound, \
    FileUploadCreateException, FileStorageUploadError
from operator import itemgetter
from app.util.textmessage import send_sms

logger = logging.getLogger(__name__)


class MemberScheduleEventResource(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.create_event'),
                                    "topic": settings.get('kafka.topics.calendar')
                                    },
                           "PUT": {"event_type": settings.get('kafka.event_types.put.edit_event'),
                                   "topic": settings.get('kafka.topics.calendar')
                                   },
                           "DELETE": {"event_type": settings.get('kafka.event_types.delete.delete_event'),
                                      "topic": settings.get('kafka.topics.calendar')
                                      },
                           }

    @check_session
    def on_get(self, req, resp):
        """
        Retrieve all events for a user's calendar based on search start and end time
        """
        event_host_member_id = req.context.auth["session"]["member_id"]

        search_time_start = req.get_param('search_time_start')
        search_time_end = req.get_param('search_time_end')
        schedule_events = MemberEventDA.get_events_by_range(
            event_host_member_id,
            search_time_start,
            search_time_end
        )

        # If no events, it will return [None]
        if schedule_events and len(schedule_events) > 0 and schedule_events[0]:
            resp.body = json.dumps({
                "data": schedule_events,
                "description": "Events fetched successfully",
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "data": [[]],
                "description": "No events for selected date time range",
                "success": True
            }, default_parser=json.parser)

    @check_session
    def on_post(self, req, resp):
        """
        Create an event for a user
        """
        host_member_id = req.context.auth["session"]["member_id"]
        (event_data,) = request.get_json_or_form("event_data", req=req)

        (event_name,
            color_id,  # color id
            event_description,
            invited_members,  # [contact_member_id]
            invited_group,  # group_id or None
            event_tz,  # [IANA string, not matches the V2 table]
            event_start_utc,
            event_end_utc,
            isFullDay,  # bool
            event_type,  # enum
            event_recurrence_freq,  # enum
            end_condition,  # eunm
            repeat_weekdays,  # [int ids of weekdays fro date-fns]
            end_date_datetime,
            repeat_times,  # int
            location_mode,  # enum
            member_location_id,  # id or none
            location,  # object or none
            event_url,  # string
            attachments,  # [member_file ids]
            recurringCopies,  # [{start: utc, end: utc}] of obj
            cover_attachment_id  # member_file_id
         ) = itemgetter('name',
                        'colorId',
                        'description',
                        'invitedMembers',
                        'invitedGroup',
                        'eventTimeZone',
                        'start',
                        'end',
                        'isFullDay',
                        'type',
                        'recurrence',
                        'endCondition',
                        'repeatWeekDays',
                        'endDate',
                        'repeatTimes',
                        'locationMode',
                        'memberLocationId',
                        "location",
                        "eventUrl",
                        'attachments',
                        'recurringCopies',
                        'coverAttachmentId'
                        )(json.loads(event_data))

        # logger.debug(f'event name is {event_name}')
        sequence_id = MemberEventDA().add_sequence(sequence_name=event_name)

        '''
            If saved location mode => store both member_location_id and location_id
            If new location, make sure to detect country at first
        '''

        location_id = None
        if location_mode == 'lookup' and location:
            storage_file_id = None
            # check if exist location by place_id
            location_data = LocationDA().get_location_by_place_id(
                location['place_id'])

            if not location_data:
                logger.debug('Location not found in database')
                # check if exist photo & save
                logger.debug(f'Check for photo URL: {location.get("photo_url")}')
                if location.get('photo_url'):
                    storage_file_id = self._fetch_location_photo_url(
                        location.get('place_id'), location.get('photo_url'))

                country_code_id = CountryCodeDA.get_id_by_alpha2(
                    location["country_alpha2"])
                location_id = LocationDA.insert_location(
                    country_code_id=country_code_id,
                    admin_area_1=location.get("admin_area_1"),
                    admin_area_2=location.get("admin_area_2"),
                    locality=location.get("locality"),
                    sub_locality=location.get("sub_locality"),
                    street_address_1=location.get("street_address_1"),
                    street_address_2=location.get("street_address_2"),
                    postal_code=location.get("postal_code"),
                    latitude=location.get("latitude"),
                    longitude=location.get("longitude"),
                    map_vendor=location.get("map_vendor"),
                    map_link=location.get("map_link"),
                    place_id=location.get("place_id"),
                    vendor_formatted_address=location.get("vendor_formatted_address"),
                    raw_response=json.dumps(location),
                    location_profile_picture_id=storage_file_id,
                    name=location.get("name")
                )
            else:
                location_id = location_data['id']
        elif location_mode == 'my_locations' and member_location_id:
            location_id = MemberInfoDA.get_location_id_for_member_location(
                member_location_id)

        cover_attachment_id = cover_attachment_id if (
            cover_attachment_id != 'null') else None

        # This is the first event id

        main_event_id = MemberEventDA().add_2(
            sequence_id=sequence_id,
            event_color_id=color_id,
            event_name=event_name,
            event_description=event_description,
            host_member_id=host_member_id,
            is_full_day=isFullDay,
            event_tz=event_tz,
            start_datetime=event_start_utc,
            end_datetime=event_end_utc,
            event_type=event_type,
            event_recurrence_freq=event_recurrence_freq,
            end_condition=end_condition,
            repeat_weekdays=repeat_weekdays,
            end_date_datetime=end_date_datetime,
            location_mode=location_mode,
            location_id=location_id,
            member_location_id=member_location_id,
            event_url=event_url,
            repeat_times=repeat_times,
            cover_attachment_id=cover_attachment_id,
            group_id=invited_group
        )

        # if recurring -> add events for each instance
        all_event_ids = [main_event_id]

        if event_recurrence_freq != 'No recurrence':
            if len(recurringCopies) > 0:
                for copy in recurringCopies:
                    recurring_id = MemberEventDA().add_2(
                        sequence_id=sequence_id,
                        event_color_id=color_id,
                        event_name=event_name,
                        event_description=event_description,
                        host_member_id=host_member_id,
                        is_full_day=isFullDay,
                        event_tz=event_tz,
                        start_datetime=copy["start"],
                        end_datetime=copy["end"],
                        event_type=event_type,
                        event_recurrence_freq=event_recurrence_freq,
                        end_condition=end_condition,
                        repeat_weekdays=repeat_weekdays,
                        end_date_datetime=end_date_datetime,
                        location_mode=location_mode,
                        location_id=location_id,
                        member_location_id=member_location_id,
                        event_url=event_url,
                        repeat_times=repeat_times,
                        cover_attachment_id=cover_attachment_id,
                        group_id=invited_group
                    )
                    all_event_ids.append(recurring_id)

        '''
            attachments for all instances of the
            recurring event
        '''
        if len(attachments) > 0:
            for file_id in attachments:
                for event_id in all_event_ids:
                    MemberEventDA().bind_attachment(event_id, file_id)

        '''
            Invite members for all events in the row. 1 event x 1 member = 1 invite
        '''
        if invited_members and len(invited_members) > 0:
            if len(all_event_ids) > 0:
                for invitee_id in invited_members:
                    for event_id in all_event_ids:
                        if event_id == main_event_id:
                            MemberScheduleEventInviteDA().create_invite(
                                invitee_id=invitee_id, event_id=event_id)
                        else:
                            MemberScheduleEventInviteDA().create_invite(
                                invitee_id=invitee_id, event_id=event_id, status="Recurring")

        '''
            Now get the sequence we've created and send it back to front end.
            Single event is a sequence of one
        '''
        event_sequence_json = MemberEventDA.get_event_sequence_by_id(
            sequence_id)

        '''
            TODO:
            Send invitation emails to members, BUT group them by sequence, i.e.
            A member gets one email per all events he is invited to in this sequence
        '''

        if event_sequence_json:
            resp.body = json.dumps({
                "data": event_sequence_json,
                "description": "Event sequence has been scheduled successfully!",
                "success": True
            }, default_parser=json.parser)
        else:
            resp.status = 500
            resp.body = json.dumps({
                "description": "Creating event sequence went wrong",
                "success": False
            }, default_parser=json.parser)

    @check_session
    def on_put(self, req, resp):
        host_member_id = req.context.auth["session"]["member_id"]
        (event_data, mode) = request.get_json_or_form(
            "event_data", "mode", req=req)

        contents = json.loads(event_data)
        result = None
        updated_event_id = None

        if mode == 'date':
            event_id = contents.get('event_id')
            event_start_utc = contents.get('start')
            event_end_utc = contents.get('end')

            updated_event_id = MemberEventDA().change_event_date(
                event_id=event_id, start=event_start_utc, end=event_end_utc)

        elif mode == 'full':
            event_id = contents.get('event_id')
            event_name = contents.get('name')
            color_id = contents.get('colorId')
            event_start_utc = contents.get('start')
            event_end_utc = contents.get('end')
            isFullDay = contents.get('isFullDay')
            event_type = contents.get('type')
            event_url = contents.get('eventUrl')
            event_tz = contents.get('eventTimeZone')
            location_mode = contents.get('locationMode')
            member_location_id = contents.get('memberLocationId')
            location = contents.get('location', {})
            sequence_id = contents.get('sequence_id')
            event_recurrence_freq = contents.get('recurrence')
            end_condition = contents.get('endCondition')
            repeat_weekdays = contents.get('repeatWeekDays')
            end_date_datetime = contents.get('endDate')
            repeat_times = contents.get('repeatTimes')
            invitedGroup = contents.get('invitedGroup')
            recurringCopies = contents.get('recurringCopies')
            recurrenceUpdateOption = contents.get('recurrenceUpdateOption')
            event_description = contents.get('description')
            invitations = contents.get('invitations')
            attachments = contents.get('attachments')
            cover_attachment_id = contents.get('coverAttachmentId')
            if cover_attachment_id == 'null':
                cover_attachment_id = None

            location_id = None
            if location_mode == 'lookup' and location:
                storage_file_id = None
                # check if exist location by place_id
                location_data = LocationDA().get_location_by_place_id(location.get('place_id'))

                if not location_data:
                    # check if exist photo & save
                    if location.get('photo_url'):
                        storage_file_id = self._fetch_location_photo_url(
                            location.get('place_id'), location.get('photo_url'))

                    country_code_id = CountryCodeDA.get_id_by_alpha2(
                        location["country_alpha2"])

                    location_id = LocationDA.insert_location(
                        country_code_id=country_code_id,
                        admin_area_1=location.get("admin_area_1"),
                        admin_area_2=location.get("admin_area_2"),
                        locality=location.get("locality"),
                        sub_locality=location.get("sub_locality"),
                        street_address_1=location.get("street_address_1"),
                        street_address_2=location.get("street_address_2"),
                        postal_code=location.get("postal_code"),
                        latitude=location.get("latitude"),
                        longitude=location.get("longitude"),
                        map_vendor=location.get("map_vendor"),
                        map_link=location.get("map_link"),
                        place_id=location.get("place_id"),
                        vendor_formatted_address=location.get("vendor_formatted_address"),
                        name=location.get("name"),
                        raw_response=json.dumps(location),
                        location_profile_picture_id=storage_file_id
                    )
                else:
                    location_id = location_data['id']
            elif location_mode == 'my_locations' and member_location_id:
                location_id = MemberInfoDA.get_location_id_for_member_location(
                    member_location_id)

            if hasattr(invitedGroup, 'group_id'):
                group_id = invitedGroup.group_id
            else:
                group_id = None

            if recurrenceUpdateOption and recurrenceUpdateOption == 'next':
                # cancel sequence_id & date
                MemberEventDA.cancel_events_after(sequence_id, event_start_utc)
                # add new sequence
                sequence_id = MemberEventDA().add_sequence(sequence_name=event_name)
            else:
                # cancel sequence_id
                MemberEventDA.cancel_events_by_sequence_id(sequence_id)

            # This is the first event id
            event_id = MemberEventDA().add_2(
                sequence_id=sequence_id,
                event_color_id=color_id,
                event_name=event_name,
                event_description=event_description,
                host_member_id=host_member_id,
                is_full_day=isFullDay,
                event_tz=event_tz,
                start_datetime=event_start_utc,
                end_datetime=event_end_utc,
                event_type=event_type,
                event_recurrence_freq=event_recurrence_freq,
                end_condition=end_condition,
                repeat_weekdays=repeat_weekdays,
                end_date_datetime=end_date_datetime,
                location_mode=location_mode,
                location_id=location_id,
                member_location_id=member_location_id,
                event_url=event_url,
                repeat_times=repeat_times,
                cover_attachment_id=cover_attachment_id,
                group_id=None
            )

            # if recurring -> add events for each instance
            all_event_ids = [event_id]

            if event_recurrence_freq != 'No recurrence':
                if len(recurringCopies) > 0:
                    for copy in recurringCopies:
                        recurring_id = MemberEventDA().add_2(
                            sequence_id=sequence_id,
                            event_color_id=color_id,
                            event_name=event_name,
                            event_description=event_description,
                            host_member_id=host_member_id,
                            is_full_day=isFullDay,
                            event_tz=event_tz,
                            start_datetime=copy["start"],
                            end_datetime=copy["end"],
                            event_type=event_type,
                            event_recurrence_freq=event_recurrence_freq,
                            end_condition=end_condition,
                            repeat_weekdays=repeat_weekdays,
                            end_date_datetime=end_date_datetime,
                            location_mode=location_mode,
                            location_id=location_id,
                            member_location_id=member_location_id,
                            event_url=event_url,
                            repeat_times=repeat_times,
                            cover_attachment_id=cover_attachment_id,
                            group_id=None
                        )
                        all_event_ids.append(recurring_id)

            '''
                attachments for all instances of the
                recurring event
            '''
            if len(attachments) > 0:
                for file_id in attachments:
                    for event_id in all_event_ids:
                        MemberEventDA().bind_attachment(
                            event_id, file_id['member_file_id'])

            '''
                Invite members for all events in the row. 1 event x 1 member = 1 invite
            '''
            if invitations and len(invitations) > 0:
                if len(all_event_ids) > 0:
                    for invitation in invitations:
                        for event_id in all_event_ids:
                            MemberScheduleEventInviteDA().create_invite(
                                invitee_id=invitation['invite_member_id'], event_id=event_id)

            '''
                Now get the sequence we've created and send it back to front end.
                Single event is a sequence of one
            '''
            result = MemberEventDA.get_event_sequence_by_id(
                sequence_id)

        if updated_event_id:
            logger.debug('updating success', updated_event_id)
            result = MemberEventDA().get_event_by_id(updated_event_id)
        if result:
            resp.body = json.dumps({
                "data": result,
                "description": "Event has been modified succsessfully",
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Creating modification went wrong",
                "success": False
            }, default_parser=json.parser)

    @check_session
    def on_delete(self, req, resp):
        host_member_id = req.context.auth["session"]["member_id"]
        (option, event) = request.get_json_or_form('option', 'event', req=req)
        event_id = event['event_id']
        sequence_id = event['sequence_id']
        start_datetime = event['start']
        success = None
        if (option == 'onlyThis'):
            success = MemberEventDA.cancel_single_event(event_id)
        elif (option == 'allUpcoming'):
            success = MemberEventDA.cancel_events_after(
                sequence_id, start_datetime)

        if success:
            result = MemberEventDA.get_event_sequence_by_id(sequence_id)
            if result:
                resp.body = json.dumps({
                    "data": result,
                    "sequence_id": sequence_id,
                    "description": "Event cancelled succsessfully",
                    "success": True
                }, default_parser=json.parser)
            else:
                resp.body = json.dumps({
                    "description": "Cancelling events went wrong",
                    "success": False
                }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Cancelling events went wrong",
                "success": False
            }, default_parser=json.parser)

    def _fetch_location_photo_url(self, place_id, photo_url):
        mime_type = "image/jpeg"
        file_name = f"{place_id}.jpg"

        logger.debug(f"Fetching place_id: {place_id} photo: {photo_url}")
        try:
            with requests.get(photo_url, stream=True) as photo_response:
                logger.debug(
                    f"Fetching result with http status of: {photo_response.status_code}, raising for status")
                photo_response.raise_for_status()
                # file = io.BytesIO(photo_response.content)
                file_size_bytes = photo_response.headers["Content-Length"]
                logger.debug(
                    f"Fetch result with Content-Length of: {photo_response.headers['Content-Length']}, raising for status")

                if photo_response.headers["Content-Length"] == 0:
                    raise HTTPError
                return FileStorageDA().save_to_storage(
                    file=photo_response.raw,
                    filename=file_name,
                    size=file_size_bytes,
                    mime_type=mime_type,
                    member_id=None
                )
        except HTTPError:
            logger.exception(f"Failed to fetch photo_url: {photo_url}, with place id of: {place_id}")

        return None


class MemberScheduleEventColors(object):
    @staticmethod
    def on_post(req, resp):
        """
        Create an event for a user
        """

    def on_get(self, req, resp):
        try:

            session_id = get_session_cookie(req)
            session = validate_session(session_id)

            colors = MemberScheduleEventDA().get_colors()

            if colors:
                resp.body = json.dumps({
                    "colors": colors,
                    "success": True
                }, default_parser=json.parser)
            else:
                resp.body = json.dumps({
                    "description": "Could not retrieve event colors",
                    "success": False
                }, default_parser=json.parser)

        except InvalidSessionError as err:
            raise UnauthorizedSession() from err


class EventAttachmentResorce(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.create_event_attachment'),
                                    "topic": settings.get('kafka.topics.calendar')
                                    },
                           "DELETE": {"event_type": settings.get('kafka.event_types.delete.delete_event_attachment'),
                                      "topic": settings.get('kafka.topics.calendar')
                                      },
                           }

    @check_session
    def on_get(self, req, resp):
        logger.debug('aaa')

    @check_session
    def on_post(self, req, resp):
        logger.debug('Incoming attachment')
        file = req.get_param("file")
        file_name = req.get_param("fileName")
        file_size_bytes = req.get_param("size")
        mime_type = req.get_param("mime")
        member = req.context.auth["session"]
        member_id = member["member_id"]

        storage_file_id = FileStorageDA().put_file_to_storage(
            file, file_size_bytes, mime_type)
        member_file_id = FileTreeDA().create_member_file_entry(
            file_id=storage_file_id,
            file_name=file_name,
            member_id=member_id,
            status="available",
            file_size_bytes=file_size_bytes)  # FIXME: change this after we migrate to storing file size in fs_storage
        if not member_file_id:
            raise FileUploadCreateException

        file_data = FileStorageDA().get_member_file(
            member, storage_file_id)

        if file_data:
            resp.body = json.dumps({
                "data": file_data,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Could not attach file",
                "success": False
            }, default_parser=json.parser)

    @check_session
    def on_delete(self, req, resp):
        logger.debug('ccc')


class MemberUpcomingEvents(object):
    @check_session
    def on_get(self, req, resp):
        member_id = req.context.auth["session"]["member_id"]
        current = req.get_param('current')
        limit = req.get_param('limit')

        upcoming_events = MemberEventDA().get_upcoming_events(member_id, current, limit)

        resp.body = json.dumps({
            "data": upcoming_events,
            "message": "Upcoming Events",
            "status": "success",
            "success": True
        }, default_parser=json.parser)


class MemberEventInvitations(object):
    def __init__(self):
        self.kafka_data = {"GET": {"event_type": settings.get('kafka.event_types.get.event_invite_response'),
                                   "topic": settings.get('kafka.topics.calendar')
                                   },
                           "PUT": {"event_type": settings.get('kafka.event_types.get.event_invite_response'),
                                   "topic": settings.get('kafka.topics.calendar')
                                   },
                           }

    @check_session
    def on_get(self, req, resp):
        member_id = req.context.auth["session"]["member_id"]

        event_invitations = MemberEventDA().get_event_invitations(member_id)

        # contact invitation
        contact_invitations = MemberContactDA.get_all_contact_invitations_by_member_id(
            member_id)

        # group invite
        group_invitations = GroupDA.get_all_group_invitations_by_member_id(
            member_id)            # project contract invite

        # new media message
        new_media_messages = MemberVideoMailDA.get_all_media_mails(
            member_id)

        # project contract invitations
        contract_invitations = ProjectDA.get_member_contract_invites(
            member_id)

        if not event_invitations:
            event_invitations = []
        if not contact_invitations:
            contact_invitations = []
        if not group_invitations:
            group_invitations = []
        if not new_media_messages:
            new_media_messages = []
        if not contract_invitations:
            contract_invitations = []

        result = event_invitations + contact_invitations + \
            new_media_messages + group_invitations + contract_invitations

        resp.body = json.dumps({
            "data": result,
            "message": "Invitations",
            "status": "success",
            "success": True
        }, default_parser=json.parser)

    @check_session
    def on_put(self, req, resp, event_invite_id):
        status_list = ['Accepted', 'Declined']
        (status, comment) = request.get_json_or_form(
            "status", "comment", req=req)
        member_id = req.context.auth["session"]["member_id"]
        if status in status_list:

            '''
                Here comes the logic to handle recurring events:
                If the invite refers to an event from a recurrent sequence =>
                Find all instances having status 'Recurring' and make them 'Accepted'
            '''
            recurring_invite_ids = MemberEventDA().get_recurring_copies_invite_ids(
                member_id, event_invite_id)

            success = {}
            if recurring_invite_ids and len(recurring_invite_ids) > 0:
                for recurring_invite_id in recurring_invite_ids:
                    success[recurring_invite_id] = MemberEventDA().set_event_invite_status(
                        member_id, recurring_invite_id, status, comment)

            success[event_invite_id] = MemberEventDA().set_event_invite_status(
                member_id, event_invite_id, status, comment)

            is_all_updated = all(value == True for value in success.values())
            if is_all_updated:
                resp.body = json.dumps({
                    "message": "success to set event status",
                    "status": "success",
                    "success": True
                }, default_parser=json.parser)
            else:
                failed_event_ids = list(
                    {k: v for (k, v) in success.items() if v != True}.keys())

                resp.body = json.dumps({
                    "description": f"Could not set event status for invite ids {failed_event_ids}",
                    "success": False
                }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Invalid status",
                "success": False
            }, default_parser=json.parser)


class MemberEventDirections(object):
    @check_session
    def on_post(self, req, resp):
        try:
            (event_name, destination_address, destination_name, link, member_ids) = request.get_json_or_form("event_name", "destinationAddress", "destinationName",
                                                                                                             "link", "memberIds", req=req)

            success = {id: False for id in member_ids}

            if member_ids and len(member_ids) > 0:
                for member_id in member_ids:
                    cell_phone = MemberContactDA.get_member_cell(member_id)
                    message = f"Driving directions to \"{event_name}\" at:\n\n{destination_name if destination_name else ''}\n{destination_address}"
                    if cell_phone:
                        sid = send_sms(
                            cell_phone, message)
                        logger.debug(f"sid {sid}")
                        if sid:
                            success.update({member_id: True})

            resp.body = json.dumps({
                "success": success,
            }, default_parser=json.parser)
        except Exception as err:
            logger.exception(err)
            raise err
