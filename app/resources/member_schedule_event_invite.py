import logging
from datetime import timezone, datetime

import app.util.json as json
import app.util.request as request
from app.util.session import get_session_cookie, validate_session
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
from app.da.member_schedule_event_invite import MemberScheduleEventInviteDA
from app.da.member import MemberDA
from app.da.member_schedule_event import MemberScheduleEventDA
from app.exceptions.member import MemberNotFound
from app.exceptions.member_schedule_event_invite import ScheduleEventInviteNotFound, ScheduleEventInviteAddingFailed
from app.exceptions.member_schedule_event import ScheduleEventNotFound

logger = logging.getLogger(__name__)


class MemberScheduleEventInviteResource(object):
    @staticmethod
    def on_get(req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            event_invite_to = req.get_param("event_invite_to")
            search_time_start = req.get_param("search_time_start")
            search_time_end = req.get_param("search_time_end")

            event_invites = MemberScheduleEventInviteDA.get_event_invites_full(event_invite_to, search_time_start,
                                                                               search_time_end)

            resp.body = json.dumps({
                "data": event_invites,
                "success": True
            }, default_parser=json.parser)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

    @staticmethod
    def on_post(req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            (event_id, event_invite_to_list) = request.get_json_or_form(
                "event_id", "event_invite_to_list", req=req)

            add_result = list()
            if event_invite_to_list is not None:
                event_invite_to_list = json.loads(event_invite_to_list)
                available_member_list = MemberDA().extractAvailableMembers(event_invite_to_list)

                set_params = {
                    "event_id": event_id,
                    "event_invite_to_list": available_member_list
                }
                #logger.debug("set_params: {}".format(set_params))

                add_result = MemberScheduleEventInviteDA().addMultiple(**set_params)

                if not add_result:
                    raise ScheduleEventInviteAddingFailed()

            resp.body = json.dumps({
                "data": add_result,
                "description": "Event invites have been sent successfully!",
                "success": True
            }, default_parser=json.parser)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err
    

class MemberScheduleEventInviteAddSingleResource(object):
    @staticmethod
    def on_post(req, resp):
        (event_id, event_invite_to) = request.get_json_or_form(
            "event_id", "event_invite_to", req=req)

        member = MemberDA().get_member(event_invite_to)
        if not member:
            raise MemberNotFound(member)

        b_event_existing = MemberScheduleEventDA().check_eventExistanceById(event_id)
        if not b_event_existing:
            raise ScheduleEventNotFound(event_id)

        set_params = {
            "event_id": event_id,
            "event_invite_to": event_invite_to   
        }

        add_result = MemberScheduleEventInviteDA().addSingle(**set_params)

        if not add_result:
            raise ScheduleEventInviteAddingFailed()

        resp.body = json.dumps({
            "data": add_result,
            "description": "Event invite has been sent successfully!",
            "success": True
        })
    

class MemberScheduleEventInviteSetStatusResource(object):
    @staticmethod
    def on_post(req, resp):

        [event_invite_id] = request.get_json_or_form("event_invite_id", req=req)
        [event_invite_status] = request.get_json_or_form("event_invite_status", req=req)

        invite = MemberScheduleEventInviteDA().get_event_inviteById(event_invite_id)
        if not invite:
            raise ScheduleEventInviteNotFound(invite)

        set_params = {
            "event_invite_id": event_invite_id,
            "event_invite_status": event_invite_status   
        }

        event_invite_full = MemberScheduleEventInviteDA.setStatus(**set_params)

        resp.body = json.dumps({
            "data": event_invite_full,
            "description": "Event invite status has been updated successfully!",
            "success": True
        }, default_parser=json.parser)
