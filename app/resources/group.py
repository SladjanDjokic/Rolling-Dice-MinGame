import uuid
import app.util.json as json
import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from urllib.parse import urljoin

import app.util.request as request
from app.util.session import get_session_cookie, validate_session
from app.config import settings
import app.util.email as sendmail

from app.da.file_sharing import FileStorageDA
from app.da.group import GroupDA, GroupMembershipDA, GroupMemberInviteDA
from app.da.member import MemberDA
from app.exceptions.group import GroupExists, MemberNotFound, MemberExists, GroupNotFound
from app.exceptions.invite import InviteExistsError, InviteDataMissingError,\
    InviteKeyMissing, InviteNotFound, InviteExists,\
    InviteExpired, InviteDataMissing, InviteInvalidInviterError,\
    InviteInvalidInviter, InviteEmailSystemFailure
from app.exceptions.member import MemberExists
from app.exceptions.session import ForbiddenSession

logger = logging.getLogger(__name__)


class MemberGroupResource(object):
    def on_post(self, req, resp):
        (name, pin, members, exchange_option) = request.get_json_or_form(
            "name", "pin", "members", "exchangeOption", req=req)
        
        session_id = get_session_cookie(req)
        session = validate_session(session_id)
        group_leader_id = session["member_id"]
        
        group_exist = GroupDA().get_group_by_name_and_leader_id(group_leader_id, name)
        members = json.loads(members)
        
        if group_exist:
            raise GroupExists(name)
        else:
            file = req.get_param('picture')
            file_id = FileStorageDA().store_file_to_storage(file)
            group_id = GroupDA().create_expanded_group(group_leader_id, name, file_id, pin, exchange_option)
            GroupMembershipDA().bulk_create_group_membership(group_leader_id, group_id, members)
            # self.bulk_create_invite(group_leader_id, group_id, members, req)
            group = list()
            new_group = GroupDA().get_group(group_id)
            group.insert(0, new_group)
            resp.body = json.dumps({
                "data": group,
                "description": "Group created successfully",
                "success": True
            }, default_parser=json.parser)

    @staticmethod
    def on_get(req, resp):
        group_leader_id = req.get_param('groupLeaderId')
        group_list = GroupDA().get_group_list_by_group_leader_id(group_leader_id)
        resp.body = json.dumps({
            "data": group_list,
            "message": "All Group",
            "success": True
        }, default_parser=json.parser)

    def bulk_create_invite(self, inviter_member_id, group_id, members, req):

        expiration = datetime.now() + relativedelta(months=+1)

        for member_id in members:

            invite_key = uuid.uuid4().hex

            member = MemberDA.get_member(member_id)
            member_contact = MemberDA.get_member_contact(member_id)
            member_location = MemberDA.get_member_location(member_id)

            if member is None:
                continue

            invite_params = {
                "registered_member_id": member_id,
                "email": member["email"],
                "first_name": member["first_name"],
                "last_name": member["last_name"],
                "inviter_member_id": inviter_member_id,
                "invite_key": invite_key,
                "group_id": group_id,
                "country": member_location["country"] if member_location else None,
                "phone_number": member_contact["phone_number"] if member_contact else None,
                "expiration": expiration
            }
            try:
                invite_id = GroupMemberInviteDA().create_invite(**invite_params)
                register_url = settings.get(
                    "web.member_invite_register_url"
                ).format(invite_key)

                register_url = urljoin(request.get_url_base(req), register_url)

                # GroupMemberInviteResource._send_email(
                #     email=email,
                #     first_name=first_name,
                #     invite_key=invite_key,
                #     register_url=register_url
                # )

            except sendmail.EmailAuthError:
                continue
            except InviteExistsError:
                continue
            except InviteDataMissingError:
                continue
            except InviteInvalidInviterError:
                continue


class GroupDetailResource(object):
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
    
    def on_delete(self, req, resp, group_id=None):
        session_id = get_session_cookie(req)
        session = validate_session(session_id)
        member_id = session["member_id"]
        
        group = GroupDA().get_group(group_id)

        if not group:
            raise GroupNotFound
        if group["group_leader_id"] != member_id:
            raise ForbiddenSession
        GroupDA().change_group_status(group_id, 'deleted')
        resp.body = json.dumps({
            "data": group,
            "description": "Group deleted successfully!",
            "success": True
        }, default_parser=json.parser)

class GroupMembershipResource(object):
    @staticmethod
    def on_post(req, resp):
        (group_id, group_member_email) = request.get_json_or_form("groupId", "groupMemberEmail", req=req)
        member = MemberDA().get_member_by_email(group_member_email)
        if not member:
            raise MemberNotFound(group_member_email)
        group_member_id = GroupMembershipDA().create_group_membership(group_id, member['member_id'])
        if not group_member_id:
            raise MemberExists(group_member_email)
        group = GroupDetailResource().get_group_detail(group_id)
        resp.body = json.dumps({
            "data": group,
            "description": "Member added successfully!",
            "success": True
        }, default_parser=json.parser)

    @staticmethod
    def on_get(req, resp):
        member_id = req.get_param('member_id')
        group_list = GroupMembershipDA().get_group_by_member_id(member_id)
        resp.body = json.dumps({
            "data": group_list,
            "message": "All Group",
            "status": "success",
            "success": True
        }, default_parser=json.parser)

    @staticmethod
    def on_delete(req, resp):
        (group_id, member_id) = request.get_json_or_form("groupId", "groupMemberId", req=req)
        group_member_id = GroupMembershipDA().remove_group_member(group_id, member_id)
        if not group_member_id:
            raise MemberNotFound
        group = GroupDetailResource().get_group_detail(group_id)
        resp.body = json.dumps({
            "data": group,
            "description": "Member removed successfully!",
            "success": True
        }, default_parser=json.parser)


class GroupMemberInviteResource(object):
    def on_post(self, req, resp):

        logger.debug("Content-Type: {}".format(req.content_type))
        logger.debug("Accepts: {}".format(req.accept))

        session_id = get_session_cookie(req)
        session = validate_session(session_id)
        inviter_member_id = session["member_id"]

        (email, first_name, last_name, group_id, country, phone_number) = request.get_json_or_form(
            "groupMemberEmail", "firstName", "lastName", "groupId", "country", "phoneNumber", req=req
        )

        expiration = datetime.now() + relativedelta(months=+1)

        invite_key = uuid.uuid4().hex
        member = MemberDA.get_member_by_email(email=email)
        if member:
            raise MemberExists(email)

        invite_params = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "inviter_member_id": inviter_member_id,
            "invite_key": invite_key,
            "group_id": group_id,
            "country": country,
            "phone_number": phone_number,
            "expiration": expiration
        }
        try:
            invite_id = GroupMemberInviteDA().create_invite(**invite_params)

            register_url = settings.get(
                "web.member_invite_register_url"
            ).format(invite_key)

            register_url = urljoin(request.get_url_base(req), register_url)

            self._send_email(
                email=email,
                first_name=first_name,
                invite_key=invite_key,
                register_url=register_url
            )

            resp.body = json.dumps({
                "data": invite_id,
                "description": "Invite has been sent successfully!",
                "success": True
            })
        except sendmail.EmailAuthError:
            logger.exception('Deleting invite due to unable \
                             to auth to email system')
            GroupMemberInviteDA.delete_invite(invite_key)
            raise InviteEmailSystemFailure(invite_key)
        except InviteExistsError:
            raise InviteExists(email)
        except InviteDataMissingError:
            del invite_params["invite_key"]
            del invite_params["expiration"]
            raise InviteDataMissing(invite_params)
        except InviteInvalidInviterError:
            raise InviteInvalidInviter(inviter_member_id)

    @staticmethod
    def _send_email(invite_key, email, first_name, register_url):

        sendmail.send_mail(
            to_email=email,
            subject="Welcome to AMERA Share",
            template="welcome",
            data={
                "first_name": first_name,
                "invite_key": invite_key,
                "register_url": register_url
            })
