import json
import random
import logging
import uuid
from datetime import datetime, timezone, timedelta
from pprint import pformat

import falcon
import requests
from ipregistry import IpregistryClient, InMemoryCache, ApiError

from app import settings
from app.da import FileTreeDA
from app.da.member import MemberDA
from app.da.session import SessionDA
from app.exceptions.session import ForbiddenSession, ForbiddenSessionError, InvalidSessionError, UnauthorizedSession, \
    SessionExistsError
from app.util import request
from app.util.session import get_session_cookie, validate_session, set_session_cookie

logger = logging.getLogger(__name__)


def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


def validate_token(token):
    return SessionDA.get_session(token)


def validate_session_request(request):
    session_id = get_session_cookie(request)
    if not session_id:
        raise InvalidSessionError()
    session = validate_token(session_id)
    if not session:
        raise InvalidSessionError()

    request.context.auth = {
        "session": session
    }

    return session


def validate_session_administrator(request):
    session = validate_session_request(request)

    # logger.debug(f"Resource Class: {cls}")
    logger.debug(f"User Type: {session['user_type']}")

    if session["user_type"] != 'administrator':
        raise ForbiddenSessionError()

    request.context.auth = {
        "admin": session
    }

    return session


def get_session_member_data(request):
    session = validate_session_request(request)
    member = MemberDA.get_member(session['member_id'])

    member["amera_avatar_url"] = session["amera_avatar_url"]
    request.context.auth = {
        "user": member,
        "session": session
    }

    return member


def check_session(func):
    def wrapper(cls, request, response, *args, **kwargs):
        try:
            validate_session_request(request)
            return func(cls, request, response, *args, **kwargs)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err
        except ForbiddenSessionError as err:
            raise ForbiddenSession() from err
    return wrapper


def check_session_pass(func):
    def wrapper(cls, request, response, *args, **kwargs):
        try:
            validate_session_request(request)
            return func(cls, request, response, *args, **kwargs)
        except InvalidSessionError as err:
            request.context.auth = {
                "session": {},
                "exception": InvalidSessionError
            }
        except ForbiddenSessionError as err:
            request.context.auth = {
                "session": {},
                "exception": InvalidSessionError
            }
    return wrapper

def check_session_administrator(func):
    def wrapper(cls, request, response, *args, **kwargs):
        try:
            validate_session_administrator(request)
            return func(cls, request, response, *args, **kwargs)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err
        except ForbiddenSessionError as err:
            raise ForbiddenSession() from err
    return wrapper


# def inject_member(func):
#     def wrapper(cls, request, response, *args, **kwargs):
#         try:
#             member = get_session_member_data(request)
#             func(cls, request, response, member, *args, **kwargs)
#         except InvalidSessionError as err:
#             raise UnauthorizedSession() from err
#         except ForbiddenSessionError as err:
#             raise ForbiddenSession() from err
#     return wrapper


def create_session(req, resp, member):
    expiration_seconds = settings.get("web.session_expiration")
    expiration_datetime = datetime.now(timezone.utc) + timedelta(
        seconds=int(expiration_seconds)
    )

    (client_ip, gateway_ip, original_url, query_string,
     client_name, gateway_name, server_name1, server_ip1,
     server_name2, server_ip2) = request.get_request_client_data(req)

    if client_ip == '127.0.0.1' or \
       client_ip == '172.18.0.1' or \
       not client_ip:
        client_ip = '216.58.193.142'


    ip_info = {
        '_json': {
            'carrier': {},
            'connection': {},
            'location': {
                'country': {},
                'region': {},
            },
            'time_zone': {},
            'user_agent': {
                'device': {},
                'engine': {},
                'os': {},
            }
        }
    }
    try:
        api_key = settings.get('services.ipregistry.api_key')
        if not api_key:
            raise Exception('Unable to load a proper key')
        client = IpregistryClient(api_key,
                                  cache=InMemoryCache(maxsize=2048, ttl=600))
        try:
            ip_info = client.lookup(client_ip)
            ip_info = vars(ip_info)
        except ApiError as e:
            logger.error(f'''
                                                   Error looking up IP: {client_ip} from IP Registry
                                                   Is key empty?: {(not settings.get('services.ipregistry.api_key'))}
                                               ''')
            logger.exception(e)

        try:
            url = client._requestHandler._buildApiUrl('user_agent', {})
            r = requests.post(url, data=json.dumps(
                [req.env['HTTP_USER_AGENT']]),
                              headers=client._requestHandler._headers(),
                              timeout=client._config.timeout)
            r.raise_for_status()
            data = r.json()['results']
            data = next(iter(data))
            logger.debug(f'Map: {data}')
            ip_info['_json'].update({
                'user_agent': data
            })
        except requests.HTTPError as e:
            logger.error(f'''
                                                   Error getting browser data from ip registry
                                                   Is key empty?: {(not settings.get('services.ipregistry.api_key'))}
                                               ''')
            logger.exception(e)
            ip_info.update({
                'user_agent': {
                    'header': {},
                    'device': {},
                    'os': {},
                    'engine': {},
                }
            })
            pass
    except Exception as e:
        logger.error(f'''
                                               Error creating an instance of ip registry
                                               Is key empty?: {(not settings.get('services.ipregistry.api_key'))}
                                           ''')
        logger.exception(e)

    logger.debug(f'IP Info: {pformat(ip_info)}')
    while True:
        try:
            session_id = uuid.uuid4().hex
            SessionDA.create_session(
                member, session_id, expiration_datetime,
                remote_ip_address=client_ip, gateway_ip_address=gateway_ip,
                original_url=original_url, original_arguments=query_string,
                remote_ip_name=client_name, gateway_ip_name=gateway_name,
                server_name=server_name1, server_ip=server_ip1,
                ip_info=ip_info['_json']
            )
            set_session_cookie(req, resp, session_id, expiration_datetime)
            break
        except SessionExistsError:
            continue


def create_new_user(self, req, resp, username, email=None,
                                first_name=None, last_name=None,
                                birthday=None, phone_number=None):

    # Create a new user. Basic copy paste from register

    tree_id, file_tree_id = FileTreeDA().create_tree('main', 'member', True)
    bin_file_tree_id = FileTreeDA().create_tree('bin', 'member')
    main_file_tree_id = tree_id

    default_drive_folders = settings.get('drive.default_folders')
    default_drive_folders.sort()

    for folder_name in default_drive_folders:
        FileTreeDA().create_file_tree_entry(
            tree_id=main_file_tree_id,
            parent_id=file_tree_id,
            member_file_id=None,
            display_name=folder_name
        )
    password = generate_nonce(length=25)
    if email:
        username = email
    else:
        email = generate_nonce(length=25)
    if not birthday:
        birthday = datetime.utcnow()
    if not phone_number:
        phone_number = generate_nonce(length=10)
    if not first_name:
        first_name = 'github'
    if not last_name:
        last_name = 'github'

    member_id = MemberDA.register(
        city=None, state=None, province=None, pin=None, avatar_storage_id=None,
        email=email, username=username, password=password,
        first_name=first_name, last_name=last_name, company_name=None, job_title_id=None,
        date_of_birth=birthday, phone_number=phone_number,
        country=840, postal=None, cell_confrimation_ts=None,
        email_confrimation_ts=None,
        department_id=None, main_file_tree_id=main_file_tree_id, bin_file_tree_id=bin_file_tree_id,
        commit=True)
    logger.debug("New registered member_id: {}".format(member_id))

    # Get member if we just created on
    member = SessionDA.auth(username, password)

    # Copy paste of login
    main_file_tree = member["main_file_tree"]
    bin_file_tree = member["bin_file_tree"]
    if not main_file_tree:
        tree_id = FileTreeDA().create_tree('main', 'member')
        MemberDA().assign_tree('main', member_id, tree_id)

    if not bin_file_tree:
        tree_id = FileTreeDA().create_tree('bin', 'member')
        MemberDA().assign_tree('bin', member_id, tree_id)

    return member
