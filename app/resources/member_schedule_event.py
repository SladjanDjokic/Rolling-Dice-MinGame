import logging

import app.util.json as json
import app.util.request as request
from app import settings
from app.util.session import get_session_cookie, validate_session
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
from app.da.member_event import MemberEventDA
from app.da.member_schedule_event import MemberScheduleEventDA
from app.da.member import MemberDA
from app.da.file_sharing import FileStorageDA, FileTreeDA
from app.da.member_schedule_event_invite import MemberScheduleEventInviteDA
from app.da.file_sharing import FileStorageDA
from app.util.auth import check_session
from app.exceptions.member import MemberNotFound
from app.exceptions.member_schedule_event import ScheduleEventAddingFailed
from app.exceptions.file_sharing import FileShareExists, FileNotFound, \
    FileUploadCreateException, FileStorageUploadError
from operator import itemgetter

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
            location_data,  # is either and id of memeber location or a string
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
                        'locationData',
                        'attachments',
                        'recurringCopies',
                        'coverAttachmentId'
                        )(json.loads(event_data))

        # logger.debug(f'event name is {event_name}')
        sequence_id = MemberEventDA().add_sequence(sequence_name=event_name)

        location_id = location_data if (
            location_mode == 'my_locations' and location_data != '' and (event_type == 'Meeting' or event_type == 'Personal')) else None
        location_address = location_data if (
            location_mode == 'lookup' or location_mode == 'url') else None
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
            location_address=location_address,
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
                        location_address=location_address,
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

        updated_event_id = None

        if mode == 'date':
            event_id = contents['event_id']
            event_start_utc = contents['start']
            event_end_utc = contents['end']

            updated_event_id = MemberEventDA().change_event_date(
                event_id=event_id, start=event_start_utc, end=event_end_utc)

        elif mode == 'full':
            event_id = contents['event_id']
            event_name = contents['name']
            color_id = contents['colorId']
            event_start_utc = contents['start']
            event_end_utc = contents['end']
            isFullDay = contents['isFullDay']
            event_type = contents['type']
            event_tz = contents['eventTimeZone']
            location_mode = contents['locationMode']
            location_data = contents['locationData']
            sequence_id = contents['sequence_id']
            event_recurrence_freq = contents['recurrence']
            end_condition = contents['endCondition']
            repeat_weekdays = contents['repeatWeekDays']
            end_date_datetime = contents['endDate']
            repeat_times = contents['repeatTimes']
            invitedGroup = contents['invitedGroup']
            recurringCopies = contents['recurringCopies']
            recurrenceUpdateOption = contents['recurrenceUpdateOption'] if 'recurrenceUpdateOption' in contents.keys(
            ) else None
            event_description = contents['description'] if 'description' in contents.keys(
            ) else None
            invitations = contents['invitations'] if 'invitations' in contents.keys(
            ) else None
            attachments = contents['attachments'] if 'attachments' in contents.keys(
            ) else None
            cover_attachment_id = contents['coverAttachmentId'] if (
                ('coverAttachmentId' in contents.keys()) and (contents['coverAttachmentId'] != 'null')) else None

            location_id = location_data if (
                location_mode == 'my_locations' and location_data != '' and (event_type == 'Meeting' or event_type == 'Personal')) else None
            location_address = location_data if (
                location_mode == 'lookup' or location_mode == 'url') else None

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
                location_address=location_address,
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
                            location_address=location_address,
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
        success = MemberEventDA().get_event_invitations(member_id)

        resp.body = json.dumps({
            "data": success,
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
