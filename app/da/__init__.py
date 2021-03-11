from app.da.member import MemberDA
from app.da.group import GroupDA
from app.da.file_sharing import FileTreeDA
from app.da.group import GroupDA, GroupMembershipDA, GroupRole, GroupMemberStatus


def check_trees():
    '''
        Take all members and loop through them to add trees if Required
    '''
    all_members = MemberDA()._get_all_members()
    for member in all_members:
        main_file_tree = member["main_file_tree"]
        bin_file_tree = member["bin_file_tree"]
        member_id = member["member_id"]
        if not main_file_tree:
            tree_id = FileTreeDA().create_tree('main', 'member')
            MemberDA().assign_tree('main', member_id, tree_id)

        if not bin_file_tree:
            tree_id = FileTreeDA().create_tree('bin', 'member')
            MemberDA().assign_tree('bin', member_id, tree_id)

    '''
        Take all groups and do the same
    '''
    all_groups = GroupDA().get_all_groups()
    for group in all_groups:
        main_file_tree = group["main_file_tree"]
        bin_file_tree = group["bin_file_tree"]
        group_id = group["group_id"]
        if not main_file_tree:
            tree_id = FileTreeDA().create_tree('main', 'group')
            GroupDA().assign_tree('main', group_id, tree_id)

        if not bin_file_tree:
            tree_id = FileTreeDA().create_tree('bin', 'group')
            GroupDA().assign_tree('bin', group_id, tree_id)


def migrate_group_members():
    groups = GroupDA.get_all_groups()

    # Make all regular members being standard
    members = GroupMembershipDA.get_members_without_role()

    if members and len(members) > 0:
        for member in members:
            member_id = members["member_id"]
            group_id = members["group_id"]
            GroupMembershipDA.set_member_group_role(
                member_id, group_id, GroupRole.STANDARD.value)

    # Migrate all leaders
    if groups and len(groups) > 0:
        for group in groups:
            leader_id = group["group_leader_id"]
            group_id = group["group_id"]
            GroupMembershipDA.create_group_membership(
                group_id=group_id, member_id=leader_id, status=GroupMemberStatus.ACTIVE.value, group_role=GroupRole.OWNER.value)
