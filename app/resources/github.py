import logging
import falcon
import requests

import app.util.json as json

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


logger = logging.getLogger(__name__)
# Cache to hold state between redirects
STATE_CACHE = {}


def create_name_from_github_user(username):
    name = "Unknown User"
    u = get_amera_member_from_github(username)
    if u:
        name = u.get('first_name') + ' ' + u.get('last_name')
    return name


def get_amera_member_from_github(username):
    u = None
    git_user = ExternalAccountDA().get_external_account_by_username(username)
    if git_user:
        u = MemberDA().get_member(git_user.get('member_id'))
    return u


class GithubLoginResource:

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.member_change_password'),
                                    "topic": settings.get('kafka.topics.member')
                                    },
                           }

        self.client_id = settings.get('services.github.client_id')
        self.github_auth_endpoint = settings.get('services.github.authorization_url')
        self.client = WebApplicationClient(self.client_id)

    @check_session_pass
    def on_get(self, req, resp):

        if 'exception' in req.context.auth: 
            member_id = None
        else:
            member_id = req.context.auth['session']['member_id']

        # ------------- Generate state and request temporary code from github -------------- #
        state = generate_nonce()
        if not member_id:
            client_ip = request.get_request_client_data(req)[0]
            # Save state to cache with ip as key so we can process on redirect
            STATE_CACHE.update({client_ip: state})
        else:
            STATE_CACHE.update({member_id: state})

        callback_url = request.build_url_from_request(
            req,
            settings.get('services.github.callback_url')
        )

        request_uri = self.client.prepare_request_uri(
            self.github_auth_endpoint,
            redirect_uri=callback_url,
            scope=["admin:repo_hook", "read:org", "user"],
            state=state
        )
        raise falcon.HTTPFound(request_uri)


class GithubOAuthResource:

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.member_change_password'),
                                    "topic": settings.get('kafka.topics.member')
                                    },
                           }

        self.client_id = settings.get('services.github.client_id')
        self.github_auth_endpoint = settings.get('services.github.authorization_url')
        self.client = WebApplicationClient(self.client_id)
        self.client_secret = settings.get('services.github.client_secret')
        self.token_endpoint = settings.get('services.github.token_url')

    @check_session_pass
    def on_get(self, req, resp):
        if 'exception' in req.context.auth:
            member_id = None
        else:
            member_id = req.context.auth['session']['member_id']

        # ------------- Get code and state that github sends us, then retrieve a real token -----------
        code = req.params.get('code')
        state = req.params.get('state')
        if member_id:
            cache_state = STATE_CACHE.pop(member_id)
        else:
            ip = request.get_request_client_data(req)[0]
            cache_state = STATE_CACHE.pop(ip)

        if state != cache_state:
            raise Exception("Something went wrong authenticating your request")

        token_url, headers, body = self.client.prepare_token_request(
            self.token_endpoint,
            code=code,
            state=state
        )
        logger.debug(f"Github Token URL: {token_url}")
        logger.debug(f"Github Token Headers: {headers}")
        logger.debug(f"Github Token Body: {body}")

        headers['Accept'] = 'application/json'
        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(self.client_id, self.client_secret),
        )
        logger.debug(f"Token response: {token_response}")
        token_response = token_response.json()
        logger.debug(f"Token response JSON: {pformat(token_response)}")

        token = token_response.get('access_token', None)
        if not token:
            raise Exception("There was an error authenticating your account.")

        # ---------- Get user data to connect github to Amera --------- #
        r = requests.get(settings.get('services.github.api_url'), auth=('username', token))
        logger.debug(f"User response: {r}")

        if r.status_code == 200:
            user = r.json()
            logger.debug(f"User object: {pformat(user)}")
            username = user.get('login')
            email = user.get('email')
            profile_link = user.get('html_url')
            company = user.get('company')
            #name = user.get('name').split(' ')
            name = user.get('name')
            first_name = None
            last_name = None
            if name:
                name = name.split(' ')
                first_name = name[0]
                last_name = name[1]
            #first_name = name[0]
            #last_name = name[1]
            scope = r.headers.get('X-OAuth-Scopes').split(',')

            # look up user by username - create if they don't exist.
            external_account = ExternalAccountDA().get_external_account_by_username(username, 'github')
            if member_id:
                member = req.context.auth['session']
            else:
                member = MemberDA().get_member_by_username(username)

            try:
                if external_account:
                    external_account = ExternalAccountDA(). \
                        update_external_account(external_account['member_id'], 'github', username, email,
                                                profile_link, company, json.dumps(scope), token)
                else:
                    if not member:
                        member = create_new_user(req, resp, username, email,
                                                 first_name=first_name, last_name=last_name,
                                                 birthday=None, phone_number=None)
                        member_id = member['id']
                    external_account = ExternalAccountDA().create_external_account(
                        member_id, 'github', username, email,
                        profile_link, company, json.dumps(scope), token)
            except Exception as e:
                raise e

            # Redirect if they have admin:repo
            if "admin:repo_hook" in scope:
                raise falcon.HTTPFound(
                    request.build_url_from_request(req,
                        settings.get('services.github.admin_repo_redirect_url')
                    )
                )

            # set session cookie with new/existing user after oauth has completed if not admin
            create_session(req, resp, member)
        raise falcon.HTTPFound(request.get_url_base(req))


class GithubWebhooksResource(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.member_change_password'),
                                    "topic": settings.get('kafka.topics.member')
                                    },
                           }

    def on_post(self, req, resp):

        data = req.media
        logger.debug(f"Webhook data received: {data}")
        payload = None

        if data.get('action') and data.get('pull_request'):
            action = data.get('action')
            pull_request = data.get('pull_request')
            branch_name = pull_request.get('head').get('ref')
            pr_creator_name = create_name_from_github_user(pull_request.get('user').get('login'))
            ticket = ProjectDA().get_story_by_github_branch(branch_name)
            project_members = ProjectDA().get_member_ids_for_project(ticket.get('project_id'))
            leader = ProjectDA().get_project_owner(ticket.get('project_id'))
            project = ProjectDA().get_project_by_id(ticket.get('project_id'))

            if action == 'created':
                # PR opened
                # USER has created a PR for TICKET in PROJECT
                payload = dict(
                    type="pull_request_opened",
                    pr_url=pull_request.get('url'),
                    pr_creator=pr_creator_name,  # Austin
                    pr_name=pull_request.get('title'),
                    project_name=project.get('title'),  # Github Project
                    ticket_id=ticket.get('id'),  # 101
                    ticket_title=ticket.get('title'),  # Create Github Webhooks
                    notifiee_ids=[leader.get('id'), ],  # Leader of project? or List of all project members?
                )
            elif action == 'review_requested':
                # Requested to review
                # USER has requested you to review PR for TICKET PR_URL
                reviewer = get_amera_member_from_github(pull_request.get('requested_reviewer'))
                requestor = create_name_from_github_user(pull_request.get('sender').get('login'))
                payload = dict(
                    type="review_requested",
                    pr_url=pull_request.get('url'),
                    pr_name=pull_request.get('title'),
                    pr_creator=pr_creator_name,  # Austin Nicholas,
                    ticket_id=ticket.get('id'),  # 101
                    ticket_title=ticket.get('title'),  # Amera-1001
                    project_name=project.get('title'),
                    review_requestor=requestor,
                    notifiee_ids=[reviewer.get('member_id'), ],
                )
            elif action == "closed" and pull_request.get('merged') == 'true':
                # merged MR
                # USER merged a PULL REQUEST NAME for TICKET/PROJECT
                merger = create_name_from_github_user(data.get('sender').get('login'))
                payload = dict(
                    type="pull_request_merged",
                    pr_url=pull_request.get('url'),
                    pr_name=pull_request.get('title'),
                    pr_creator=pr_creator_name,  # Austin Nicholas,
                    ticket_title=ticket.get('title'),  # Amera-1001
                    ticket_id=ticket.get('id'),  # 101
                    project_name=project.get('title'),
                    merger=merger,
                    notifiee_ids=[leader.get('member_id'), ],
                )
            elif action == 'submitted':  # review submitted
                # USER submitted a review for TICKET/PROJECT
                pr_creator = get_amera_member_from_github(pull_request.get('user').get('login'))
                sender_name = create_name_from_github_user(data.get('sender').get('login'))
                payload = dict(
                    type="review_submitted",
                    pr_url=pull_request.get('url'),
                    pr_name=pull_request.get('title'),
                    pr_creator=pr_creator_name,  # Austin Nicholas,
                    ticket_title=ticket.get('title'),  # Amera-1001
                    ticket_id=ticket.get('id'),  # 101
                    project_name=project.get('title'),
                    reviewer_name=sender_name,
                    notifiee_ids=[pr_creator.get('member_id'), ],
                )
            elif action == 'created' and data.get('comment'):
                # Comment on PR
                # USER commented on your PR TICKET PROJECT
                pr_creator = get_amera_member_from_github(pull_request.get('user').get('login'))
                commenter_name = create_name_from_github_user(data.get('sender').get('login'))
                payload = dict(type="comment_submitted",
                               pr_url=pull_request.get('url'),
                               pr_name=pull_request.get('title'),
                               pr_creator=pr_creator_name,  # Austin Nicholas,
                               ticket_title=ticket.get('title'),  # Amera-1001
                               project_name=project.get('title'),
                               commenter=commenter_name,
                               notifiee_ids=[pr_creator.get('member_id'), ],
                               )

        if payload:
            r = requests.post("http://amera-eventserver:4000/consumer/call-notifications", json.dumps(payload))

        resp.body = json.dumps({
            "success": True
        })
        resp.status = falcon.HTTP_200


class GithubRepoListResource:

    @check_session
    def on_get(self, req, resp):
        member_id = req.context.auth['session']['member_id']

        external_account = ExternalAccountDA().get_external_account_by_member_id(member_id, 'github')
        if "admin:repo_hook" in external_account.get('scope'):
            r = requests.get('https://api.github.com/user/repos',
                             auth=('username', external_account['token']))
            if r.status_code == 200:
                data = r.json()
                names = []
                for repo in data:
                    names.append({"name": repo.get('name'), "url": repo.get('url')})

                resp.body = json.dumps(names)

    @check_session
    def on_post(self, req, resp):
        member_id = req.context.auth['session']['member_id']
        data = req.media
        external_account = ExternalAccountDA().get_external_account_by_member_id(member_id, 'github')

        # creat webhook for each repo
        for repo in data.get('repo_list'):
            r = requests.post(f'https://api.github.com/repos/{data.get("username")}/{repo.get("name")}/hooks',
                              auth=('username', external_account['token']),
                              data=json.dumps({
                                  "config": {
                                      "url": "http://29670233115a.ngrok.io/github-webhooks",
                                      "content_type": 'application/json',
                                      "secret": "amera-webhook-secret",

                                  },
                                  "events":
                                      ["pull_request", "pull_request_review",
                                       "pull_request_review_comment",
                                       "create", "delete"
                                       ]

                              }))
            if r.status_code == 201:
                logger.debug(r.json())
                resp.status = falcon.HTTP_201
            else:
                resp.status = falcon.HTTP_400
                logger.error(r.json())
