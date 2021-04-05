import logging

from requests.models import HTTPError
import falcon
import requests
from requests.exceptions import RequestException

import app.util.json as json
from urllib.parse import urljoin, urlencode, urlparse
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


def get_token_url():
    login_uri = "https://trello.com/1/authorize?expiration=never&name=Amera&scope=read,write,account&key=a9046e495ce5f110b59a6b9e003d4be9&callback_method=fragment&return_url=http://localhost:3000/api/trello/auth"
    return login_uri

def redirect_uri(req):
    callback_uri = settings.get('services.trello.callback_url')
    callback_url = request.build_url_from_request(
        req,
        callback_uri
    )
    return callback_url

def report_bug(member_id, description, referer_url, current_url, data, req):
    report_id = BugReportDA.create(
                member_id, description, json.dumps(data),
                None, json.dumps(req), referer_url,
                current_url
            )
    return report_id

class TrelloLoginResource:

    def __init__(self):
        self.trello_auth_endpoint = settings.get('services.trello.login_uri')
        
    @check_session_pass
    def on_get(self, req, resp):
        params = (
            ('expiration', 'never'),
            ('name', 'Amera'),
            ('scope', settings.get('services.trello.scope')),
            ('key', 'a9046e495ce5f110b59a6b9e003d4be9'),
            ('return_url', redirect_uri(req)),
            ('callback_method', 'fragment'),
        )
        raise falcon.HTTPFound(
            f"{self.trello_auth_endpoint}?{urlencode(params)}"
        )

class TrelloOAuthResource:

    def __init__(self):
        self.api_key = settings.get('services.trello.api_key')
        self.secret = settings.get('services.trello.secret')

    @check_session_pass
    def on_get(self, req, resp):
        if 'exception' in req.context.auth:
            member_id = None
        else:
            member_id = req.context.auth['session']['member_id']

        url = req.env
        logger.debug(url)
        resp.body = json.dumps({"r": url})
