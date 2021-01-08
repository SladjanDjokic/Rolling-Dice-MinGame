import logging
from app import configure
from app.config import parser, settings
from app.da.member import MemberDA
from app.da.file_sharing import FileTreeDA

logger = logging.getLogger(__name__)


# {
#     "member_id": member_id,
#     "email": email,
#     "create_date": create_date,
#     "update_date": update_date,
#     "username": username,
#     "status": status,
#     "first_name": first_name,
#     "last_name": last_name,
#     "member_name": f'{first_name} {last_name}',
#     "main_file_tree": main_file_tree,
#     "bin_file_tree": bin_file_tree
# }
def get_all_members():
    members = MemberDA._get_all_members()
    return members


def create_trees(member):
    tree_id, file_tree_id = FileTreeDA().create_tree('main', 'member', True)
    bin_file_tree_id = FileTreeDA().create_tree('bin', 'member')

    MemberDA.assign_tree('main', member['member_id'], tree_id)
    MemberDA.assign_tree('bin', member['member_id'], bin_file_tree_id)

    return tree_id, file_tree_id


def create_default_folders(member, tree_id, file_tree_id):
    # Add default folders for Drive
    default_drive_folders = ['Documents', 'Passwords', 'Pictures', 'PowerPoints', 'Spreadsheets', 'Videos']
    default_drive_folders.sort()

    for folder_name in default_drive_folders:
        FileTreeDA().create_file_tree_entry(
            tree_id=tree_id,
            parent_id=file_tree_id,
            member_file_id=None,
            display_name=folder_name
        )


def init_app():
    args = vars(parser.parse_args())
    # Get the configuration values from runtime/env/parameters
    # Essentially puts them in the settings variable
    configure(**args)
    return


if __name__ == "__main__":
    init_app()

    settings.set('database.host', 'localhost')
    # print(f"Member ID: {member}")
    members = get_all_members()

    for member in members:
        # print(f"Member: {member}")
        print(f"Member ID: {member['member_id']} email: {member['email']} main_file_tree: {member['main_file_tree']}")

        tree_id = member['main_file_tree']
        logger.debug(f"Main file tree: {tree_id}")
        if not tree_id:
            tree_id, file_tree_id = create_trees(member)
            logger.debug(f"Created file tree: {tree_id} {file_tree_id}")
        else:
            file_tree_id = FileTreeDA().get_tree_root_id(tree_id)
            logger.debug(f"getting file tree id: {tree_id} {file_tree_id}")

    members = get_all_members()
    for member in members:
        tree_id = member['main_file_tree']
        file_tree_id = FileTreeDA().get_tree_root_id(tree_id)
        create_default_folders(member, tree_id, file_tree_id)
