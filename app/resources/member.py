import logging
from datetime import timezone, datetime

import app.util.json as json
import app.util.request as request
from app.da.member import MemberDA
from app.da.invite import InviteDA
from app.da.group import GroupMembershipDA
from app.util.session import get_session_cookie, validate_session
from app.exceptions.member import MemberNotFound, MemberDataMissing, MemberExists
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
                members = GroupMembershipDA.get_members_not_in_group(group_id=exclude_group_id, member_id=member_id, search_key=search_key, page_size=page_size, page_number=page_number)
            else:
                members = MemberDA.get_members(member_id=member_id, search_key=search_key, page_size=page_size, page_number=page_number)
                
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

            members = MemberDA.get_group_members(member_id=member_id, search_key=search_key, page_size=page_size, page_number=page_number)
                
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

    def on_post(self, req, resp, invite_key):
        # We store the key in hex format in the database
        invite_key = invite_key.hex

        (email, username, password, 
         first_name, last_name, date_of_birth,
         phone_number, country, city, street,
         postal, state, province) = request.get_json_or_form(
            "email", "userName", "password",
            "firstName", "lastName", "dob",
            "cell", "country", "city", "street", "postalCode",
            "state", "province", req=req)
         
        if (not email or not username or not password or
            not first_name or not last_name or
            not date_of_birth or not phone_number or
            not country or not city or not street or not postal):
            raise MemberDataMissing()
        
        logger.debug("invite_key: {}".format(invite_key))
        logger.debug(": {}".format(email))
        logger.debug("First_nEmailame: {}".format(first_name))
        logger.debug("Last_name: {}".format(last_name))
        logger.debug("Username: {}".format(username))
        logger.debug("Password: {}".format(password))

        # db_connection.start_transaction()

        invite = InviteDA.get_invite(invite_key=invite_key)

        if not invite:
            raise InviteNotFound(invite_key)

        utc_expiration = invite["expiration"].replace(tzinfo=timezone.utc)
        utc_now = datetime.now(timezone.utc)

        if utc_now > utc_expiration:
            logger.debug((
                "Expiration Datetime: {} (UTC) is"
                " past current Datetime: {} (UTC)"
            ).format(
                utc_expiration, utc_now))
            raise InviteExpired(invite_key)

        member = MemberDA.get_member_by_email(email);
        
        if member:
            raise MemberExists(email);
        
        member_id = MemberDA.register(
            email=email, username=username, password=password,
            first_name=first_name, last_name=last_name,
            date_of_birth=date_of_birth, phone_number=phone_number, 
            country=country, city=city, street=street, postal=postal,
            state=state, province=province, commit=False)

        logger.debug("New registered member_id: {}".format(member_id))

        # Update the invite reference to the newly created member_id
        InviteDA.update_invite_registered_member(
            invite_key=invite_key, registered_member_id=member_id
        )

        MemberDA.source.commit()

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
