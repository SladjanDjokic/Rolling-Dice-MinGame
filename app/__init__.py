import logging
import os
import falcon
# from falcon_auth import FalconAuthMiddleware, TokenAuthBackend
from falcon_multipart.middleware import MultipartMiddleware

from app.calls.views import IncomingCallView
from app.chat.views import ChatView
from app.config import parser, settings
from app.middleware import CrossDomain, KafkaProducerMiddleware  # , JSONTranslator
from app.resources.member import MemberRegisterResource, MemberResource, MemberSearchResource, \
    MemberGroupSearchResource, MemberContactResource, ContactMembersResource, \
    MemberInfoResource, MemberJobTitles, MemberTerms, MemberDepartments, MemberContactsRoles, \
    MemberContactsCompanies, MemberContactsCountries, MemberTimezones, MemberInfoByIdResource, MemberContactSecurity
from app.resources.verification import Verification
from app.resources.verifycell import VerifyCell
from app.resources.promo_codes import PromoCodes
from app.resources.invite import MemberInviteResource, ValidInviteResource
from app.resources.login import MemberLoginResource
from app.resources.forgot_password import MemberForgotPasswordResource
from app.resources.reset_password import MemberResetPasswordResource
from app.resources.change_password import MemberChangePasswordResource
from app.resources.logout import MemberLogoutResource
from app.resources.session import SessionResource, ValidateSessionResource
from app.resources.file_download import FileDownloadResource
from app.resources.file_sharing import FileStorage, FileStorageDetail, ShareFile, ShareFileDetail, \
    DownloadStorageFile, DownloadSharedFile, MemberFileCloud, MemberFileBin, MemberShareFile, GroupFileCloud, \
    GroupFileBin
from app.resources.group import MemberGroupResource, GroupMembershipResource, GroupDetailResource, \
    GroupMemberInviteResource, GroupMembersResource, MemberGroupSecurity
from app.resources.file_sharing import FileStorage, FileStorageDetail, \
    ShareFile, ShareFileDetail, DownloadStorageFile, DownloadSharedFile, \
    FileGroupResource
from app.resources.system import SystemActivityResource
from app.resources.language import LanguageResource
from app.resources.static import StaticResource
from app.resources.member_scheduler_setting import MemberSchedulerSettingResource
from app.resources.member_schedule_event import MemberScheduleEventResource, MemberScheduleEventColors, EventAttachmentResorce
from app.resources.member_schedule_holiday import MemberScheduleHolidayResource
from app.resources.member_schedule_event_invite import MemberScheduleEventInviteResource, \
    MemberScheduleEventInviteAddSingleResource, MemberScheduleEventInviteSetStatusResource
from app.resources.country import CountryCodeResource
from app.resources.mail import MailDraftComposeResource, MailAttachmentResource, MailInboxResource, MailStaredResource, \
    MailTrashResource, MailArchiveResource, MailSettingsResource, MailSentResource, MailMemberFolderResource
from app.resources.role import RolesResource
from app.resources.avatar import AvatarResource
from app.resources.activity import ActivitiesResource
# from app.resources.memberfile import
# from app.resources.keygen import KeyGenResource, KeyGenFileUpload

from app.da.__init__ import check_trees

from app.util.config import setup_vyper
from app.util.error import error_handler
from app.util.logging import setup_logging

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


def create_app():
    setup_logging()

    app = falcon.API(
        middleware=[
            CrossDomain(),
            # FalconAuthMiddleware(auth_backend),
            MultipartMiddleware(),
            KafkaProducerMiddleware(),
            # JSONTranslator()
        ],
    )

    app.add_error_handler(Exception, error_handler)

    _setup_routes(app)

    # check_trees()

    return app


class HealthResource:
    def on_get(self, req, resp):
        resp.media = {'status': 'OK', 'health': 1.0}


def start():
    logger.info("Environment: {}".format(settings.get("ENV_NAME")))


def _setup_routes(app):
    app.add_route('/healthz', HealthResource())

    # app.add_route('/demo/image-upload', KeyGenFileUpload())
    # app.add_route("/demo/keygen", KeyGenResource())
    app.add_route("/member/login", MemberLoginResource())
    app.add_route("/member/forgot", MemberForgotPasswordResource())
    app.add_route(
        "/member/reset-password/{forgot_key:uuid}", MemberResetPasswordResource())
    app.add_route("/member/change-password", MemberChangePasswordResource())
    app.add_route("/member/logout", MemberLogoutResource())
    app.add_route("/member/invite", MemberInviteResource())
    app.add_route("/member/info/{member_id}", MemberInfoByIdResource())
    app.add_route("/member/info", MemberInfoResource())
    app.add_route("/member/invite/{invite_key:uuid}", MemberInviteResource())
    app.add_route("/valid-invite/{invite_key:uuid}", ValidInviteResource())
    app.add_route("/member/register/{invite_key:uuid}", MemberRegisterResource())  # noqa: E501
    app.add_route("/member/register", MemberRegisterResource())  # noqa: E501
    # get the job titles list
    app.add_route("/member/register/job-title", MemberJobTitles())
    app.add_route("/member/register/departments", MemberDepartments())
    app.add_route("/member/register/terms", MemberTerms())
    app.add_route("/member/register/tzlist", MemberTimezones())
    # 2FA of cell during registration
    app.add_route("/member/register/verification", Verification())
    app.add_route("/member/register/verify-cell", VerifyCell())
    app.add_route("/member/register/promo-code", PromoCodes())

    # This route is commneted out to prevent any registrations someone may be sniffing out
    # This will be enabled later on
    # app.add_route("/member/register", MemberRegistrationResource())  # noqa: E501
    app.add_route("/member/search", MemberSearchResource())
    app.add_route("/member/group/search", MemberGroupSearchResource())
    member_resource = MemberResource()
    app.add_route("/member/{username}", member_resource)

    app.add_route("/member/contact/security/{contact_member_id}", MemberContactSecurity())
    app.add_route("/member/contact", MemberContactResource())
    app.add_route("/member/contacts/roles", MemberContactsRoles())
    app.add_route("/member/contacts/companies", MemberContactsCompanies())
    app.add_route("/member/contacts/countries", MemberContactsCountries())
    app.add_route("/member/file/{file_path}", FileDownloadResource())
    app.add_route("/member-contacts", ContactMembersResource())
    app.add_route('/session/{session_id}', SessionResource)
    app.add_route("/valid-session", ValidateSessionResource())
    # app.add_route("/cloud/files", MemberFile())
    app.add_route("/cloud/files", FileStorage())
    app.add_route("/cloud/files/new", MemberFileCloud())
    app.add_route("/cloud/files/bin", MemberFileBin())
    app.add_route("/cloud/files/sharing", MemberShareFile())
    app.add_route("/cloud/files/group/{group_id}", GroupFileCloud())
    app.add_route("/cloud/files/group/bin/{group_id}", GroupFileBin())
    app.add_route("/cloud/files/groups", FileGroupResource())
    app.add_route("/cloud/files/details/{file_id}", FileStorageDetail())
    app.add_route("/cloud/files/download/{file_id}", DownloadStorageFile())
    app.add_route("/cloud/files/share", ShareFile())
    app.add_route("/cloud/files/share/details/{shared_key}", ShareFileDetail())
    app.add_route(
        "/cloud/files/share/download/{shared_key}", DownloadSharedFile())
    app.add_route("/static/{file_name}", StaticResource())
    app.add_route("/group", MemberGroupResource())
    app.add_route("/group/{group_id}", GroupDetailResource())
    app.add_route("/groups", MemberGroupResource())
    app.add_route("/groups/membership", GroupMembershipResource())
    app.add_route("/member/group/invite", GroupMemberInviteResource())
    app.add_route("/member/group-members", GroupMembersResource())
    app.add_route("/member/group/security/{group_id}", MemberGroupSecurity())
    app.add_route("/system/activity/invite", SystemActivityResource("invites"))
    app.add_route("/system/activity/session", SystemActivityResource("sessions"))

    app.add_route("/member/activity", ActivitiesResource())

    app.add_route("/languages", LanguageResource())

    app.add_route("/member/scheduler/setting",
                  MemberSchedulerSettingResource())
    app.add_route("/member/schedule/event", MemberScheduleEventResource())
    app.add_route("/member/schedule/colors", MemberScheduleEventColors())
    app.add_route("/member/schedule/attach", EventAttachmentResorce())
    app.add_route("/member/schedule/holiday", MemberScheduleHolidayResource())

    # app.add_route("/member/schedule/event-invite/add-single", MemberScheduleEventInviteAddSingleResource())
    app.add_route("/member/schedule/event-invite",
                  MemberScheduleEventInviteResource())
    app.add_route("/member/schedule/event-invite/set-status",
                  MemberScheduleEventInviteSetStatusResource())

    app.add_route("/member/register/country", CountryCodeResource())
    app.add_route("/member/role", RolesResource())
    app.add_route("/member/avatar", AvatarResource())

    # Draft
    draft_resource = MailDraftComposeResource()
    app.add_route("/mail/draft", draft_resource)  # POST
    app.add_route("/mail/draft/list", draft_resource, suffix="list")  # GET
    app.add_route("/mail/draft/{mail_id}", draft_resource, suffix="draft")  # DELETE
    app.add_route("/mail/draft/get/{mail_id}", draft_resource, suffix="detail")  # GET
    app.add_route("/mail/draft/send", draft_resource, suffix="send")  # POST

    # Attachment
    attach_resource = MailAttachmentResource()
    app.add_route("/mail/attach", attach_resource)
    app.add_route("/mail/attach/{mail_id}/{attachment_id}",
                  attach_resource, suffix="attachment")

    # Inbox
    mail_inbox_resource = MailInboxResource()
    app.add_route("/mail/inbox", mail_inbox_resource, suffix="list")
    app.add_route("/mail/{mail_id}", mail_inbox_resource, suffix="detail")
    app.add_route("/mail/forward", mail_inbox_resource, suffix="forward")

    # Star
    mail_star_resource = MailStaredResource()
    app.add_route("/mail/star", mail_star_resource)  # POST
    app.add_route("/mail/star/list", mail_star_resource, suffix="list")  # GET
    app.add_route("/mail/star/{mail_id}", mail_star_resource, suffix="detail")

    # Trash
    mail_trash_resource = MailTrashResource()
    app.add_route("/mail/trash", mail_trash_resource)  # POST - Add to trash
    app.add_route("/mail/trash/list", mail_trash_resource, suffix="list")  # GET - Trash list
    app.add_route("/mail/trash/{mail_id}", mail_trash_resource, suffix="detail")  # GET - Trash mail detail
    #                                                                                 DELETE - delete email for ever
    app.add_route("/mail/trash/mv/origin", mail_trash_resource, suffix="remove")  # POST - move mail to origin
    app.add_route("/mail/trash/mv/archive", mail_trash_resource, suffix="archive")  # POST - Add to archive

    # Archive
    mail_archive_resource = MailArchiveResource()
    app.add_route("/mail/archive", mail_archive_resource)  # POST - Add to trash
    app.add_route("/mail/archive/list", mail_archive_resource, suffix="list")  # GET - Trash list
    app.add_route("/mail/archive/{mail_id}", mail_archive_resource, suffix="detail")  # GET - Trash mail detail
    #                                                                                 DELETE - delete email for ever
    app.add_route("/mail/archive/mv/origin", mail_archive_resource, suffix="remove")  # POST - move mail to origin
    app.add_route("/mail/archive/mv/trash", mail_archive_resource, suffix="trash")  # POST - Add to archive

    # Sent
    mail_sent_resource = MailSentResource()
    app.add_route("/mail/sent/list", mail_sent_resource, suffix="list")  # GET
    app.add_route("/mail/sent/{mail_id}", mail_sent_resource, suffix="detail")

    # Signature
    mail_sign_resource = MailSettingsResource()
    app.add_route("/mail/settings", mail_sign_resource)  # POST - move mail to origin
    app.add_route("/mail/sign", mail_sign_resource, suffix="sign")  # POST - move mail to origin
    app.add_route("/mail/sign/list", mail_sign_resource, suffix="list")  # POST - Add to archive

    mail_member_folder_resource = MailMemberFolderResource()
    app.add_route("/mail/folders", mail_member_folder_resource)
    app.add_route("/mail/folders/mv", mail_member_folder_resource, suffix="move")

    # Routes for Chat App
    app.add_route("/chat", ChatView())

    # Call Notificaitons
    app.add_route("/notifications/incoming-call", IncomingCallView())
