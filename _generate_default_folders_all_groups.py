import logging
from app import configure
from app.config import parser, settings
from app.da.group import GroupDA
from app.da.file_sharing import FileTreeDA

logger = logging.getLogger(__name__)

def get_all_groups():
    groups = GroupDA().get_all_groups()
    return groups


def create_trees(group):
    tree_id, file_tree_id = FileTreeDA().create_tree('main', 'group', True)
    bin_file_tree_id = FileTreeDA().create_tree('bin', 'group')

    GroupDA.assign_tree('main', group['group_id'], tree_id)
    GroupDA.assign_tree('bin', group['group_id'], bin_file_tree_id)

    return tree_id, file_tree_id


def create_default_folders(group, tree_id, file_tree_id):
    # Add default folders for Drive
    default_drive_folders = settings.get('drive.default_folders')
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
    configure(**args)
    return


if __name__ == "__main__":
    init_app()

    settings.set('database.host', 'localhost')
    groups = get_all_groups()

    for group in groups:
        print(f"Group ID: {group['group_id']} main_file_tree: {group['main_file_tree']}")

        tree_id = group['main_file_tree']
        logger.debug(f"Main file tree: {tree_id}")
        if not tree_id:
            tree_id, file_tree_id = create_trees(group)
            logger.debug(f"Created file tree: {tree_id} {file_tree_id}")
        else:
            file_tree_id = FileTreeDA().get_tree_root_id(tree_id)
            logger.debug(f"getting file tree id: {tree_id} {file_tree_id}")

    groups = get_all_groups()
    for group in groups:
        tree_id = group['main_file_tree']
        file_tree_id = FileTreeDA().get_tree_root_id(tree_id)
        create_default_folders(group, tree_id, file_tree_id)
