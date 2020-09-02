import logging
from datetime import timezone, datetime
from uuid import UUID

import app.util.json as json
import app.util.request as request
from app.da.member import MemberDA, MemberContactDA
from app.da.invite import InviteDA
from app.da.group import GroupMembershipDA
from app.util.session import get_session_cookie, validate_session
from app.exceptions.member import MemberNotFound, MemberDataMissing, MemberExists, MemberContactExists, MemberPasswordMismatch
from app.exceptions.invite import InviteNotFound, InviteExpired
from app.exceptions.session import InvalidSessionError, UnauthorizedSession

logger = logging.getLogger(__name__)


class MemberResource(object):

    def on_get(self, req, resp, username=None):
        # We store the key in hex format in the database
        member = MemberDA.get_member_by_username(username=username)

        if not member:
            raise MemberNotFound(username)

        resp.body = json.dumps({
            "username": username,
            "success": True
        })

    def on_post(self, req, resp):
        (search_key) = request.get_json_or_form('search_key', req=req)

        members = MemberDA.get_members(search_key=search_key)

        resp.body = json.dumps({
            "members": members,
            "success": True
        })


class MemberSearchResource(object):

    def on_get(self, req, resp):

        search_key = req.get_param('search_key')
        page_size = req.get_param_as_int('page_size')
        page_number = req.get_param_as_int('page_number')
        exclude_group_id = req.get_param_as_int('exclude_group_id')

        if search_key is None:
            search_key = ''

        members = []

        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            if exclude_group_id:
                members = GroupMembershipDA.get_members_not_in_group(group_id=exclude_group_id, member_id=member_id,
                                                                     search_key=search_key, page_size=page_size,
                                                                     page_number=page_number)
            else:
                members = MemberDA.get_members(member_id=member_id, search_key=search_key, page_size=page_size,
                                               page_number=page_number)

            resp.body = json.dumps({
                "members": members,
                "success": True
            })
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err


class MemberGroupSearchResource(object):

    def on_get(self, req, resp):

        search_key = req.get_param('search_key')
        page_size = req.get_param_as_int('page_size')
        page_number = req.get_param_as_int('page_number')

        if search_key is None:
            search_key = ''

        members = []

        try:

            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            members = MemberDA.get_group_members(member_id=member_id, search_key=search_key, page_size=page_size,
                                                 page_number=page_number)

            resp.body = json.dumps({
                "members": members,
                "success": True
            })
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err


class MemberRegisterResource(object):
    auth = {
        'exempt_methods': ['POST']
    }

    def on_post(self, req, resp, invite_key=None):
        # We store the key in hex format in the database

        (email, password, confirm_password,
         first_name, middle_name, last_name, date_of_birth,
         phone_number, country, city, street,
         postal, state, province) = request.get_json_or_form(
            "email", "password", "confirm_password",
            "first_name", "middle_name", "last_name", "dob",
            "cell", "country", "city", "street", "postal_code",
            "state", "province", req=req)

        if password != confirm_password:
            raise MemberPasswordMismatch()

        if (not email or not password or
                not first_name or not last_name):  # or
            #            not date_of_birth or not phone_number or
            #            not country or not city or not street or not postal):

            raise MemberDataMissing()

        # logger.debug("invite_key: {}".format(invite_key))

        logger.debug("invite_key: {}".format(invite_key))
        logger.debug(": {}".format(email))
        logger.debug("First_name: {}".format(first_name))
        logger.debug("Middle_name: {}".format(middle_name))
        logger.debug("Last_name: {}".format(last_name))
        logger.debug("Password: {}".format(password))

        member = MemberDA.get_member_by_email(email)

        if member:
            raise MemberExists(email)

        # member = MemberDA.get_member_by_email(email)

        # if member:
        #     raise MemberExists(email)

        member_id = MemberDA.register(
            email=email, username=email, password=password,
            first_name=first_name, middle_name=middle_name, last_name=last_name,
            date_of_birth=date_of_birth, phone_number=phone_number,
            country=country, city=city, street=street, postal=postal,
            state=state, province=province, commit=True)

        logger.debug("New registered member_id: {}".format(member_id))

        # Update the invite reference to the newly created member_id
        if invite_key:
            invite_key = invite_key.hex
            InviteDA.update_invite_registered_member(
                invite_key=invite_key, registered_member_id=member_id
            )

            MemberDA.source.commit()

            invite = InviteDA.get_invite(invite_key=invite_key)
            if invite.get("email") != email:
                self._send_email(
                    first_name=first_name,
                    email=email,
                    invite_email=invite.get("email")
                )

        resp.body = json.dumps({
            "member_id": member_id,
            "success": True
        })

    def _send_email(self, first_name, email, invite_email):

        sendmail.send_mail(
            to_email=email,
            subject="Welcome to AMERA Share",
            template="registered",
            data={
                "email": email,
                "invite_email": invite_email
            })


class MemberRoleResource(object):
    pass


class ContactMembersResource(object):
    auth = {
        'exempt_methods': ['POST']
    }

    def on_post(self, req, resp):

        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

        contacts = list()
        contact_member_id_list = req.get_param('member_id_list').split(',')
        for contact_member_id in contact_member_id_list:
            contact_member = MemberDA().get_contact_member(contact_member_id)

            contact_member_params = {
                "member_id": member_id,
                "contact_member_id": contact_member_id,
                "first_name": contact_member['first_name'],
                "last_name": contact_member['last_name'],
                "country": contact_member['country'],
                "cell_phone": contact_member['cell_phone'],
                "office_phone": '',
                "home_phone": '',
                "email": contact_member['email'],
                "personal_email": '',
                "company_name": '',
                "company_phone": '',
                "company_web_site": '',
                "company_email": '',
                "company_bio": '',
                "contact_role": ''
            }

            contact_id = MemberContactDA().create_member_contact(**contact_member_params)
            logger.debug("New created contact_id: {}".format(contact_id))
            contact = {}
            if contact_id:
                contact = MemberContactDA().get_member_contact(contact_id)
            contacts.append(contact)

        resp.body = json.dumps({
            "contacts": contacts,
            "success": True
        }, default_parser=json.parser)

    @staticmethod
    def on_get(req, resp):

        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            members = MemberContactDA.get_members(member_id)

            resp.body = json.dumps({
                "members": members,
                "success": True
            }, default_parser=json.parser)

        except InvalidSessionError as err:
            raise UnauthorizedSession() from err


class MemberContactResource(object):
    auth = {
        'exempt_methods': ['POST']
    }

    def on_post(self, req, resp):

        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

        (first_name, last_name, country, cell_phone,
         office_phone, home_phone, email,
         personal_email, company_name, company_phone, company_web_site,
         company_email, company_bio, role) = request.get_json_or_form(
            "first_name", "last_name", "country", "cell_phone",
            "office_phone", "home_phone", "work_email",
            "personal_email", "company_name", "company_phone_number", "company_website", "company_email",
            "company_bio", "role", req=req)

        member = MemberDA.get_member_by_email(email)

        if not member:
            raise MemberNotFound(email)

        member_contact = MemberContactDA().get_member_contact_by_email(email)
        if member_contact:
            raise MemberContactExists(email)

        new_member_contact_params = {
            "member_id": member_id,
            "contact_member_id": member['member_id'],
            "first_name": first_name,
            "last_name": last_name,
            "country": country,
            "cell_phone": cell_phone,
            "office_phone": office_phone,
            "home_phone": home_phone,
            "email": email,
            "personal_email": personal_email,
            "company_name": company_name,
            "company_phone": company_phone,
            "company_web_site": company_web_site,
            "company_email": company_email,
            "company_bio": company_bio,
            "contact_role": role
        }

        member_contact_id = MemberContactDA().create_member_contact(**
                                                                    new_member_contact_params)
        logger.debug("New created contact_id: {}".format(member_contact_id))
        member_contact = {}
        if member_contact_id:
            member_contact = MemberContactDA().get_member_contact(member_contact_id)

        resp.body = json.dumps({
            "contact": member_contact,
            "success": True
        }, default_parser=json.parser)

    @staticmethod
    def on_get(req, resp):

        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            member_contacts = MemberContactDA.get_member_contacts(member_id)

            resp.body = json.dumps({
                "contacts": member_contacts,
                "success": True
            }, default_parser=json.parser)

        except InvalidSessionError as err:
            raise UnauthorizedSession() from err
