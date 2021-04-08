import logging
from app.util.auth import check_session_administrator, check_session
import app.util.json as json
import app.util.request as request
from app.util.session import get_session_cookie, validate_session
from app.da.activity import ActivityDA
from app.da.session import SessionDA
from app.da.mail import MailServiceDA
from app.da.group import GroupDA
from app.da.member_event import MemberEventDA
from app.da.member import MemberVideoMailDA
from app import settings

from operator import itemgetter

logger = logging.getLogger(__name__)


class SystemActivityBaseResource(object):
    @classmethod
    def _parse_session(self, req, resp):
        session_id = get_session_cookie(req)
        session = validate_session(session_id)

        return session

    @classmethod
    def _parse_params(self, req, resp):
        get_all = req.get_param_as_bool('get_all')
        search_key = req.get_param('search_key') or ''
        page_size = req.get_param_as_int('page_size')
        page_number = req.get_param_as_int('page_number')
        sort_params = req.get_param('sort')

        if get_all:
            return self._get_params_admin(self, req, resp, search_key, page_size, page_number, sort_params, get_all)
        
        return self._get_params_user(self, req, resp, search_key, page_size, page_number, sort_params, get_all)

    @check_session
    def _get_params_user(self, req, resp, *return_params):
        return return_params

    @check_session_administrator
    def _get_params_admin(self, req, resp, *return_params):
        return return_params

class SystemActivitySessionResource(SystemActivityBaseResource):
    def __init__(self):
        self.kafka_data = {
                            "GET": {"uri": {"/system/activity/activity":
                                                 {"event_type": settings.get('kafka.event_types.get.activity_activity'),
                                                   "topic": settings.get('kafka.topics.activity')
                                                },
                                             }
                                    }
                            }

    @classmethod
    def on_get(self, req, resp):
        try:
            (search_key, page_size, page_number, sort_params, get_all) = self._parse_params(req, resp)
            session = self._parse_session(req, resp)
            result = SessionDA.get_sessions(search_key, page_size, page_number, sort_params, get_all, session["member_id"])

            resp.body = json.dumps({
                "success": True,
                "description": "Activity result fetched sucessfully",
                "data": result
            }, default_parser=json.parser)
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            }, default_parser=json.parser)
            logger.exception(err)
            raise err

class SystemActivitySecurityResource(SystemActivityBaseResource):
    def __init__(self):
        self.kafka_data = {
                            "GET": {"uri": {"/system/activity/security":
                                                 {"event_type": settings.get('kafka.event_types.get.activity_security'),
                                                   "topic": settings.get('kafka.topics.activity')
                                                },
                                             }
                                    }
                            }

    @classmethod
    def on_get(self, req, resp):
        try:
            (search_key, page_size, page_number, sort_params, get_all) = self._parse_params(req, resp)
            session = self._parse_session(req, resp)
            result = SessionDA.get_threats(search_key, page_size, page_number, sort_params, get_all, session["member_id"])
            resp.body = json.dumps({
                "success": True,
                "description": "Security result fetched sucessfully",
                "data": result
            }, default_parser=json.parser)
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            }, default_parser=json.parser)
            logger.exception(err)
            raise err

class SystemActivityMessageResource(SystemActivityBaseResource):
    def __init__(self):
        self.kafka_data = {
                            "GET": {"uri": {"/system/activity/message":
                                                 {"event_type": settings.get('kafka.event_types.get.activity_message'),
                                                   "topic": settings.get('kafka.topics.activity')
                                                },
                                             }
                                    }
                            }

    @classmethod
    def on_get(self, req, resp):
        try:
            session = self._parse_session(req, resp)
            (search_key, page_size, page_number, sort_params, get_all) = self._parse_params(req, resp)

            result = ActivityDA.get_mail_activities_by_member_id(session["member_id"], is_history=True, search_key=search_key, page_size=page_size, page_number=page_number, sort_params=sort_params)
            
            # session = self._parse_session(req, resp)
            # text_mails = MailServiceDA.get_all_text_mails(session["member_id"], is_history=True)
            # media_mails = MemberVideoMailDA.get_all_media_mails(session["member_id"], is_history=True)

            # all_mails = text_mails['mails'] + media_mails['mails']
            # total_count = text_mails['count'] + media_mails['count']
            # data = {
            #     "mails": all_mails,
            #     "count": total_count
            # }
            
            resp.body = json.dumps({
                "success": True,
                "description": "Message result fetched sucessfully",
                "data": result
            }, default_parser=json.parser)
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            }, default_parser=json.parser)
            logger.exception(err)
            raise err

class SystemActivityGroupResource(SystemActivityBaseResource):
    def __init__(self):
        self.kafka_data = {
                            "GET": {"uri": {"/system/activity/group":
                                                 {"event_type": settings.get('kafka.event_types.get.activity_group'),
                                                   "topic": settings.get('kafka.topics.activity')
                                                },
                                             }
                                    }
                            }

    @classmethod
    def on_get(self, req, resp):
        try:
            session = self._parse_session(req, resp)
            (search_key, page_size, page_number, sort_params, get_all) = self._parse_params(req, resp)

            result = ActivityDA.get_group_invitations_by_member_id(session["member_id"], is_history=True, search_key=search_key, page_size=page_size, page_number=page_number, sort_params=sort_params)

            # group_invitations = GroupDA.get_all_group_invitations_by_member_id(session["member_id"], is_history=True)
            # event_group_invitations = MemberEventDA.get_all_group_event_invitations_by_member_id(session["member_id"])
            # invitations = group_invitations['groups'] + event_group_invitations['groups']
            # total_count = group_invitations['count'] + event_group_invitations['count']

            # data = {
            #     "invitations": invitations,
            #     "count": total_count
            # }
            resp.body = json.dumps({
                "success": True,
                "description": "Group result fetched sucessfully",
                "data": result
            }, default_parser=json.parser)
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            }, default_parser=json.parser)
            logger.exception(err)
            raise err

class SystemActivityInvitationsResource(SystemActivityBaseResource):
    def __init__(self):
        self.kafka_data = {
                            "GET": {"uri": {"/system/activity/invitations":
                                                 {"event_type": settings.get('kafka.event_types.get.activity_invitations'),
                                                   "topic": settings.get('kafka.topics.activity')
                                                },
                                             }
                                    }
                            }

    @classmethod
    def on_get(self, req, resp):
        try:
            session = self._parse_session(req, resp)
            (search_key, page_size, page_number, sort_params, get_all) = self._parse_params(req, resp)
            
            result = ActivityDA.get_invitations_by_member_id(session["member_id"], is_history=True, search_key=search_key, page_size=page_size, page_number=page_number, sort_params=sort_params)

            # contact invitation
            # contact_invitations = MemberContactDA.get_all_contact_invitations_by_member_id(session["member_id"], is_history=True, search_key=search_key, page_size=page_size, page_number=page_number, sort_params=sort_params)
            # # event invite get_all_event_invitations_by_member_id
            # event_invitations = MemberEventDA.get_all_event_invitations_by_member_id(session["member_id"])
            # # drive files get_all_file_share_invitations_by_member_id
            # drive_sharing = ShareFileDA.get_all_file_share_invitations_by_member_id(session["member_id"])
            
            # invitations = contact_invitations["contacts"] + event_invitations["events"] + drive_sharing["files"]
            # total_count = contact_invitations["count"] + event_invitations["count"] + event_invitations["count"]
            
            resp.body = json.dumps({
                "success": True,
                "description": "Invitations result fetched sucessfully",
                "data": result
            }, default_parser=json.parser)
        except Exception as err:
            resp.body = json.dumps({
                "success": False,
                "description": err
            }, default_parser=json.parser)
            logger.exception(err)
            raise err


