import logging
from datetime import timezone, datetime
from uuid import UUID

import app.util.json as json
import app.util.request as request
from app.da.member import MemberDA, MemberContactDA, MemberInfoDA
from app.da.file_sharing import FileStorageDA
from app.da.invite import InviteDA
from app.da.group import GroupMembershipDA, GroupDA
from app.da.promo_codes import PromoCodesDA
from app.util.session import get_session_cookie, validate_session
from app.exceptions.member import MemberNotFound, MemberDataMissing, MemberExists, MemberContactExists, MemberPasswordMismatch
from app.exceptions.invite import InviteNotFound, InviteExpired
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
import app.util.email as sendmail


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

        (city, state, pin, email, password, confirm_password, first_name, last_name, date_of_birth,
         phone_number, country, postal, company_name, job_title_id, profilePicture,
         cell_confrimation_ts, email_confrimation_ts, promo_code_id, department_id) = request.get_json_or_form(
            "city", "state", "pin", "email", "password", "confirm_password", "first_name", "last_name", "dob",
            "cell", "country", "postal_code", "company_name", "job_title_id", "profilePicture",
            "cellConfirmationTS", "emailConfirmationTS", "activatedPromoCode", "department_id", req=req)

        if password != confirm_password:
            raise MemberPasswordMismatch()

        logger.debug(f"Job Title ID: {job_title_id} and {type(job_title_id)}")
        if job_title_id:
            job_title_id = job_title_id.strip() or None

        if department_id:
            department_id = department_id.strip() or None

        if (not email or not password or
                not first_name or not last_name):  # or
            #            not date_of_birth or not phone_number or
            #            not country or not city or not street or not postal):

            raise MemberDataMissing()

        # logger.debug("invite_key: {}".format(invite_key))

        logger.debug("invite_key: {}".format(invite_key))
        logger.debug("email: {}".format(email))
        logger.debug("First_name: {}".format(first_name))
        # logger.debug("Middle_name: {}".format(middle_name))
        logger.debug("Last_name: {}".format(last_name))
        logger.debug("Password: {}".format(password))
        logger.debug("Company name: {}".format(company_name))
        # logger.debug("group id: {}".format(group_id))

        member = MemberDA.get_member_by_email(email)

        if member:
            raise MemberExists(email)

        # Upload image to aws and create an entry in db
        avatar_storage_id = None
        #print(f"TYPE PICTURE {type(profilePicture)}")
        #print(f"PICTURE {profilePicture}")
        #print(f"PICTURE MATCH {type(profilePicture) == 'falcon_multipart.parser.Parser'}")

        if profilePicture is not None:
            avatar_storage_id = FileStorageDA().store_file_to_storage(profilePicture)

        logger.debug(f"Job Title ID: {job_title_id} and {type(job_title_id)}")

        if not job_title_id:
            job_title_id = None

        if not department_id:
            department_id = None

        if not country:
            country = 'US'

        member_id = MemberDA.register(
            city=city, state=state, pin=pin, avatar_storage_id=avatar_storage_id, email=email, username=email, password=password,
            first_name=first_name, last_name=last_name, company_name=company_name, job_title_id=job_title_id,
            date_of_birth=date_of_birth, phone_number=phone_number,
            country=country, postal=postal, cell_confrimation_ts=cell_confrimation_ts, email_confrimation_ts=email_confrimation_ts,
            department_id=department_id, commit=True)
        logger.debug("New registered member_id: {}".format(member_id))

        group = None
        if invite_key:
            invite_key = invite_key.hex
            invite = InviteDA.get_invite(invite_key=invite_key)
            inviter_member_id = invite.get('inviter_member_id')
            role_id = invite.get('role_id')
            group_id = invite.get('group_id')

            logger.debug(f"inviter_member_id: {inviter_member_id}")
            logger.debug(f"role_id: {role_id}")
            logger.debug(f"group_id: {group_id}")

            # invitee contact info for inviter
            MemberContactDA.create_member_contact(member_id=inviter_member_id,
                                                  contact_member_id=member_id, first_name=first_name, last_name=last_name, country=country,
                                                  cell_phone=phone_number, office_phone='',  home_phone='', email=email,
                                                  personal_email='', company_name=company_name, company_phone='', company_web_site='',
                                                  company_email='', company_bio='', contact_role='', role_id=role_id)

            # inviter contact info for invitee
            inviter = MemberDA.get_contact_member(inviter_member_id)
            if inviter:
                (inviter_first_name, inviter_last_name, inviter_country,
                    inviter_phone_number, inviter_email, inviter_company_name,
                    inviter_role_id) = [inviter[k] for k in ('first_name', 'last_name', 'country', 'cell_phone', 'email', 'company_name', 'role_id')]

                # contact for invitee
                MemberContactDA.create_member_contact(member_id=member_id,
                                                      contact_member_id=inviter_member_id, first_name=inviter_first_name, last_name=inviter_last_name,
                                                      country=inviter_country, cell_phone=inviter_phone_number, office_phone='',  home_phone='',
                                                      email=inviter_email, personal_email='', company_name=inviter_company_name, company_phone='',
                                                      company_web_site='', company_email='', company_bio='', contact_role='',
                                                      role_id=inviter_role_id)

            if group_id:
                GroupMembershipDA().create_group_membership(group_id, member_id)
                group = MemberRegisterResource.get_group_detail(group_id)

            # Update the invite reference to the newly created member_id
            InviteDA.update_invite_registered_member(invite_key=invite_key, registered_member_id=member_id
                                                     )

            MemberDA.source.commit()
            if invite.get("email") != email:
                self._send_email(
                    first_name=first_name,
                    email=email,
                    invite_email=invite.get("email")
                )

        # Update the promo code reference for the newly created member_id
        if promo_code_id != "null":
            PromoCodesDA().create_activation_entry(member_id, promo_code_id)

        resp.body = json.dumps({
            "member_id": member_id,
            "data": group,
            "description": "Registered Successfully!",
            "success": True
        }, default_parser=json.parser)

    def _send_email(self, first_name, email, invite_email):
        sendmail.send_mail(
            to_email=email,
            subject="Welcome to AMERA Share",
            template="registered",
            data={
                "email": email,
                "invite_email": invite_email
            })

    @staticmethod
    def get_group_detail(group_id):
        group = GroupDA().get_group(group_id)
        members = GroupMembershipDA().get_members_by_group_id(group_id)
        group['members'] = members
        group['total_member'] = len(members)
        return group


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
                "contact_role": '',
                "role_id": None
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

    def on_delete(self, req, resp):
        (contact_ids) = request.get_json_or_form("contactIds", req=req)
        contact_ids = contact_ids[0].split(',')

        delete_status = {}
        for contact_id in contact_ids:
            try:
                MemberContactDA().delete_contact(contact_id)
                delete_status[contact_id] = True
            except:
                delete_status[contact_id] = False

        resp.body = json.dumps({
            "data": delete_status,
            "description": "Contact's deleted successfully!",
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

    def on_put(self, req, resp):
        (id, role_id, role) = request.get_json_or_form(
            "id", "role_id", "role", req=req)

        if id and role_id and role:
            try:
                MemberContactDA.update_member_contact_role(
                    contact_id=id, contact_role_id=role_id, contact_role=role
                )
                resp.body = json.dumps({
                    "description": 'Contact updated successfully',
                    "success": True
                }, default_parser=json.parser)
            except Exception as e:
                resp.body = json.dumps({
                    "description": 'Failed to update contact role!',
                    "success": False
                }, default_parser=json.parser)
        return

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


class MemberInfoResource(object):
    @staticmethod
    def on_get(req, resp):

        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            member_info = MemberInfoDA().get_member_info(member_id)

            resp.body = json.dumps({
                "member": member_info,
                "success": True
            }, default_parser=json.parser)

        except InvalidSessionError as err:
            raise UnauthorizedSession() from err


class MemberJobTitles(object):
    auth = {
        'exempt_methods': ['GET']
    }

    def on_get(self, req, resp):
        job_title_list = MemberDA().get_job_list()
        department_list = MemberDA().get_department_list()
        # TODO: Replace with try/except and raise an exception
        # if unable to get a list
        if job_title_list and department_list:
            resp.body = json.dumps({
                "data": {"job_list": job_title_list, "deps_list": department_list},
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Could not get the job title or department list",
                "success": False
            }, default_parser=json.parser)


class MemberTerms(object):
    auth = {
        'exempt_methods': ['GET']
    }

    def on_get(self, req, resp):
        # fetch all terms and conditions from db
        # send them back
        terms = MemberDA().get_terms()

        if terms:
            resp.body = json.dumps({
                "data": terms,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Could not get the terms and conditions",
                "success": False
            }, default_parser=json.parser)
