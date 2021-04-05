import logging

from requests.models import HTTPError
import falcon
import requests
from requests.exceptions import RequestException

import app.util.json as json
from urllib.parse import urljoin, urlencode
from pprint import pformat
from oauthlib.oauth2 import WebApplicationClient

from app import settings
from app.da import MemberDA
from app.da.member_external_account import ExternalAccountDA
from app.da.project import ProjectDA
from app.util import request
from app.util.auth import check_session, check_session_pass, create_session, \
    create_new_user, generate_nonce
from app.util.session import set_session_cookie
from app.exceptions.session import InvalidSessionError
from app.da.bug_report import BugReportDA


logger = logging.getLogger(__name__)
# Cache to hold state between redirects
STATE_CACHE = {}


def get_common_token_url():
    login_uri = settings.get('services.o365.login_uri')
    token_path = settings.get('services.o365.token_path')

    return urljoin(
        login_uri,
        token_path.format('common')
    )


def get_graph_users_url():
    #graph_uri = settings.get('services.o365.graph_uri')
    graph_uri = "https://graph.microsoft.com/v1.0" + "/users"
    return graph_uri

def get_graph_me_url():
    #graph_uri = settings.get('services.o365.graph_uri')
    graph_uri = settings.get('services.o365.graph_uri') + "/me"

    return graph_uri

class O365AccessTokenError(Exception):
    def __init__(self, response, request, *args):
        super().__init__(*args)
        self._response = response
        self._request = request


# get access token for tenant
def getO365AccessToken():
    grant_type = "refresh_token"
    refresh_token = settings.get("services.o365.refresh_token")
    client_id = settings.get("services.o365.client_id")
    client_secret = settings.get("services.o365.client_secret")
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": grant_type,
        "refresh_token": refresh_token
    }

    login_uri = settings.get('services.o365.login_uri')
    tenant_id = settings.get('services.o365.tenant_id')
    token_path = settings.get('services.o365.token_path')

    tenant_token_url = urljoin(
        login_uri,
        token_path.format(tenant_id)
    )
    r = requests.post(tenant_token_url, data)
    try:
        r.raise_for_status()
        token_data = r.json()
        return token_data["access_token"]
    except RequestException as e:
        raise O365AccessTokenError(e.response, e.request) from e

def userScope(org):
    if org:
        return settings.get("services.o365.user_scope_org")
    return settings.get("services.o365.user_scope")


def authUri(org):
    login_uri = settings.get('services.o365.login_uri')
    tenant_id = settings.get('services.o365.tenant_id')
    authorize_path = settings.get('services.o365.authorize_path')

    if org:
        return urljoin(
            login_uri,
            authorize_path.format(tenant_id)
        )
    return urljoin(
        login_uri,
        authorize_path.format('common')
    )


def redirect_uri(req):
    callback_uri = settings.get('services.o365.callback_url')
    callback_url = request.build_url_from_request(
        req,
        callback_uri
    )
    return callback_url


def get_amera_member_from_o365(member_id):
    u = None
    user = ExternalAccountDA().get_external_account_by_member_id(member_id, "microsoft")
    if user:
        u = user
    return u


def report_bug(member_id, description, referer_url, current_url, data, req):
    # logger.debug(data.text)
    # logger.debug(data)
    try:
        data = data.json()
    except:
        pass
    request_data = {
        "headers": req.headers,
        "req_params": req.params,
        "headers": req.headers,
        "referer_url": req.headers.get('REFERER'),
        "url": req.url,
    }

    report_id = BugReportDA.create(
                member_id, description, json.dumps(data),
                None, json.dumps(request_data), referer_url,
                current_url
            )
    return report_id

def getErrorDescription(e):
    try:
        return e
    except Exception as e:
        return ""

def getFalconStatusError(status, text):
    return f'{status} {text}'

class O365LoginResource:

    def __init__(self):

        self.client_id = settings.get('services.o365.client_id')
        self.o365_auth_endpoint = authUri(False)
        self.client = WebApplicationClient(self.client_id)

    @check_session_pass
    def on_get(self, req, resp):

        state = generate_nonce()
        request_uri = self.client.prepare_request_uri(
            self.o365_auth_endpoint,
            redirect_uri=redirect_uri(req),
            scope=userScope(False),
            #state=state,
        )
        raise falcon.HTTPFound(request_uri)

class O365OAuthResource:

    def __init__(self):
        self.client_secret = settings.get('services.o365.client_secret')
        self.client_id = settings.get('services.o365.client_id')
        self.client = WebApplicationClient(self.client_id)
        self.token_endpoint = get_common_token_url()

    @check_session_pass
    def on_get(self, req, resp):
        if 'exception' in req.context.auth:
            member_id = None
        else:
            member_id = req.context.auth['session']['member_id']

        # ------------- Get Loginer's email address -----------
        code = req.params.get('code')

        state = generate_nonce()
        token_url, headers, body = self.client.prepare_token_request(
            self.token_endpoint,
            code=code,
            state=state,
        )
        params = (
            ('redirect_uri', redirect_uri(req)),
        )
        body += f"&{urlencode(params)}"

        headers['Accept'] = 'application/json'
        referer_url = request.build_url_from_request(
            req,
            settings.get('services.o365.admin_redirect_url')
        )
        current_url = authUri(False)
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(self.client_id, self.client_secret),
        )

        try:
            token_response.raise_for_status()
            token_response = token_response.json()
        except RequestException as e:
            token_response = e.response.json()
            description = getErrorDescription(
                token_response.get(
                    'error_description',
                    'Unknown error getting access token'
                )
            )
            bug_id = report_bug(member_id, description,
                                referer_url, current_url, e.response, req)
            redirect_params = (
                ('bug_id', bug_id),
                ('error', token_response.get('error', None)),
                ('step', 'token'),
            )
            raise falcon.HTTPFound(
                request.build_url_from_request(
                    req,
                    f"{settings.get('services.o365.admin_redirect_url')}?{urlencode(redirect_params)}"
                )
            )

        access_token = token_response.get("access_token")
        my_headers = {'Authorization' : 'Bearer ' + access_token}
        response = requests.get(get_graph_me_url(), headers=my_headers)
        try:
            response.raise_for_status()
            user_email = response.json()["userPrincipalName"]
        except RequestException as e:
            response = e.response.json()
            description = getErrorDescription(
                response.get(
                    'error_description',
                    'Unknown error getting access token'
                )
            )
            bug_id = report_bug(member_id, description,
                                referer_url, get_graph_me_url(), e.response, req)
            redirect_params = (
                ('bug_id', bug_id),
                ('error', response.get('error', None)),
                ('step', 'userInfo'),
            )
            raise falcon.HTTPFound(
                request.build_url_from_request(
                    req,
                    f"{settings.get('services.o365.admin_redirect_url')}?{urlencode(redirect_params)}"
                )
            )

        user_email_4_search = user_email.replace("#", "%23").replace("@", "%40")

        # get user info using graph api
        try:
            access_token = getO365AccessToken()
        except O365AccessTokenError as e:
            response = e._response.json()
            bug_id = report_bug(member_id, 'unable to get tenant access token',
                                referer_url, get_graph_me_url(), e._response, req)
            redirect_params = (
                ('bug_id', bug_id),
                ('error', response.get('error', None)),
                ('step', 'tenantToken'),
            )
            raise falcon.HTTPFound(
                request.build_url_from_request(
                    req,
                    f"{settings.get('services.o365.admin_redirect_url')}?{urlencode(redirect_params)}"
                )
            )

        try:
            url4api = settings.get('services.o365.graph_uri') + "/users?$filter=userPrincipalName eq '" + user_email_4_search + "' or mail eq '" + user_email_4_search + "'" # get user filtered on mail or userPrincipalName
            my_headers = {'Authorization': 'Bearer ' + access_token}
            response = requests.get(url4api, headers=my_headers)
            user = response.json().get("value", [])
            o365_user = None
            user_id = None
            username = "Unknown User"
            first_name = "Test"
            second_name = "Test"
            if len(user):
                o365_user = user[0]
        except Exception as e:
            response = e.response.json()
            description = getErrorDescription(
                response.get(
                    'error_description',
                    'Unknown error getting tenant users'
                )
            )
            bug_id = report_bug(member_id, description,
                                referer_url, get_graph_users_url(), e.response, req)
            redirect_params = (
                ('bug_id', bug_id),
                ('error', response.get('error', None)),
                ('step', 'tenantUsers'),
            )
            raise falcon.HTTPFound(
                request.build_url_from_request(
                    req,
                    f"{settings.get('services.o365.admin_redirect_url')}?{urlencode(redirect_params)}"
                )
            )

        try:
            if o365_user:
                user_id = o365_user["id"]
                username = o365_user["displayName"]

            external_account = get_amera_member_from_o365(member_id)
            user_scope = userScope(False).split(" ")
            user_scope = json.dumps(user_scope)

            if external_account:
                external_account = ExternalAccountDA(). \
                    update_external_account(member_id, 'microsoft', username, user_email,
                                            user_id, "", user_scope, "" )
            else:
                external_account = ExternalAccountDA().create_external_account( member_id, 'microsoft', username, user_email, user_id, "", user_scope, "")
        except Exception as e:
            description = "modifying database failed"
            bug_id = report_bug(member_id, description,
                                referer_url, 'database://', e, req)
            redirect_params = (
                ('bug_id', bug_id),
                ('error', json.dumps(e)),
                ('step', 'updateDB'),
            )
            raise falcon.HTTPFound(
                request.build_url_from_request(
                    req,
                    f"{settings.get('services.o365.admin_redirect_url')}?{urlencode(redirect_params)}"
                )
            )

        raise falcon.HTTPFound(
            request.build_url_from_request(
                req, settings.get('services.o365.admin_redirect_url'))
        )

