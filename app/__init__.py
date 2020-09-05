import logging
import os
import falcon
# from falcon_auth import FalconAuthMiddleware, TokenAuthBackend
from falcon_multipart.middleware import MultipartMiddleware

from app.config import parser, settings
from app.middleware import CrossDomain  # , JSONTranslator
from app.resources.member import MemberRegisterResource, MemberResource, MemberSearchResource, \
    MemberGroupSearchResource, MemberContactResource, ContactMembersResource, MemberJobTitles, MemberTerms
from app.resources.verify_cell import VerifyCell
from app.resources.invite import MemberInviteResource, ValidInviteResource
from app.resources.login import MemberLoginResource
from app.resources.forgot_password import MemberForgotPasswordResource
from app.resources.reset_password import MemberResetPasswordResource
from app.resources.change_password import MemberChangePasswordResource
from app.resources.logout import MemberLogoutResource
from app.resources.session import SessionResource, ValidateSessionResource
from app.resources.file_sharing import FileStorage, FileStorageDetail, ShareFile, ShareFileDetail, \
    DownloadStorageFile, DownloadSharedFile
from app.resources.group import MemberGroupResource, GroupMembershipResource, GroupDetailResource, \
    GroupMemberInviteResource, GroupMembersResource
from app.resources.file_sharing import FileStorage, FileStorageDetail, \
    ShareFile, ShareFileDetail, DownloadStorageFile, DownloadSharedFile
from app.resources.system import SystemActivitySessionResource, SystemActivityInviteResource
from app.resources.language import LanguageResource
from app.resources.static import StaticResource
from app.resources.member_scheduler_setting import MemberSchedulerSettingResource, MemberSchedulerSettingUpdateResource
from app.resources.member_schedule_event import MemberScheduleEventAddResource, MemberScheduleEventResource
from app.resources.member_schedule_holiday import MemberScheduleHolidayAddResource, MemberScheduleHolidayResource
from app.resources.member_schedule_event_invite import MemberScheduleEventInviteResource, \
    MemberScheduleEventInviteAddMultipleResource, MemberScheduleEventInviteAddSingleResource, \
    MemberScheduleEventInviteSetStatusResource
# from app.resources.memberfile import MemberFile
# from app.resources.keygen import KeyGenResource, KeyGenFileUpload

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
            # JSONTranslator()
        ],
    )

    app.add_error_handler(Exception, error_handler)

    _setup_routes(app)

    return app


def start():
    logger.info("Environment: {}".format(settings.get("ENV_NAME")))


def _setup_routes(app):
    # app.add_route('/demo/image-upload', KeyGenFileUpload())
    # app.add_route("/demo/keygen", KeyGenResource())
    app.add_route("/member/login", MemberLoginResource())
    app.add_route("/member/forgot", MemberForgotPasswordResource())
    app.add_route(
        "/member/reset-password/{forgot_key:uuid}", MemberResetPasswordResource())
    app.add_route("/member/change-password", MemberChangePasswordResource())
    app.add_route("/member/logout", MemberLogoutResource())
    app.add_route("/member/invite", MemberInviteResource())
    app.add_route("/member/invite/{invite_key:uuid}", MemberInviteResource())
    app.add_route("/valid-invite/{invite_key:uuid}", ValidInviteResource())
    app.add_route("/member/register/{invite_key:uuid}", MemberRegisterResource())  # noqa: E501
    app.add_route("/member/register", MemberRegisterResource())  # noqa: E501
    # get the job titles list
    app.add_route("/member/register/job-title", MemberJobTitles())
    app.add_route("/member/register/terms", MemberTerms())
    # 2FA of cell during registration
    app.add_route("/member/register/verify-cell", VerifyCell())

    # This route is commneted out to prevent any registrations someone may be sniffing out
    # This will be enabled later on
    # app.add_route("/member/register", MemberRegistrationResource())  # noqa: E501
    app.add_route("/member/search", MemberSearchResource())
    app.add_route("/member/group/search", MemberGroupSearchResource())
    app.add_route("/member/{username}", MemberResource())
    app.add_route("/member/contact", MemberContactResource())
    app.add_route("/member-contacts", ContactMembersResource())
    app.add_route('/session/{session_id}', SessionResource)
    app.add_route("/valid-session", ValidateSessionResource())
    # app.add_route("/cloud/files", MemberFile())
    app.add_route("/cloud/files", FileStorage())
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

    app.add_route("/system/activity/invite", SystemActivityInviteResource())
    app.add_route("/system/activity/session", SystemActivitySessionResource())

    app.add_route("/languages", LanguageResource())

    app.add_route("/member/scheduler/setting/set",
                  MemberSchedulerSettingUpdateResource())
    app.add_route("/member/scheduler/setting/get",
                  MemberSchedulerSettingResource())

    app.add_route("/member/schedule/event/add",
                  MemberScheduleEventAddResource())
    app.add_route("/member/schedule/event/get", MemberScheduleEventResource())

    app.add_route("/member/schedule/holiday/add",
                  MemberScheduleHolidayAddResource())
    app.add_route("/member/schedule/holiday/get",
                  MemberScheduleHolidayResource())

    # app.add_route("/member/schedule/event-invite/add-single", MemberScheduleEventInviteAddSingleResource())
    app.add_route("/member/schedule/event-invite/add",
                  MemberScheduleEventInviteAddMultipleResource())
    app.add_route("/member/schedule/event-invite/get",
                  MemberScheduleEventInviteResource())
    app.add_route("/member/schedule/event-invite/set-status",
                  MemberScheduleEventInviteSetStatusResource())
