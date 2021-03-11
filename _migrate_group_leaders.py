import logging
from app import configure
from app.config import parser, settings
from app.da.group import GroupDA, GroupMembershipDA, GroupRole, GroupMemberStatus

logger = logging.getLogger(__name__)


def init_app():
    args = vars(parser.parse_args())
    configure(**args)
    return


if __name__ == "__main__":
    init_app()

    settings.set('database.host', 'localhost')
    groups = GroupDA.get_all_groups()

    # Make all regular members being standard
    members = GroupMembershipDA.get_members_without_role()

    if len(members) > 0:
        for member in members:
            member_id = members["member_id"]
            group_id = members["group_id"]
            GroupMembershipDA.set_member_group_role(
                member_id, group_id, GroupRole.STANDARD.value)

    # Migrate all leaders
    if len(groups) > 0:
        for group in groups:
            leader_id = group["group_leader_id"]
            group_id = group["id"]
            GroupMembershipDA.create_group_membership(
                group_id=group_id, member_id=leader_id, status=GroupMemberStatus.ACTIVE.value, group_role=GroupRole.OWNER.value)
