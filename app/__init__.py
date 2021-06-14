import logging
import os
import falcon

import importlib

# from falcon_auth import FalconAuthMiddleware, TokenAuthBackend
from falcon_multipart.middleware import MultipartMiddleware

from app.calls.views import IncomingCallView
from app.chat.views import ChatView
from app.config import parser, settings
from app.middleware import CrossDomain, HandleForwardSlashMiddleware, KafkaProducerMiddleware  # , JSONTranslator
from app.resources.facial_recognition import FacialRecognitionResource
from app.resources.github import GithubWebhooksResource, GithubRepoListResource, GithubLoginResource, \
    GithubOAuthResource
from app.resources.member import MemberRegisterResource, MemberSearchResource, \
    MemberGroupSearchResource, MemberContactResource, MemberContactAccept, ContactMembersResource, \
    MemberInfoResource, MemberJobTitles, MemberTerms, MemberDepartments, MemberContactsRoles, \
    MemberContactsCompanies, MemberContactsCountries, MemberTimezones, MemberInfoByIdResource, \
    MemberContactSecurity, MemberSettingResource, MemberVideoMailResource, \
    ContactMembersTextMailsResource, MemberSkills, MemberIndustry
from app.resources.verification import Verification
from app.resources.verifycell import VerifyCell
from app.resources.promo_codes import PromoCodes
from app.resources.invite import MemberInviteResource, ValidInviteResource
from app.resources.login import MemberLoginResource
from app.resources.forgot_password import MemberForgotPasswordResource
from app.resources.reset_password import MemberResetPasswordResource
from app.resources.change_password import MemberChangePasswordResource
from app.resources.logout import MemberLogoutResource
from app.resources.session import ValidateSessionResource
from app.resources.file_download import FileDownloadResource
from app.resources.file_sharing import MemberFileCloud, MemberFileBin, \
    MemberShareFile, GroupFileCloud, GroupFileBin, FileGroupResource
from app.resources.group import MemberGroupResource, GroupMembershipResource, GroupDetailResource, \
    GroupMemberInviteResource, GroupMembersResource, MemberGroupSecurity, GroupMemberAccept, \
    GroupActivityDriveResource, GroupActivityCalendarResource
from app.resources.system import SystemActivityResource
from app.resources.system import SystemActivityUsersResource
from app.resources.system import SystemMemberResource
from app.resources.language import LanguageResource
from app.resources.member_scheduler_setting import MemberSchedulerSettingResource
from app.resources.member_schedule_event import MemberScheduleEventResource, MemberScheduleEventColors, \
    EventAttachmentResorce, MemberUpcomingEvents, MemberEventInvitations, MemberEventDirections
from app.resources.member_schedule_holiday import MemberScheduleHolidayResource
from app.resources.member_schedule_event_invite import MemberScheduleEventInviteResource, \
    MemberScheduleEventInviteSetStatusResource
from app.resources.country import CountryCodeResource
from app.resources.mail import MailDraftComposeResource, MailAttachmentResource, MailInboxResource, MailStaredResource, \
    MailTrashResource, MailArchiveResource, MailSettingsResource, MailSentResource, MailMemberFolderResource
from app.resources.role import RolesResource
from app.resources.avatar import MemberAvatarResource
from app.resources.activity import ActivitiesResource
from app.resources.project import ProjectResource
from app.resources.company import CompanyResource, CompanyUnregisteredResource
from app.resources.forum import ForumResource
from app.resources.billing import BillingResource
from app.resources.activity_new import SystemActivitySessionResource, SystemActivitySecurityResource, SystemActivityMessageResource, \
    SystemActivityGroupResource, SystemActivityInvitationsResource
from app.resources.page_settings import PageSettingsResource

from app.resources.notifications_setting import MemberNotificationsSetting
# from app.resources.memberfile import

from app.resources.o365Resource import O365LoginResource
from app.resources.o365Resource import O365OAuthResource
# O365Resource import

from app.resources.trelloResource import TrelloLoginResource
from app.resources.trelloResource import TrelloOAuthResource
from app.resources.twilioResource import TwilioResource

from app.resources.newsfeeds import NewsFeedsResource
from app.resources.password import PasswordResource

from app.resources.billing import BillingResource

from app.resources.bug_report import BugReportResource, BugReportUsersResource

from app.resources.admin import AdminMemberResource
from app.resources.stream import StreamResource, StreamCategoryResource, StreamTypeResource
from app.util.request import get_request_host
from app.util.config import setup_vyper
from app.util.error import error_handler
from app.util.logging import setup_logging
# import app.util.stored_procedure as stored_procedure

try:
    imsecure_spec = importlib.util.find_spec(
        ".imsecure.image_secure", package="imsecure")
except ModuleNotFoundError:
    imsecure_spec = None

imsecure_found = imsecure_spec is not None

if imsecure_found:
    from app.resources.keygen import KeyGenResource, KeyGenFileUpload

# from app.util.auth import validate_token


logger = logging.getLogger(__name__)

# auth_backend = TokenAuthBackend(validate_token)


def configure(**overrides):
    # This allows us to set an environment variable before
    # the application starts to configure to see the configuration
    # process and debug any issues
    env_log_level_name = "APP_LOG_LEVEL"
    prefix = parser.get_default("environment_variables_prefix")
    if prefix:
        env_log_level_name = "{}_LOG_LEVEL".format(prefix).upper()

    log_level = os.getenv(env_log_level_name, logging.WARNING)

    logging.getLogger("vyper").setLevel(log_level)
    setup_vyper(parser, overrides)
    print(f"Getting Worker Class {settings.get('WORKER_CLASS')}")
    if 'meinheld' in settings.get('WORKER_CLASS'):
        import meinheld
        # This passes the limits of Signed int
        # print(f"Max Size: {sys.maxsize}")
        # This passes the limits of Signed int )
        # print(f"Max size: {2**10 * 2**10 * 2**10 * 2**10 * 1}")
        # Setting to 1 Gigabyte
        max_size = 2**10 * 2**10 * 2**10 * 1
        # print(f"Max size: {max_size}")
        # This sets the max body size to 549 GB
        meinheld.set_max_content_length(max_size)


def create_app():
    setup_logging()

    app = falcon.API(
        middleware=[
            HandleForwardSlashMiddleware(),
            CrossDomain(),
            # FalconAuthMiddleware(auth_backend),
            MultipartMiddleware(),
            KafkaProducerMiddleware(),
            # JSONTranslator()
        ],
    )

    app.req_options.auto_parse_qs_csv = True

    app.add_error_handler(Exception, error_handler)

    _setup_routes(app)

    # stored_procedure.init_procedures()

    return app


class HealthResource:
    def on_get(self, req, resp):
        resp.media = {'status': 'OK', 'health': 1.0,
                      'domain': get_request_host(req)}


class HeadersResource:
    def on_get(self, req, resp):
        data = dict(req.env)
        data.pop('wsgi.file_wrapper', None)
        data.pop('wsgi.input', None)
        data.pop('wsgi.errors', None)
        data.pop('gunicorn.socket', None)
        data.pop('meinheld.client', None)
        data['domain'] = get_request_host(req)
        data['req.host'] = req.host
        data['req.forwarded'] = req.forwarded_host
        logger.debug(data)
        resp.media = data


def start():
    logger.info("Environment: {}".format(settings.get("ENV_NAME")))


def _setup_routes(app):
    logger.debug(
        f"Spec checker: {imsecure_found} {imsecure_spec} {imsecure_spec.name if imsecure_spec else ''}")

    app.add_route('/healthz', HealthResource())
    app.add_route('/healthz/headers', HeadersResource())

    if imsecure_found:
        app.add_route('/demo/image-upload', KeyGenFileUpload())
        app.add_route("/demo/keygen", KeyGenResource())
    app.add_route("/member/login", MemberLoginResource())
    app.add_route("/member/forgot", MemberForgotPasswordResource())
    app.add_route(
        "/member/reset-password/{forgot_key:uuid}", MemberResetPasswordResource())
    app.add_route("/member/change-password", MemberChangePasswordResource())
    app.add_route(
        "/member/{member_id:int}/logout/{session_id:uuid}", MemberLogoutResource())
    app.add_route("/member/invite", MemberInviteResource())
    app.add_route("/member/info/{member_id}", MemberInfoByIdResource())
    app.add_route("/member/info", MemberInfoResource())
    member_setting_resource = MemberSettingResource()
    app.add_route("/member/setting", member_setting_resource)
    app.add_route("/member/payment-setting",
                  member_setting_resource, suffix="payment")
    app.add_route("/member/invite/{invite_key:uuid}", MemberInviteResource())
    app.add_route("/member/register/{invite_key:uuid}", MemberRegisterResource())  # noqa: E501
    app.add_route("/member/register", MemberRegisterResource())  # noqa: E501
    app.add_route("/valid-invite/{invite_key:uuid}", ValidInviteResource())
    # get the job titles list
    app.add_route("/member/register/job-title", MemberJobTitles())
    app.add_route("/member/register/departments", MemberDepartments())
    app.add_route("/member/register/terms", MemberTerms())
    app.add_route("/member/register/tzlist", MemberTimezones())
    app.add_route("/member/register/skills", MemberSkills())
    app.add_route("/member/register/industries", MemberIndustry())
    # 2FA of cell during registration

    verify_cell_resource = VerifyCell()
    app.add_route("/member/register/verification", Verification())
    app.add_route("/member/register/verify-cell", verify_cell_resource)
    app.add_route("/member/register/promo-code", PromoCodes())
    app.add_route("/member/register/verify-outgoing-cell", verify_cell_resource, suffix="outgoing")

    # This route is commneted out to prevent any registrations someone may be sniffing out
    # This will be enabled later on
    # app.add_route("/member/register", MemberRegistrationResource())  # noqa: E501
    app.add_route("/member/search", MemberSearchResource())
    app.add_route("/member/group/search", MemberGroupSearchResource())
    app.add_route(
        "/member/contact/security/{contact_member_id}", MemberContactSecurity())
    app.add_route("/member/contact", MemberContactResource())
    app.add_route(
        "/member/contact/request/{contact_member_id}", MemberContactAccept())
    app.add_route("/member/contacts/roles", MemberContactsRoles())
    app.add_route("/member/contacts/companies", MemberContactsCompanies())
    app.add_route("/member/contacts/countries", MemberContactsCountries())
    app.add_route("/member/file/{file_path}", FileDownloadResource())
    app.add_route("/member-contacts", ContactMembersResource())
    app.add_route("/member/text-mails",
                  ContactMembersTextMailsResource())

    app.add_route("/valid-session", ValidateSessionResource())
    app.add_route("/valid-session/xmpp", ValidateSessionResource(), suffix="xmpp")

    # member drive
    app.add_route("/drive/member/files", MemberFileCloud())
    app.add_route("/drive/member/files/bin", MemberFileBin())
    app.add_route("/drive/member/files/sharing", MemberShareFile())

    # group drive
    app.add_route("/drive/group/{group_id}/files", GroupFileCloud())
    app.add_route("/drive/group/{group_id}/files/bin", GroupFileBin())
    app.add_route("/drive/groups", FileGroupResource())

    app.add_route("/group", MemberGroupResource())
    app.add_route("/group/{group_id}", GroupDetailResource())
    app.add_route("/groups", MemberGroupResource())
    app.add_route("/groups/membership", GroupMembershipResource())
    app.add_route(
        "/group/activity/calendar/{group_id}", GroupActivityCalendarResource())
    app.add_route(
        "/group/activity/drive/{group_id}", GroupActivityDriveResource())
    app.add_route("/member/group/invite", GroupMemberInviteResource())
    app.add_route(
        "/member/group/membership/request/{group_id}", GroupMemberAccept())
    app.add_route("/member/group-members", GroupMembersResource())
    app.add_route("/member/group/security/{group_id}", MemberGroupSecurity())
    app.add_route("/system/activity/invite", SystemActivityResource("invites"))
    app.add_route("/system/activity/session",
                  SystemActivityResource("sessions"))
    app.add_route("/system/activity/threat", SystemActivityResource("threats"))
    app.add_route("/system/activity/behaviour",
                  SystemActivityResource("behaviour"))
    app.add_route("/system/activity/users", SystemActivityUsersResource())
    app.add_route("/system/activity/members/registered",
                  SystemMemberResource())

    app.add_route("/member/activity", ActivitiesResource())

    # Activity New version
    app.add_route("/system/activity/activity", SystemActivitySessionResource())
    app.add_route("/system/activity/security",
                  SystemActivitySecurityResource())
    app.add_route("/system/activity/message", SystemActivityMessageResource())
    app.add_route("/system/activity/group", SystemActivityGroupResource())
    app.add_route("/system/activity/invitations",
                  SystemActivityInvitationsResource())

    app.add_route("/languages", LanguageResource())

    app.add_route("/member/scheduler/setting",
                  MemberSchedulerSettingResource())
    app.add_route("/member/schedule/event", MemberScheduleEventResource())
    app.add_route("/member/schedule/colors", MemberScheduleEventColors())
    app.add_route("/member/schedule/attach", EventAttachmentResorce())
    app.add_route("/member/schedule/holiday", MemberScheduleHolidayResource())
    app.add_route("/member/schedule/event/directions", MemberEventDirections())

    # app.add_route("/member/schedule/event-invite/add-single", MemberScheduleEventInviteAddSingleResource())
    app.add_route("/member/schedule/event-invite",
                  MemberScheduleEventInviteResource())
    app.add_route("/member/schedule/event-invite/set-status",
                  MemberScheduleEventInviteSetStatusResource())

    app.add_route("/member/register/country", CountryCodeResource())
    app.add_route("/member/role", RolesResource())
    app.add_route("/member/page/settings", PageSettingsResource())

    # Avatars
    member_avatar_resource = MemberAvatarResource()
    app.add_route("/member/avatar", member_avatar_resource,
                  suffix="deprecated")
    app.add_route("/member/{member_id:int}/avatar", member_avatar_resource)

    # Notifications setting
    app.add_route("/member/notifications/setting",
                  MemberNotificationsSetting())

    # Draft
    draft_resource = MailDraftComposeResource()
    app.add_route("/mail/draft", draft_resource)  # POST
    app.add_route("/mail/draft/list", draft_resource, suffix="list")  # GET
    app.add_route("/mail/draft/{mail_id}",
                  draft_resource, suffix="draft")  # DELETE
    app.add_route("/mail/draft/get/{mail_id}",
                  draft_resource, suffix="detail")  # GET
    app.add_route("/mail/draft/send", draft_resource, suffix="send")  # POST
    app.add_route("/mail/draft/members", draft_resource, suffix="members")

    # Attachment
    attach_resource = MailAttachmentResource()
    app.add_route("/mail/attach", attach_resource)
    app.add_route("/mail/attach/{mail_id}/{attachment_id}",
                  attach_resource, suffix="attachment")

    # Inbox
    mail_inbox_resource = MailInboxResource()
    app.add_route("/mail/threads", mail_inbox_resource, suffix="thread_mails")
    app.add_route("/mail/inbox", mail_inbox_resource, suffix="list")
    app.add_route("/mail/inbox/members", mail_inbox_resource, suffix="members")

    app.add_route("/mail/{mail_id}", mail_inbox_resource, suffix="detail")
    app.add_route("/mail/forward", mail_inbox_resource, suffix="forward")

    # Star
    mail_star_resource = MailStaredResource()
    app.add_route("/mail/star", mail_star_resource)  # POST
    app.add_route("/mail/star/list", mail_star_resource, suffix="list")  # GET
    app.add_route("/mail/star/{mail_id}", mail_star_resource, suffix="detail")
    app.add_route("/mail/star/members", mail_star_resource, suffix="members")

    # Trash
    mail_trash_resource = MailTrashResource()
    app.add_route("/mail/trash", mail_trash_resource)  # POST - Add to trash
    app.add_route("/mail/trash/list", mail_trash_resource,
                  suffix="list")  # GET - Trash list
    # GET - Trash mail detail
    app.add_route("/mail/trash/{mail_id}",
                  mail_trash_resource, suffix="detail")
    app.add_route("/mail/trash/{mail_id}/{mail_xref}",
                  mail_trash_resource, suffix="detail_rm")
    # DELETE - delete email for ever
    app.add_route("/mail/trash/mv/origin", mail_trash_resource,
                  suffix="remove")  # POST - move mail to origin
    app.add_route("/mail/trash/mv/archive", mail_trash_resource,
                  suffix="archive")  # POST - Add to archive
    app.add_route("/mail/trash/members", mail_trash_resource, suffix="members")

    # Archive
    mail_archive_resource = MailArchiveResource()
    # POST - Add to trash
    app.add_route("/mail/archive", mail_archive_resource)
    app.add_route("/mail/archive/list", mail_archive_resource,
                  suffix="list")  # GET - Trash list
    # GET - Trash mail detail
    app.add_route("/mail/archive/{mail_id}",
                  mail_archive_resource, suffix="detail")
    app.add_route("/mail/archive/{mail_id}/{mail_xref}",
                  mail_archive_resource, suffix="detail_rm")
    # DELETE - delete email for ever
    app.add_route("/mail/archive/mv/origin", mail_archive_resource,
                  suffix="remove")  # POST - move mail to origin
    app.add_route("/mail/archive/mv/trash", mail_archive_resource,
                  suffix="trash")  # POST - Add to archive
    app.add_route("/mail/archive/members",
                  mail_archive_resource, suffix="members")

    # Sent
    mail_sent_resource = MailSentResource()
    app.add_route("/mail/sent/list", mail_sent_resource, suffix="list")  # GET
    app.add_route("/mail/sent/{mail_id}", mail_sent_resource, suffix="detail")
    app.add_route("/mail/sent/members", mail_sent_resource, suffix="members")

    # Signature
    mail_sign_resource = MailSettingsResource()
    # POST - move mail to origin
    app.add_route("/mail/settings", mail_sign_resource)
    app.add_route("/mail/sign", mail_sign_resource,
                  suffix="sign")  # POST - move mail to origin
    app.add_route("/mail/sign/list", mail_sign_resource,
                  suffix="list")  # POST - Add to archive

    mail_member_folder_resource = MailMemberFolderResource()
    app.add_route("/mail/folders", mail_member_folder_resource)
    app.add_route("/mail/folders/mv",
                  mail_member_folder_resource, suffix="move")

    # Routes for video mail

    video_mail_resource = MemberVideoMailResource()

    app.add_route("/mail/video/all", video_mail_resource, suffix="all")
    app.add_route(
        "/mail/video/contact/{member_id:int}", video_mail_resource, suffix="contact")
    app.add_route(
        "/mail/video/contact/{member_id:int}/video_mail/{video_mail_id:int}", video_mail_resource, suffix="contact")
    app.add_route("/mail/video/group/{group_id:int}",
                  video_mail_resource, suffix="group")
    app.add_route(
        "/mail/video/group/{group_id:int}/video_mail/{video_mail_id:int}", video_mail_resource, suffix="group")

    # Routes for forum

    forum_resource = ForumResource()

    app.add_route("/groups/{group_id:int}/forum/topics", forum_resource)
    app.add_route(
        "/forum/topics/post/{post_id}/like", forum_resource, suffix="like")
    app.add_route("/forum/topics/post", forum_resource, suffix="post")
    app.add_route("/forum/topics/{topic_id:int}",
                  forum_resource, suffix="detail")

    # Routes for contact newsfeeds

    newsfeeds_resource = NewsFeedsResource()

    app.add_route("/newsfeeds", newsfeeds_resource)
    app.add_route("/newsfeeds/{topic_id:int}",
                  newsfeeds_resource, suffix="post")

    # Routes for password manager

    password_resource = PasswordResource()

    app.add_route(
        "/password/favicon/{password_id:int}", password_resource, suffix="favicon")
    app.add_route("/password/{password_id:int}",
                  password_resource, suffix="detail")
    app.add_route("/password", password_resource)

    # Routes for Chat App
    app.add_route("/chat", ChatView())

    # Call Notificaitons

    # Project
    project_resource = ProjectResource()
    app.add_route("/project", project_resource)
    app.add_route("/project/{project_id:int}", project_resource)
    app.add_route("/project/{project_id:int}/soft_delete",
                  project_resource, suffix="soft_delete")
    app.add_route("/project/{project_id:int}/restore",
                  project_resource, suffix="project_restore")
    app.add_route("/project/{project_id:int}/suspend",
                  project_resource, suffix="project_suspend")
    app.add_route("/project/{project_id:int}/unsuspend",
                  project_resource, suffix="project_unsuspend")
    app.add_route("/project/roles", project_resource, suffix="roles")
    app.add_route("/project/member", project_resource, suffix="member")
    app.add_route("/project/member/roles",
                  project_resource, suffix="member_role")
    app.add_route("/project/member/privilege",
                  project_resource, suffix="member_privilege")
    app.add_route("/project/element", project_resource, suffix="element")
    app.add_route("/project/element/{element_id:int}",
                  project_resource, suffix="element")
    app.add_route("/project/element/{element_id:int}/restore",
                  project_resource, suffix="element_restore")
    app.add_route("/project/element/{element_id:int}/suspend",
                  project_resource, suffix="element_suspend")
    app.add_route("/project/element/{element_id:int}/unsuspend",
                  project_resource, suffix="element_unsuspend")
    app.add_route("/project/element/note",
                  project_resource, suffix="note")
    app.add_route("/project/element/note/{note_id:int}",
                  project_resource, suffix="note")
    app.add_route("/project/element/time",
                  project_resource, suffix="time")
    app.add_route("/project/element/time/{time_id:int}",
                  project_resource, suffix="time")
    app.add_route("/project/milestone", project_resource, suffix="milestone")
    app.add_route(
        "/project/milestone/{milestone_id:int}", project_resource, suffix="milestone")
    app.add_route(
        "/project/invite_reaction/{invite_id:int}", project_resource, suffix="invite_reaction")
    app.add_route(
        "/project/deactivate/{project_id:int}", project_resource, suffix="deactivate")
    app.add_route(
        "/project/contract-rate/{contract_id:int}", project_resource, suffix="contract_rate")
    # app.add_route("/project/contract", project_resource, suffix="contract")
    # app.add_route(
    #     "/project/contract/{contract_id:int}", project_resource, suffix="contract")

    # Upcoming Events
    app.add_route("/member/event/upcoming", MemberUpcomingEvents())

    member_event_invitation_resource = MemberEventInvitations()
    # Event Invitations
    app.add_route("/member/event/invite", member_event_invitation_resource)
    # Event Invitation Accept/Decline
    app.add_route(
        "/member/event/invite/{event_invite_id}", member_event_invitation_resource)
    app.add_route("/notify", IncomingCallView())

    # Report Bugs
    app.add_route("/member/report/bug", BugReportResource())
    app.add_route("/member/report/bug/users", BugReportUsersResource())

    # Company

    company_resource = CompanyResource()

    app.add_route("/company", company_resource)
    app.add_route("/company/{company_id:int}",
                  company_resource, suffix="detail")
    app.add_route("/company/picture/{company_id:int}",
                  company_resource, suffix="picture")
    app.add_route("/company/details/{company_id:int}",
                  company_resource, suffix="details_update")
    app.add_route("/company/members/{company_id:int}",
                  company_resource, suffix="members_update")

    app.add_route("/company/member", company_resource, suffix="member")

    app.add_route("/company/unregistered", CompanyUnregisteredResource())

    # Billing resource
    billing_resource = BillingResource()

    app.add_route("/billing/currency", billing_resource, suffix="currency")
    app.add_route("/billing/weekly", billing_resource, suffix="weekly_billing")
    # Admin Resources
    admin_resource = AdminMemberResource()
    app.add_route("/admin/member/{member_id:int}/session/{session_id:uuid}",
                  admin_resource, suffix="session")
    app.add_route("/admin/member/{member_id:int}",
                  admin_resource, suffix="member")

    app.add_route("/facial-recognition", FacialRecognitionResource())

    # Github Webhook
    app.add_route("/github/webhooks", GithubWebhooksResource())
    app.add_route("/github/repo/setup", GithubRepoListResource())
    app.add_route("/github/oauth/login", GithubLoginResource())
    app.add_route("/github/oauth", GithubOAuthResource())

    # o365
    app.add_route("/o365/oauth/login", O365LoginResource())
    app.add_route("/o365/auth", O365OAuthResource())

    # trello
    app.add_route("/trello/oauth/login", TrelloLoginResource())
    app.add_route("/trello/auth", TrelloOAuthResource())

    # Streaming
    stream_resource = StreamResource()
    app.add_route("/streaming/upload-video", stream_resource, suffix="video")
    app.add_route("/streaming/upload", stream_resource)
    app.add_route("/streaming/videos", stream_resource)
    app.add_route("/streaming/video/{id:int}", stream_resource)

    stream_category_resource = StreamCategoryResource()
    app.add_route("/streaming/categories", stream_category_resource)

    stream_type_resource = StreamTypeResource()
    app.add_route("/streaming/types", stream_type_resource)

    # twilio
    app.add_route("/twilio/outgoing-caller/{twilio_verify_id}", verify_cell_resource, suffix="verified")
    # app.add_route("/twilio/message")
    # app.add_route("/twilio/message/status")
    twilio_resource = TwilioResource()
    app.add_route("/twilio/voice", twilio_resource, suffix="voice")
    # app.add_route("/twilio/voice/status", twilio_resource, suffix="voice_status")
    app.add_route("/twilio/get-token", twilio_resource, suffix="token")
