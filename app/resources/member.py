import logging
from datetime import timezone, datetime
from uuid import UUID

import app.util.json as json
import app.util.request as request
from app.util.auth import check_session
from app import settings
from app.da.member import MemberDA, MemberContactDA, MemberInfoDA, MemberSettingDA, MemberVideoMailDA
from app.da.file_sharing import FileStorageDA, FileTreeDA
from app.da.invite import InviteDA
from app.da.group import GroupMembershipDA, GroupDA
from app.da.promo_codes import PromoCodesDA
from app.da.member import MemberInfoDA
from app.da.company import CompanyDA
from app.util.session import get_session_cookie, validate_session
from app.exceptions.member import MemberExistsError, MemberNotFound, MemberDataMissing, MemberExists, MemberContactExists, MemberPasswordMismatch
from app.exceptions.invite import InviteNotFound, InviteExpired
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
from app.da.member import MemberContactDA, MemberVideoMailDA
from app.da.mail import MailServiceDA
from app.da.project import ProjectDA
import app.util.email as sendmail

logger = logging.getLogger(__name__)


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

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.member_registration'),
                                    "topic": settings.get('kafka.topics.registration')
                                    },
                           }

    auth = {
        'exempt_methods': ['POST']
    }

    def on_post(self, req, resp, invite_key=None):

        (city, state, province, pin, email, password, confirm_password, first_name, last_name, date_of_birth,
         phone_number, country, postal, company_name, job_title_id, profilePicture,
         cell_confrimation_ts, email_confrimation_ts, promo_code_id, department_id, company_id, ) = request.get_json_or_form(
            "city", "state", "province", "pin", "email", "password", "confirm_password", "first_name", "last_name", "dob",
            "cell", "country", "postal_code", "company_name", "job_title_id", "profilePicture",
            "cellConfirmationTS", "emailConfirmationTS", "activatedPromoCode", "department_id", "company_id", req=req)
        try:
            # We store the key in hex format in the database

            if password != confirm_password:
                raise MemberPasswordMismatch()

            logger.debug(
                f"Job Title ID: {job_title_id} and {type(job_title_id)}")

            job_title_id = None if job_title_id == 'not_applicable' else job_title_id
            department_id = None if department_id == 'not_applicable' else department_id
            company_name = None if company_name == 'null' else company_name
            company_id = None if company_id == 'null' else company_id

            if company_id is not None:
                company_name = None
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
                raise MemberExistsError

            # Upload image to aws and create an entry in db
            avatar_storage_id = None
            # print(f"TYPE PICTURE {type(profilePicture)}")
            # print(f"PICTURE {profilePicture}")
            # print(f"PICTURE MATCH {type(profilePicture) == 'falcon_multipart.parser.Parser'}")

            if profilePicture is not None:
                avatar_storage_id = FileStorageDA().put_file_to_storage(profilePicture)

            # logger.debug(
                # f"Job Title ID: {job_title_id} and {type(job_title_id)}")

            # First we create empty file trees
            tree_id, file_tree_id = FileTreeDA().create_tree('main', 'member', True)
            bin_file_tree_id = FileTreeDA().create_tree('bin', 'member')
            main_file_tree_id = tree_id

            # Add default folders for Drive
            default_drive_folders = settings.get('drive.default_folders')
            default_drive_folders.sort()

            for folder_name in default_drive_folders:
                FileTreeDA().create_file_tree_entry(
                    tree_id=main_file_tree_id,
                    parent_id=file_tree_id,
                    member_file_id=None,
                    display_name=folder_name
                )

            member_id = MemberDA.register(
                city=city, state=state, province=province, pin=pin, avatar_storage_id=avatar_storage_id, email=email, username=email, password=password,
                first_name=first_name, last_name=last_name, company_name=company_name, job_title_id=job_title_id,
                date_of_birth=date_of_birth, phone_number=phone_number,
                country=country, postal=postal, cell_confrimation_ts=cell_confrimation_ts, email_confrimation_ts=email_confrimation_ts,
                department_id=department_id, main_file_tree_id=main_file_tree_id, bin_file_tree_id=bin_file_tree_id, commit=True)
            logger.debug("New registered member_id: {}".format(member_id))

            if member_id:
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
                                                          contact_member_id=member_id, status='active', first_name=first_name, last_name=last_name, country=country,
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
                                                              contact_member_id=inviter_member_id, status='active', first_name=inviter_first_name, last_name=inviter_last_name,
                                                              country=inviter_country, cell_phone=inviter_phone_number, office_phone='',  home_phone='',
                                                              email=inviter_email, personal_email='', company_name=inviter_company_name, company_phone='',
                                                              company_web_site='', company_email='', company_bio='', contact_role='',
                                                              role_id=inviter_role_id)

                    if group_id:
                        GroupMembershipDA().create_group_membership(group_id, member_id)
                        group = MemberRegisterResource.get_group_detail(
                            group_id)

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

                if company_id is not None:
                    CompanyDA.add_member(company_id, member_id, 'standard')

                resp.body = json.dumps({
                    "member_id": member_id,
                    "data": group,
                    "description": "Registered Successfully!",
                    "success": True
                }, default_parser=json.parser)
        except MemberExistsError as err:
            raise MemberExists(email) from err
        except Exception as err:
            logger.exception(f"Unknown exception creating member {email}")
            logger.error(f"Error Creating Member: {err}")
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
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

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.create_contact'),
                                    "topic": settings.get('kafka.topics.contact')
                                    },
                           "DELETE": {"event_type": settings.get('kafka.event_types.delete.delete_contact'),
                                      "topic": settings.get('kafka.topics.contact')
                                      },
                           "GET": {"event_type": settings.get('kafka.event_types.get.get_members'),
                                   "topic": settings.get('kafka.topics.contact')
                                   },

                           }

    @check_session
    def on_post(self, req, resp):
        member_id = req.context.auth["session"]["member_id"]
        # contacts = list()
        contact_member_id_list = req.get_param('member_id_list').split(',')
        req.headers['kafka_contact_id_list'] = json.dumps(
            contact_member_id_list)
        for contact_member_id in contact_member_id_list:
            contact_member = MemberDA().get_contact_member(contact_member_id)

            contact_member_params = {
                "member_id": member_id,
                "contact_member_id": contact_member_id,
                "status": "requested",
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
            # contacts.append(contact)

            contact_member = MemberDA().get_contact_member(member_id)

            contact_member_params = {
                "member_id": contact_member_id,
                "contact_member_id": member_id,
                "status": "pending",
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

        contacts = MemberContactDA().get_member_contacts(
            member_id=member_id, sort_params=None, filter_params=None)

        resp.body = json.dumps({
            "contacts": contacts,
            "success": True
        }, default_parser=json.parser)

    @check_session
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

    @check_session
    def on_get(self, req, resp):
        member_id = req.context.auth["session"]["member_id"]

        # sort_by_params = 'first_name, last_name, -company' or '+first_name, +last_name, -company'
        sort_params = req.get_param('sort')

        members = MemberContactDA.get_members(member_id, sort_params)

        resp.body = json.dumps({
            "members": members,
            "success": True
        }, default_parser=json.parser)


class ContactMembersOtherInvitationsResource(object):

    def __init__(self):
        self.kafka_data = {
            "GET": {"event_type": settings.get('kafka.event_types.get.other_invitations'),
                    "topic": settings.get('kafka.topics.event')
                    },

        }

    def on_get(self, req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            # contact invitation
            contact_invitations = MemberContactDA.get_all_contact_invitations_by_member_id(
                member_id)
            # new text message
            new_messages = MailServiceDA.get_all_text_mails(member_id)
            # new media message
            new_media_messages = MemberVideoMailDA.get_all_media_mails(
                member_id)
            # group invite
            group_invitations = GroupDA.get_all_group_invitations_by_member_id(
                member_id)            # project contract invite
            contract_invitations = ProjectDA.get_member_contract_invites(
                member_id)
            if not contract_invitations:
                contract_invitations = []

            result = contact_invitations + new_messages + \
                new_media_messages + group_invitations + contract_invitations

            resp.body = json.dumps({
                "data": result,
                "description": "Other Invitations result fetched sucessfully",
                "success": True
            }, default_parser=json.parser)
        except Exception as err:
            resp.body = json.dumps({
                "description": err,
                "success": False
            }, default_parser=json.parser)


class MemberContactResource(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.create_contact'),
                                    "topic": settings.get('kafka.topics.contact')
                                    },
                           "PUT": {"event_type": settings.get('kafka.event_types.put.update_member_contact'),
                                   "topic": settings.get('kafka.topics.contact')
                                   },
                           }

    auth = {
        'exempt_methods': ['POST']
    }

    @check_session
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

    @check_session
    def on_post(self, req, resp):
        member_id = req.context.auth["session"]["member_id"]

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
        req.headers['kafka_single_contact_add_member_id'] = str(member_id)
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

    @check_session
    def on_get(self, req, resp):
        member_id = req.context.auth["session"]["member_id"]

        # sort_by_params = 'first_name, last_name, -company' or '+first_name, +last_name, -company'
        search_key = req.get_param('searchKey') or ''
        page_size = req.get_param_as_int('pageSize')
        page_number = req.get_param_as_int('pageNumber')
        sort_params = req.get_param('sort')
        filter_params = req.get_param('filter')

        result = MemberContactDA.get_member_contacts(
            member_id, sort_params, filter_params,
            search_key, page_size, page_number
        )

        resp.body = json.dumps({
            "contacts": result['contacts'],
            "count": result['count'],
            "success": True
        }, default_parser=json.parser)


class MemberContactSecurity(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.create_contact_security'),
                                    "topic": settings.get('kafka.topics.contact')
                                    },
                           "GET": {"event_type": settings.get('kafka.event_types.get.contact_security'),
                                   "topic": settings.get('kafka.topics.contact')
                                   },
                           }

    @check_session
    def on_get(self, req, resp, contact_member_id=None):
        member_id = req.context.auth["session"]["member_id"]

        try:
            security_info = MemberContactDA.get_security(
                member_id, contact_member_id)
            resp.body = json.dumps({
                "data": security_info,
                "success": True
            }, default_parser=json.parser)
        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    @check_session
    def on_post(self, req, resp, contact_member_id=None):
        member_id = req.context.auth["session"]["member_id"]

        try:

            (pin, picture, exchangeOption) = request.get_json_or_form(
                "pin", "picture", "exchangeOption", req=req)

            # Upload image to aws and create an entry in db

            security = MemberContactDA.get_security(
                member_id, contact_member_id)
            security_picture_storage_id = security["security_picture_storage_id"]
            logger.debug("pin: {}".format(pin))
            if picture is not None:
                security_picture_storage_id = FileStorageDA().put_file_to_storage(picture)

            security_params = {
                "member_id": member_id,
                "contact_member_id": contact_member_id,
                "security_picture_storage_id": security_picture_storage_id,
                "security_pin": pin,
                "exchangeOption": exchangeOption
            }

            MemberContactDA.update_security(**security_params)

            resp.body = json.dumps({
                "description": "Stored Successfully!",
                "success": True
            }, default_parser=json.parser)
        except expression as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)


class MemberContactsRoles(object):
    @check_session
    def on_get(self, req, resp):
        member_id = req.context.auth["session"]["member_id"]

        roles = MemberContactDA.get_contacts_roles(member_id)

        resp.body = json.dumps({
            "roles": roles,
            "success": True
        }, default_parser=json.parser)


class MemberInfoResource(object):

    def __init__(self):
        self.kafka_data = {"PUT": {"event_type": settings.get('kafka.event_types.put.member_info_update'),
                                   "topic": settings.get('kafka.topics.member')
                                   },
                           }

    @check_session
    def on_get(self, req, resp):
        member_id = req.context.auth["session"]["member_id"]

        member_info = MemberInfoDA().get_member_info(member_id)

        resp.body = json.dumps({
            "data": member_info,
            "success": True
        }, default_parser=json.parser)

    @check_session
    def on_put(self, req, resp):
        member_id = req.context.auth["session"]["member_id"]

        (member, member_profile, member_achievement, member_contact_2, member_location, member_rate, work, educations, certificates, skills) = request.get_json_or_form(
            "member", "member_profile", "member_achievement", "member_contact_2", "member_location", "member_rate", "work", "educations", "certificates", "skills", req=req)

        updated = MemberInfoDA().update_member_info(member_id,
                                                    member, member_profile, member_achievement, member_contact_2, member_location)

        updated = ProjectDA().update_member_default_rate(member_id=member_id,
                                                         pay_rate=member_rate["pay_rate"], currency_code_id=member_rate["currency_code_id"])

        # Skills
        listed_member_skills = MemberInfoDA.get_member_skills(member_id)
        new_skills = set(skills) - set(listed_member_skills)
        to_delete_skills = set(listed_member_skills) - set(skills)

        if len(new_skills) > 0:
            for s in new_skills:
                MemberInfoDA.add_skill(member_id, s)
        if len(to_delete_skills) > 0:
            for s in to_delete_skills:
                MemberInfoDA.unlist_skill(member_id, s)

        # Work

        received_record_ids = []
        if not work:
            received_record_ids = []
        if isinstance(work, list):
            received_record_ids = [w["id"] for w in work]

        listed_work_records_ids = MemberInfoDA.get_all_work_ids(member_id)

        to_add_work_ids = list(set(received_record_ids) -
                               set(listed_work_records_ids))

        to_delete_work_ids = list(set(
            listed_work_records_ids) - set(received_record_ids))

        to_update_work_ids = list(
            set(received_record_ids) & set(listed_work_records_ids))

        logger.info('listed', listed_work_records_ids)
        logger.info('add', to_add_work_ids)
        logger.info('delete', to_delete_work_ids)
        logger.info('update', to_update_work_ids)

        if len(to_add_work_ids) > 0:
            for wid in to_add_work_ids:
                wr = [w for w in work if w["id"] == wid][0]
                logger.info('work_id', wr)
                MemberInfoDA.create_work_record({"member_id": member_id, "job_title": wr["job_title"], "employment_type": wr["employment_type"], "company_id": None, "company_name": wr[
                                                "company_name"], "company_location": wr["company_location"], "start_date": wr["start_date"], "end_date": json.convert_null(wr["end_date"])})

        if len(to_delete_work_ids) > 0:
            for wid in to_delete_work_ids:
                logger.info('work_id', wid)
                MemberInfoDA.delete_work_record(wid)

        if len(to_update_work_ids) > 0:
            for wid in to_update_work_ids:
                wr = [w for w in work if w["id"] == wid][0]
                logger.info('work_id', wr)
                MemberInfoDA.update_work_record({"id": wid, "job_title": wr["job_title"], "employment_type": wr["employment_type"], "company_id": None, "company_name": wr[
                                                "company_name"], "company_location": wr["company_location"], "start_date": wr["start_date"], "end_date": json.convert_null(wr["end_date"])})

        #  Education
        received_education_ids = []
        if not educations:
            received_education_ids = []
        if isinstance(educations, list):
            received_education_ids = [edu["id"] for edu in educations]

        listed_education_ids = MemberInfoDA.get_all_education_ids(member_id)

        to_add_educations_ids = list(set(received_education_ids) -
                                     set(listed_education_ids))

        to_delete_education_ids = list(set(
            listed_education_ids) - set(received_education_ids))

        to_update_education_ids = list(
            set(received_education_ids) & set(listed_education_ids))

        if len(to_add_educations_ids) > 0:
            for eid in to_add_educations_ids:
                er = [e for e in educations if e["id"] == eid][0]
                MemberInfoDA.create_education_record({"member_id": member_id, "school_name": er["school_name"], "school_location": er["school_location"], "degree": er[
                                                     "degree"], "field_of_study": er["field_of_study"], "start_date": er["start_date"], "activity_text": json.convert_null(er["activity_text"]), "end_date": json.convert_null(er["end_date"])})

        if len(to_delete_education_ids) > 0:
            for eid in to_delete_education_ids:
                MemberInfoDA.delete_education_record(eid)

        if len(to_update_education_ids) > 0:
            for eid in to_update_education_ids:
                er = [e for e in educations if e["id"] == eid][0]
                MemberInfoDA.update_education_record({"id": eid, "school_name": er["school_name"], "school_location": er["school_location"], "degree": er["degree"], "field_of_study": er[
                    "field_of_study"],  "start_date": er["start_date"], "end_date": json.convert_null(er["end_date"]), "activity_text": json.convert_null(er["activity_text"])})

        # Certificates
        received_certs_ids = []
        if not certificates:
            received_certs_ids = []
        if isinstance(certificates, list):
            received_certs_ids = [cert["id"] for cert in certificates]

        listed_cert_ids = MemberInfoDA.get_all_certificate_ids(member_id)

        to_add_cert_ids = list(set(received_certs_ids) - set(listed_cert_ids))

        to_delete_cert_ids = list(set(
            listed_cert_ids) - set(received_certs_ids))

        to_update_cert_ids = list(
            set(received_certs_ids) & set(listed_cert_ids))

        if len(to_add_cert_ids) > 0:
            for cid in to_add_cert_ids:
                cr = [c for c in certificates if c["id"] == cid][0]
                MemberInfoDA.create_certificate_record(
                    {"member_id": member_id, "title": cr["title"], "description": cr["description"], "date_received": cr["date_received"]})

        if len(to_delete_cert_ids) > 0:
            for cid in to_delete_cert_ids:
                MemberInfoDA.delete_certificate_record(cid)

        if len(to_update_cert_ids) > 0:
            for cid in to_update_cert_ids:
                cr = [c for c in certificates if c["id"] == cid][0]
                MemberInfoDA.update_certificate_record(
                    {"id": cid, "title": cr["title"], "description": cr["description"], "date_received": cr["date_received"]})

        if updated:
            member_info = MemberInfoDA().get_member_info(member_id)
            resp.body = json.dumps({
                "data": member_info,
                "success": True
            }, default_parser=json.parser)


class MemberSettingResource(object):

    # def __init__(self):
    #     self.kafka_data = {"PUT": {"event_type": settings.get('kafka.event_types.put.member_info_update'),
    #                                "topic": settings.get('kafka.topics.member')
    #                                },
    #                        }

    @check_session
    def on_get(self, req, resp):
        member_id = req.context.auth["session"]["member_id"]
        # TODO: Convert to try/except with custom exception if no settings are found
        member_info = MemberSettingDA().get_member_setting(member_id)

        # TODO: The UI expects an obect right now, fix the UI in case there are errors
        resp.body = json.dumps({
            "data": member_info or {},
            "success": True
        }, default_parser=json.parser)

    @check_session
    def on_put(self, req, resp):
        member_id = req.context.auth["session"]["member_id"]

        (member_profile, member_location) = request.get_json_or_form(
            "member_profile", "member_location", req=req)

        logger.debug("member_profile_x: {}".format(member_profile))
        updated = MemberSettingDA().update_member_setting(
            member_id, member_profile, member_location)

        if updated:
            member_info = MemberSettingDA().get_member_setting(member_id)
            resp.body = json.dumps({
                "data": member_info,
                "success": True
            }, default_parser=json.parser)

    @check_session
    def on_put_payment(self, req, resp):
        member_id = req.context.auth["session"]["member_id"]
        (member_location, ) = request.get_json_or_form("member_location", req=req)
        updated = MemberSettingDA().update_member_payment_setting(member_id, member_location)
        if updated:
            member_info = MemberSettingDA().get_member_setting(member_id)
            resp.body = json.dumps({
                "data": member_info,
                "success": True
            }, default_parser=json.parser)


class MemberInfoByIdResource(object):
    @check_session
    def on_get(self, req, resp, member_id):
        member_info = MemberInfoDA().get_member_info(member_id)

        resp.body = json.dumps({
            "data": member_info,
            "success": True
        }, default_parser=json.parser)


class MemberJobTitles(object):
    auth = {
        'exempt_methods': ['GET']
    }

    def on_get(self, req, resp):
        job_title_list = MemberDA().get_job_list()
        # TODO: Replace with try/except and raise an exception
        # if unable to get a list
        if job_title_list:
            resp.body = json.dumps({
                "data": job_title_list,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Could not get the job title list",
                "success": False
            }, default_parser=json.parser)


class MemberDepartments(object):
    auth = {
        'exempt_methods': ['GET']
    }

    def on_get(self, req, resp):
        department_list = MemberDA().get_department_list()
        # TODO: Replace with try/except and raise an exception
        # if unable to get a list
        if department_list:
            resp.body = json.dumps({
                "data": department_list,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Could not get the departments list",
                "success": False
            }, default_parser=json.parser)


class MemberContactsCompanies(object):
    def on_get(self, req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            companies = MemberContactDA.get_contacts_companies(member_id)

            resp.body = json.dumps({
                "companies": companies,
                "success": True
            }, default_parser=json.parser)

        except InvalidSessionError as err:
            raise UnauthorizedSession() from err


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


class MemberTimezones(object):
    auth = {
        'exempt_methods': ['GET']
    }

    def on_get(self, req, resp):
        timezones = MemberDA().get_timezones()

        if timezones:
            resp.body = json.dumps({
                "data": timezones,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Could not get the terms and conditions",
                "success": False
            }, default_parser=json.parser)


class MemberSkills(object):
    auth = {
        'exempt_methods': ['GET']
    }

    def on_get(self, req, resp):
        skills = MemberDA().get_all_skills()
        if skills:
            resp.body = json.dumps({
                "data": skills,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Could not get the skills",
                "success": False
            }, default_parser=json.parser)


class MemberContactsCountries(object):
    def on_get(self, req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            countries = MemberContactDA.get_contacts_countries(member_id)

            resp.body = json.dumps({
                "countries": countries,
                "success": True
            }, default_parser=json.parser)

        except InvalidSessionError as err:
            raise UnauthorizedSession() from err


class MemberContactAccept(object):

    def __init__(self):
        self.kafka_data = {"PUT": {"event_type": settings.get('kafka.event_types.put.contact_request_response'),
                                   "topic": settings.get('kafka.topics.registration')
                                   }
                           }

    @check_session
    def on_put(self, req, resp, contact_member_id):
        member_id = req.context.auth["session"]["member_id"]
        try:
            (status,) = request.get_json_or_form(
                "status", req=req)

            MemberContactDA.accept_invitation(
                member_id, contact_member_id, status)
            MemberContactDA.accept_invitation(
                contact_member_id, member_id, status)
            req.headers['kafka_contacter_id'] = str(contact_member_id)
            req.headers['kafka_contact_request_status'] = status
            resp.body = json.dumps({
                "description": "Successfully accepted",
                "success": True
            }, default_parser=json.parser)
        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)


class MemberVideoMailResource(object):
    def __init__(self) -> None:
        self.kafka_data = {
            "POST": {
                "uri": {
                    "/mail/video/contact/{member_id:int}": {
                        "event_type": settings.get('kafka.event_types.post.send_contact_video_mail'),
                        "topic": settings.get('kafka.topics.member')
                    },
                    "/mail/video/group/{group_id:int}": {
                        "event_type": settings.get('kafka.event_types.post.send_group_video_mail'),
                        "topic": settings.get('kafka.topics.member')
                    },
                }
            },
            "GET": {
                "uri": {
                    "/mail/video/contact/{member_id:int}/video_mail/{video_mail_id:int}": {
                        "event_type": settings.get('kafka.event_types.get.read_contact_video_mail'),
                        "topic": settings.get('kafka.topics.member')
                    },
                    "/mail/video/group/{group_id:int}/video_mail/{video_mail_id:int}": {
                        "event_type": settings.get('kafka.event_types.get.read_group_video_mail'),
                        "topic": settings.get('kafka.topics.member')
                    },
                }
            },
            "DELETE": {
                "uri": {
                    "/mail/video/contact/{member_id:int}/video_mail/{video_mail_id:int}": {
                        "event_type": settings.get('kafka.event_types.delete.delete_contact_video_mail'),
                        "topic": settings.get('kafka.topics.member')
                    },
                    "/mail/video/group/{group_id:int}/video_mail/{video_mail_id:int}": {
                        "event_type": settings.get('kafka.event_types.get.delete_group_video_mail'),
                        "topic": settings.get('kafka.topics.member')
                    },
                }
            }
        }

    @check_session
    def on_post_contact(self, req, resp, member_id):
        logged_member_id = req.context.auth["session"]["member_id"]

        try:
            (video_blob, subject, type, media_type, replied_id) = request.get_json_or_form(
                "video_blob", "subject", "type", "media_type", "replied_id", req=req)

            video_storage_id = None
            if video_blob is not None:
                video_storage_id = FileStorageDA().put_file_to_storage(video_blob)

            video_mail_id = None
            if type == 'contact':
                video_mail_id = MemberVideoMailDA.create_contact_video_mail(
                    logged_member_id, video_storage_id, subject, media_type)
            else:
                video_mail_id = MemberVideoMailDA.create_reply_video_mail(
                    logged_member_id, video_storage_id, subject, media_type, replied_id)

            MemberVideoMailDA.create_contact_video_mail_xref(
                member_id, video_mail_id)

            resp.body = json.dumps({
                "video_mail_id": video_mail_id,
                "description": "Successfully created",
                "success": True
            }, default_parser=json.parser)
        except:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    @check_session
    def on_post_group(self, req, resp, group_id):
        member_id = req.context.auth["session"]["member_id"]
        try:
            (video_blob, subject, media_type) = request.get_json_or_form(
                "video_blob", "subject", "media_type", req=req)
            video_storage_id = None
            if video_blob is not None:
                video_storage_id = FileStorageDA().put_file_to_storage(video_blob)

            video_mail_id = MemberVideoMailDA.create_group_video_mail(
                member_id, group_id, video_storage_id, subject, media_type)
            group = GroupDA().get_group(group_id)
            MemberVideoMailDA.create_group_video_mail_xref(
                member_id, group_id, video_mail_id)

            if group['group_leader_id'] != member_id:
                MemberVideoMailDA.create_contact_video_mail_xref(
                    group['group_leader_id'], video_mail_id)

            resp.body = json.dumps({
                "video_mail_id": video_mail_id,
                "description": "Successfully created",
                "success": True
            }, default_parser=json.parser)
        except:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    @check_session
    def on_get_all(self, req, resp):
        member_id = req.context.auth["session"]["member_id"]
        try:
            search_key = req.get_param('search_key') or ''
            page_size = req.get_param_as_int('page_size')
            page_number = req.get_param_as_int('page_number')

            logger.debug(f"search_key {search_key}")
            logger.debug(f"page_number {search_key}")
            logger.debug(f"page_size {search_key}")

            mails = MemberVideoMailDA.get_video_mails(
                member_id, search_key, page_number, page_size)

            resp.body = json.dumps({
                "data": mails,
                "description": "Successfully loaded",
                "success": True
            }, default_parser=json.parser)

        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    def on_get_contact(self, req, resp, member_id, video_mail_id):
        try:
            MemberVideoMailDA.read_video_mail(member_id, video_mail_id)

            resp.body = json.dumps({
                "success": True
            }, default_parser=json.parser)

        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    @check_session
    def on_get_group(self, req, resp, group_id, video_mail_id):
        member_id = req.context.auth["session"]["member_id"]
        try:
            MemberVideoMailDA.read_video_mail(member_id, video_mail_id)

            resp.body = json.dumps({
                "success": True
            }, default_parser=json.parser)

        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    def on_delete_contact(self, req, resp, member_id, video_mail_id):
        try:

            MemberVideoMailDA.delete_video_mail(member_id, video_mail_id)

            resp.body = json.dumps({
                "success": True
            }, default_parser=json.parser)

        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    @check_session
    def on_delete_group(self, req, resp, group_id, video_mail_id):
        member_id = req.context.auth["session"]["member_id"]
        try:

            MemberVideoMailDA.delete_video_mail(member_id, video_mail_id)

            resp.body = json.dumps({
                "success": True
            }, default_parser=json.parser)

        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)
