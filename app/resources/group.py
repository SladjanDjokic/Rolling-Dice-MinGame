import app.util.json as json
from app.util.auth import check_session
import logging

import app.util.request as request
from app.config import settings

from app.da.file_sharing import FileStorageDA
from app.da.activity import ActivityDA
from app.da.group import GroupDA, GroupMembershipDA
from app.da.member import MemberDA
from app.exceptions.group import GroupExists, MemberNotFound, MemberExists
from app.exceptions.member import MemberExists

logger = logging.getLogger(__name__)


def is_integer(n):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()


class MemberGroupResource(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.member_group_resource'),
                                    "topic": settings.get('kafka.topics.member')
                                    },
                           "GET": {"event_type": settings.get('kafka.event_types.get.member_group_resource'),
                                   "topic": settings.get('kafka.topics.member')
                                   },
                           "DELETE": {"event_type": settings.get('kafka.event_types.delete.member_group_resource'),
                                      "topic": settings.get('kafka.topics.member')
                                      },
                           }

    @check_session
    def on_post(self, req, resp):
        (name, pin, members, exchange_option) = request.get_json_or_form(
            "name", "pin", "members", "exchangeOption", req=req)
        group_leader_id = req.context.auth['session']['member_id']
        group_exist = GroupDA().get_group_by_name_and_owner_id(group_leader_id, name)
        members = json.loads(members)

        if group_exist:
            raise GroupExists(name)
        else:
            file_id = None
            group_id = None
            if exchange_option != 'NO_ENCRYPTION':
                file = req.get_param('picture')
                if file != '':
                    file_id = FileStorageDA().put_file_to_storage(file)
            else:
                pin = None

            group_id = GroupDA().create_group_with_trees(
                name=name, file_id=file_id, pin=pin, exchange_option=exchange_option, group_type='contact')

            GroupMembershipDA().bulk_create_group_membership(
                group_leader_id, group_id, members)
            # self.bulk_create_invite(group_leader_id, group_id, members, req)
            group = list()
            new_group = GroupDA().get_group(group_id)
            group.insert(0, new_group)
            resp.body = json.dumps({
                "data": group,
                "description": "Group created successfully",
                "success": True
            }, default_parser=json.parser)
            return

    @check_session
    def on_get(self, req, resp):
        member_id = req.context.auth['session']['member_id']

        get_all = req.get_param_as_bool(
            'get_all',
            blank_as_true=False,
            required=False,
            default=False
        )
        # sort_params = '-member_group.group_name' names in descending order
        sort_params = req.get_param('sort')
        search_key = req.get_param('searchKey')
        page_size = req.get_param_as_int('pageSize')
        page_number = req.get_param_as_int('pageNumber')

        if get_all:
            result = GroupDA.get_all_groups_by_member_id(
                member_id, sort_params=sort_params, search_key=search_key, 
                page_size=page_size, page_number=page_number)
        else:
            result = GroupDA.get_groups_by_group_leader_id(
                group_leader_id=member_id, sort_params=sort_params, search_key=search_key, 
                page_size=page_size, page_number=page_number)

        resp.body = json.dumps({
            "data": result["groups"],
            "count": result["count"],
            "success": True
        }, default_parser=json.parser)

    # def bulk_create_invite(self, inviter_member_id, group_id, members, req):

    #     expiration = datetime.now() + relativedelta(months=+1)

    #     for member_id in members:

    #         invite_key = uuid.uuid4().hex

    #         member = MemberDA.get_member(member_id)
    #         member_contact = MemberDA.get_member_contact(member_id)
    #         member_location = MemberDA.get_member_location(member_id)

    #         if member is None:
    #             continue

    #         invite_params = {
    #             "registered_member_id": member_id,
    #             "email": member["email"],
    #             "first_name": member["first_name"],
    #             "last_name": member["last_name"],
    #             "inviter_member_id": inviter_member_id,
    #             "invite_key": invite_key,
    #             "group_id": group_id,
    #             "country": member_location["country"] if member_location else None,
    #             "phone_number": member_contact["phone_number"] if member_contact else None,
    #             "expiration": expiration
    #         }
    #         try:
    #             invite_id = MemberInviteContactDA().create_invite(**invite_params)
    #             register_url = settings.get(
    #                 "web.member_invite_register_url"
    #             ).format(invite_key)

    #             register_url = urljoin(request.get_url_base(req), register_url)

    #             # GroupMemberInviteResource._send_email(
    #             #     email=email,
    #             #     first_name=first_name,
    #             #     invite_key=invite_key,
    #             #     register_url=register_url
    #             # )

    #         except sendmail.EmailAuthError:
    #             continue
    #         except InviteExistsError:
    #             continue
    #         except InviteDataMissingError:
    #             continue
    #         except InviteInvalidInviterError:
    #             continue

    @check_session
    def on_delete(self, req, resp):
        (group_ids) = request.get_json_or_form("groupIds", req=req)
        group_ids = group_ids[0].split(',')

        member_id = req.context.auth['session']['member_id']

        delete_status = {}
        for group_id in group_ids:
            group = GroupDA().get_group(group_id)
            if group:
                if group["group_leader_id"] == member_id:  # FIXME:
                    GroupDA().change_group_status(group_id, 'deleted')
                    delete_status[group_id] = True
                else:
                    delete_status[group_id] = False
            else:
                delete_status[group_id] = False

        resp.body = json.dumps({
            "data": delete_status,
            "description": "Group's deleted successfully!",
            "success": True
        }, default_parser=json.parser)


class GroupDetailResource(object):

    def __init__(self):
        self.kafka_data = {
            "GET": {"event_type": settings.get('kafka.event_types.get.member_group_detail'),
                    "topic": settings.get('kafka.topics.member')
                    },
        }

    def on_get(self, req, resp, group_id=None):
        # TODO: Build pagination
        group = self.get_group_detail(group_id)
        resp.body = json.dumps({
            "data": group,
            "message": "Group Detail",
            "status": "success",
            "success": True
        }, default_parser=json.parser)

    @staticmethod
    def get_group_detail(group_id):
        group = GroupDA().get_group(group_id)
        members = GroupMembershipDA().get_members_by_group_id(group_id)
        group['members'] = members
        group['total_member'] = len(members)
        return group

    @check_session
    def on_put(self, req, resp, group_id=None):
        try:
            (group_name, ) = request.get_json_or_form(
                "group_name", req=req
            )
            GroupDA().update_group_name(group_id, group_name)

            resp.body = json.dumps({
                    "data": {
                        'group_name': group_name
                    },
                    "description": "Group Updated Successfully.",
                    "success": True
                }, default_parser=json.parser)
        except:
            resp.body = json.dumps({
                "data": {},
                "description": "Something went wrong!",
                "success": False
            })


class GroupMembershipResource(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.group_crud'),
                                    "topic": settings.get('kafka.topics.member')
                                    },
                           "GET": {"event_type": settings.get('kafka.event_types.get.group_crud'),
                                   "topic": settings.get('kafka.topics.member')
                                   },
                           "DELETE": {"event_type": settings.get('kafka.event_types.delete.group_crud'),
                                      "topic": settings.get('kafka.topics.member')
                                      },
                           }


    @staticmethod
    def on_post(req, resp):
        (group_id, contact_member_id) = request.get_json_or_form(
            "group_id", "contact_member_id", req=req)
        member = MemberDA().get_member(contact_member_id)
        if not member:
            raise MemberNotFound(contact_member_id)
        req.headers['kafka_invitee_id'] = member.get('member_id')
        group_member_id = GroupMembershipDA().create_group_membership(
            group_id, member['member_id'])
        if not group_member_id:
            raise MemberExists(member['member_id'])
        group = GroupDetailResource().get_group_detail(group_id)
        req.headers['kafka_group_name'] = group.get('group_name')
        resp.body = json.dumps({
            "data": group,
            "description": "Member added successfully!",
            "success": True
        }, default_parser=json.parser)

    @check_session
    def on_get(self, req, resp):
        member_id = req.get_param('member_id')
        if not member_id:
            member_id = req.context.auth['session']['member_id']

        # sort_params = '-member_group.group_name' names in descending order
        sort_params = req.get_param('sort')
        search_key = req.get_param('search_key')
        page_size = req.get_param_as_int('pageSize')
        page_number = req.get_param_as_int('pageNumber')

        result = GroupDA().get_all_groups_by_member_id(
            member_id=member_id, member_only=True, sort_params=sort_params, 
            search_key=search_key, page_size=page_size, page_number=page_number)

        resp.body = json.dumps({
            "data": result['groups'],
            "count": result['count'],
            "message": "All Group",
            "status": "success",
            "success": True
        }, default_parser=json.parser)

    @staticmethod
    def on_delete(req, resp):
        (group_ids, member_id) = request.get_json_or_form(
            "groupIds", "groupMemberId", req=req)

        group_ids = group_ids.split(',')

        delete_status = []
        for group_id in group_ids:
            id = GroupMembershipDA().remove_group_member(group_id, member_id)
            if id:
                delete_status.append({ 
                    "group_id" : group_id,
                    "member_id": member_id,
                    "status": True
                })
            else:
                delete_status.append({
                    "group_id" : group_id,
                    "member_id": member_id,
                    "status": False
                })
        
        # group = GroupDetailResource().get_group_detail(group_id)
        resp.body = json.dumps({
            "data": delete_status,
            "description": "Member's removed successfully!",
            "success": True
        }, default_parser=json.parser)


# class GroupMemberInviteResource(MemberInviteResource):

#     def __init__(self):
#         self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.group_non_member_invite'),
#                                     "topic": settings.get('kafka.topics.member')
#                                     }
#                            }

#     def on_post(self, req, resp):

#         logger.debug("Content-Type: {}".format(req.content_type))
#         logger.debug("Accepts: {}".format(req.accept))

#         session_id = get_session_cookie(req)
#         session = validate_session(session_id)
#         inviter_member_id = session["member_id"]

#         (email, first_name, last_name, group_id,
#             country, country_code, phone_number, role, confirm_phone_required,
#             company_id, company_name) = request.get_json_or_form(
#             "groupMemberEmail", "firstName", "lastName", "groupId",
#             "country", "countryCode", "phoneNumber", "role", "confirmPhoneRequired",
#             "company_id", "company_name", req=req
#         )
#         if not country_code and is_integer(country):
#             country_code = country
#             country = None

#         expiration = datetime.now() + relativedelta(months=+1)

#         invite_key = uuid.uuid4().hex
#         member = MemberDA.get_member_by_email(email=email)
#         if member:
#             raise MemberExists(email)

#         invite_params = {
#             "email": email,
#             "first_name": first_name,
#             "last_name": last_name,
#             "inviter_member_id": inviter_member_id,
#             "invite_key": invite_key,
#             "group_id": group_id,
#             "country": country,
#             "country_code": country_code,
#             "phone_number": phone_number,
#             "expiration": expiration,
#             "role": role,
#             "confirm_phone_required": confirm_phone_required,
#             "company_id": company_id if company_id!='null' else None,
#             "company_name": company_name if company_name!='null' else None
#         }

#         try:
#             invite_id = MemberInviteContactDA().create_invite(**invite_params)

#             register_url = self._get_register_url(req, invite_key)

#             self._send_email(
#                 email=email,
#                 first_name=first_name,
#                 invite_key=invite_key,
#                 register_url=register_url
#             )

#             resp.body = json.dumps({
#                 "data": invite_id,
#                 "description": "Invite has been sent successfully!",
#                 "success": True
#             })
#         except sendmail.EmailAuthError:
#             logger.exception('Deleting invite due to unable \
#                              to auth to email system')
#             MemberInviteContactDA.delete_invite(invite_key)
#             raise InviteEmailSystemFailure(invite_key)
#         except InviteExistsError:
#             raise InviteExists(email)
#         except InviteDataMissingError:
#             del invite_params["invite_key"]
#             del invite_params["expiration"]
#             raise InviteDataMissing(invite_params)
#         except InviteInvalidInviterError:
#             raise InviteInvalidInviter(inviter_member_id)

#     @staticmethod
#     def _send_email(invite_key, email, first_name, register_url):

#         sendmail.send_mail(
#             to_email=email,
#             subject="Welcome to AMERA Share",
#             template="welcome",
#             data={
#                 "first_name": first_name,
#                 "invite_key": invite_key,
#                 "register_url": register_url
#             })


class GroupMemberAccept(object):
    def __init__(self):
        self.kafka_data = {"PUT": {"event_type": settings.get('kafka.event_types.put.group_membership_response'),
                                   "topic": settings.get('kafka.topics.member')
                                   }
                           }

    @check_session
    def on_put(self, req, resp, group_id=None):
        member_id = req.context.auth['session']['member_id']

        try:
            (status, ) = request.get_json_or_form(
                "status", req=req
            )

            GroupMembershipDA.accept_group_invitation(
                group_id, member_id, status)
            # Headers set for kafka topic routing for notifications
            req.headers['kafka_group_id'] = str(group_id)
            req.headers['kafka_group_status'] = status
            resp.body = json.dumps({
                "description": "Successfully done",
                "success": True
            }, default_parser=json.parser)
        except Exception as err:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            })


class GroupMembersResource(object):

    def __init__(self):
        self.kafka_data = {"GET": {"event_type": settings.get('kafka.event_types.get.retrieve_all_group_members'),
                                   "topic": settings.get('kafka.topics.member')
                                   }
                           }

    @check_session
    def on_get(self, req, resp):

        member_id = req.context.auth['session']['member_id']
        members = MemberDA.get_all_members(member_id)
        resp.body = json.dumps({
            "members": members,
            "success": True
        }, default_parser=json.parser)


class MemberGroupSecurity(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.member_group_security'),
                                    "topic": settings.get('kafka.topics.member')
                                    },
                           "GET": {"event_type": settings.get('kafka.event_types.get.member_group_security'),
                                   "topic": settings.get('kafka.topics.member')
                                   },
                           }

    @check_session
    def on_get(self, req, resp, group_id=None):
        member_id = req.context.auth['session']['member_id']

        try:
            security = GroupDA().get_security(group_id)
            resp.body = json.dumps({
                "data": security,
                "success": True
            }, default_parser=json.parser)
        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    @check_session
    def on_post(self, req, resp, group_id=None):
        (picture, pin, exchange_option) = request.get_json_or_form(
            "picture", "pin", "exchange_option", req=req)

        security = GroupDA().get_security(group_id)

        picture_file_id = security["picture_file_id"]
        if picture is not None:
            picture_file_id = FileStorageDA().put_file_to_storage(picture)
        security_params = {
            "group_id": group_id,
            "picture_file_id": picture_file_id,
            "pin": pin,
            "exchange_option": exchange_option
        }
        try:
            GroupDA().update_security(**security_params)
            resp.body = json.dumps({
                "description": "Successfully saved",
                "success": True
            }, default_parser=json.parser)
        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)


class GroupActivityDriveResource(object):
    @check_session
    def on_get(self, req, resp, group_id=None):
        member_id = req.context.auth['session']['member_id']
        try:
            search_key = req.get_param('search_key') or ''
            page_size = req.get_param_as_int('page_size')
            page_number = req.get_param_as_int('page_number')
            sort_params = req.get_param('sort')
            drive_activity = ActivityDA().get_group_drive_activity(
                group_id, search_key, page_size, page_number, sort_params)
            resp.body = json.dumps({
                "data": drive_activity,
                "success": True
            }, default_parser=json.parser)
        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)


class GroupActivityCalendarResource(object):
    @check_session
    def on_get(self, req, resp, group_id=None):
        member_id = req.context.auth['session']['member_id']
        try:
            search_key = req.get_param('search_key') or ''
            page_size = req.get_param_as_int('page_size')
            page_number = req.get_param_as_int('page_number')
            sort_params = req.get_param('sort')
            calendar_activity = ActivityDA().get_group_calendar_activity(
                group_id, search_key, page_size, page_number, sort_params)
            resp.body = json.dumps({
                "data": calendar_activity,
                "success": True
            }, default_parser=json.parser)
        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)
