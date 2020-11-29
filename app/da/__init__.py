from app.da.member import MemberDA
from app.da.group import GroupDA
from app.da.file_sharing import FileTreeDA


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
