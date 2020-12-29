from pprint import pformat
import uuid
import falcon
import requests
import app.util.json as json

from ipregistry import IpregistryClient, DefaultCache
from ipregistry.model import IpInfo, ApiError


import logging

from datetime import datetime, timedelta, timezone

from app.config import settings
import app.util.request as request
from app.util.session import set_session_cookie
from app.da.session import SessionDA
from app.da.member import MemberDA
from app.da.file_sharing import FileTreeDA
from app.exceptions.session import SessionExistsError

logger = logging.getLogger(__name__)


class MemberLoginResource(object):

    auth = {
        'exempt_methods': ['POST']
    }

    def on_post(self, req, resp):

        (username, password) = request.get_json_or_form(
            "username", "password", req=req)

        if not username or not password:
            raise falcon.HTTPError("400",
                                   title="Invalid Login",
                                   description="No Login Data Sent")

        member = SessionDA.auth(username, password)
        # TODO Do ip query and save to the database.

        if not member:
            raise falcon.HTTPUnauthorized(title="Invalid Login",
                                          description="Invalid credentials")

        main_file_tree = member["main_file_tree"]
        bin_file_tree = member["bin_file_tree"]
        member_id = member["id"]
        if not main_file_tree:
            tree_id = FileTreeDA().create_tree('main', 'member')
            MemberDA().assign_tree('main', member_id, tree_id)

        if not bin_file_tree:
            tree_id = FileTreeDA().create_tree('bin', 'member')
            MemberDA().assign_tree('bin', member_id, tree_id)

        expiration_seconds = settings.get("web.session_expiration")
        expiration_datetime = datetime.now(timezone.utc) + timedelta(
            seconds=expiration_seconds
        )

        (client_ip, gateway_ip, original_url, query_string,
         client_name, gateway_name, server_name1, server_ip1,
         server_name2, server_ip2) = request.get_request_client_data(req)

        if client_ip == '127.0.0.1':
            client_ip = '23.113.176.107'
        if not client_ip:
            client_ip = '23.113.176.107'

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
                cache=DefaultCache(maxsize=2048, ttl=600))
            try:
                ip_info = client.lookup(client_ip)
                ip_info = vars(ip_info)
            except ApiError as e:
                logger.error(f'''
                    Error looking up IP: {client_ip} from IP Registry
                    Is key empty?: {(not settings.get('services.ipregistry.api_key'))}
                ''')
                logger.exception(e)

            # curl --data '["Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.120 Safari/537.36"]' \
            # --header "Content-Type: application/json" \
            # --request POST "https://api.ipregistry.co/user_agent?key=YOUR_API_KEY"

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
        # TODO: Refactor with a better pattern (one or the other):
        # * pregenerated session_id keys
        # * generate session_id keys from username, salts, etc
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
                break
            except SessionExistsError:
                continue

        set_session_cookie(req, resp, session_id, expiration_datetime)

        resp.body = json.dumps({
            "session_id": session_id
        })

    def on_get(self, req, resp):
        resp.body = json.dumps({
            "session": req.context
        })
