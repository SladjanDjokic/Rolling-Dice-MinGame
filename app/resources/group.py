import pdb
import uuid
import app.util.json as json
import logging
from pprint import pformat
from datetime import datetime
from dateutil.relativedelta import relativedelta
from urllib.parse import urljoin

import app.util.request as request
from app.util.session import get_session_cookie, validate_session
from app.config import settings
import app.util.email as sendmail

from app.da.file_sharing import FileStorageDA
from app.da.group import GroupDA, GroupMembershipDA, GroupMemberInviteDA
from app.da.file_sharing import FileTreeDA
from app.da.member import MemberDA
from app.exceptions.group import GroupExists, MemberNotFound, MemberExists, GroupNotFound
from app.exceptions.invite import InviteExistsError, InviteDataMissingError,\
    InviteKeyMissing, InviteNotFound, InviteExists,\
    InviteExpired, InviteDataMissing, InviteInvalidInviterError,\
    InviteInvalidInviter, InviteEmailSystemFailure
from app.exceptions.member import MemberExists
from app.exceptions.session import ForbiddenSession
from app.exceptions.session import InvalidSessionError, UnauthorizedSession

logger = logging.getLogger(__name__)


def is_integer(n):
    try:
        float(n)
    except ValueError:
        return False
    else:
        return float(n).is_integer()


class MemberGroupResource(object):
    def on_post(self, req, resp):
        (name, pin, members, exchange_option) = request.get_json_or_form(
            "name", "pin", "members", "exchangeOption", req=req)

        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            group_leader_id = session["member_id"]
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

        group_exist = GroupDA().get_group_by_name_and_leader_id(group_leader_id, name)
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

            # First we create empty file trees
            main_file_tree_id = FileTreeDA().create_tree('main', 'group')
            bin_file_tree_id = FileTreeDA().create_tree('bin', 'group')

            group_id = GroupDA().create_expanded_group(group_leader_id, name,
                                                       file_id, pin,
                                                       exchange_option,
                                                       main_file_tree_id,
                                                       bin_file_tree_id)

            # group_id = GroupDA().create_expanded_group(group_leader_id, name,
            #                                            file_id, pin,
            #                                            exchange_option)
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

    @staticmethod
    def on_get(req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            # group_leader_id = session["member_id"]
            member_id = session["member_id"]
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

        get_all = req.get_param('get_all')
        # sort_params = '-member_group.group_name' names in descending order
        sort_params = req.get_param('sort')

        if get_all:
            resp_list = GroupDA().get_all_groups_by_member_id(
                member_id, sort_params)
        else:
            resp_list = GroupDA().get_groups_by_group_leader_id(
                member_id, sort_params)

        resp.body = json.dumps({
            "data": resp_list,
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

    def on_delete(self, req, resp):
        (group_ids) = request.get_json_or_form("groupIds", req=req)
        group_ids = group_ids[0].split(',')

        session_id = get_session_cookie(req)
        session = validate_session(session_id)
        member_id = session["member_id"]

        delete_status = {}
        for group_id in group_ids:
            group = GroupDA().get_group(group_id)
            if group:
                if group["group_leader_id"] == member_id:
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


class GroupMembershipResource(object):
    @staticmethod
    def on_post(req, resp):
        (group_id, group_member_email) = request.get_json_or_form(
            "groupId", "groupMemberEmail", req=req)
        member = MemberDA().get_member_by_email(group_member_email)
        if not member:
            raise MemberNotFound(group_member_email)
        group_member_id = GroupMembershipDA().create_group_membership(
            group_id, member['member_id'])
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
        if not member_id:
            try:
                session_id = get_session_cookie(req)
                session = validate_session(session_id)
                member_id = session["member_id"]
            except InvalidSessionError as err:
                raise UnauthorizedSession() from err

        # sort_params = '-member_group.group_name' names in descending order
        sort_params = req.get_param('sort')

        group_list = GroupMembershipDA().get_group_membership_by_member_id(
            member_id, sort_params)
        resp.body = json.dumps({
            "data": group_list,
            "message": "All Group",
            "status": "success",
            "success": True
        }, default_parser=json.parser)

    @staticmethod
    def on_delete(req, resp):
        (group_id, member_id) = request.get_json_or_form(
            "groupId", "groupMemberId", req=req)
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

        (email, first_name, last_name, group_id,
            country, country_code, phone_number, role, confirm_phone_required) = request.get_json_or_form(
            "groupMemberEmail", "firstName", "lastName", "groupId",
            "country", "countryCode", "phoneNumber", "role", "confirmPhoneRequired", req=req
        )
        if not country_code and is_integer(country):
            country_code = country
            country = None

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
            "country_code": country_code,
            "phone_number": phone_number,
            "expiration": expiration,
            "role": role,
            "confirm_phone_required": confirm_phone_required
        }
        try:
            invite_id = GroupMemberInviteDA().create_invite(**invite_params)

            # This section here overrides the `access-control-allow-origin`
            # to be dynamic, this means that if the requests come from any
            # domains defined in web.domains, then we allow the origin
            # TODO: Remove this logic
            # request_domain is the domain being used by the original requester
            # we use forwarded_host because these API calls will be proxied in by
            # a load balancer like AWS ELB or NGINX, thus we need to know how
            # this is being requested as:
            #  (e.g. https://ameraiot.com/api/valid-session)
            request_domain = req.env.get('HTTP_ORIGIN', req.forwarded_host)

            logger.debug(f"REQUEST Forwarded Host: {request_domain}")
            logger.debug(f"REQUEST Host: {req.host}")
            logger.debug(f"REQUEST Access Route: {req.access_route}")
            logger.debug(f"REQUEST Netloc: {req.netloc}")
            logger.debug(f"REQUEST Port: {req.port}")
            # logger.debug(f"ENV: {pformat(req.env)}")

            domains = settings.get("web.domains")
            logger.debug(f"REQUEST_DOMAIN: {request_domain}")
            logger.debug(f"ALLOWED_DOMAINS: {pformat(domains)}")
            domains = next((d for d in domains if d in request_domain), None)
            logger.debug(f"DOMAINS FOUND: {domains}")
            register_domain = request_domain
            logger.debug(f"REGISTER DOMAIN: {register_domain}")
            
            register_url = settings.get(
                "web.member_invite_register_url"
            ).format(invite_key)

            register_url = urljoin(request.get_url_base(req), register_url)
            register_url = "/registration/{}".format(invite_key)
            register_url = urljoin(register_domain, register_url)

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


class GroupMembersResource(object):
    @staticmethod
    def on_get(req, resp):

        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            members = MemberDA.get_all_members(member_id)

            resp.body = json.dumps({
                "members": members,
                "success": True
            }, default_parser=json.parser)

        except InvalidSessionError as err:
            raise UnauthorizedSession() from err
