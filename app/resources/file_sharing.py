import logging
import app.util.json as json
import app.util.request as request
from app import settings
from app.da.member import MemberDA
from app.da.file_sharing import FileStorageDA, ShareFileDA, FileTreeDA
from app.util.session import get_session_cookie, validate_session
from app.exceptions.file_sharing import FileShareExists, FileNotFound, \
    FileUploadCreateException, FileStorageUploadError
from app.exceptions.session import InvalidSessionError, UnauthorizedSession
from operator import itemgetter

logger = logging.getLogger(__name__)


class FileStorage(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.file_storage'),
                                    "topic": settings.get('kafka.topics.files')
                                    },
                           "GET": {"event_type": settings.get('kafka.event_types.get.file_storage'),
                                   "topic": settings.get('kafka.topics.files')
                                   },
                           "PUT": {"event_type": settings.get('kafka.event_types.put.file_storage'),
                                   "topic": settings.get('kafka.topics.files')
                                   },
                           "DELETE": {"event_type": settings.get('kafka.event_types.delete.file_storage'),
                                      "topic": settings.get('kafka.topics.files')
                                      },
                           }

    @staticmethod
    def on_post(req, resp):
        (member_id, file_length, category) = request.get_json_or_form(
            "memberId", "fileLength", "category", req=req)

        member = MemberDA().get_member(member_id)

        if not member:
            resp.body = json.dumps({
                "message": "Member does not exist",
                "status": "warning",
                "success": False
            })
            return

        try:
            file_count = int(file_length)
            for index in range(0, file_count):

                file = req.get_param(f'file{index}')
                file_size_bytes = req.get_param(f'file{index}_size')
                file_name = req.get_param(f'file{index}_key')

                file_ids_to_delete = json.loads(req.get_param(
                    f'file{index}_replace_file_ids'))
                # Unencrypted fiels will have undefined
                iv = req.get_param(f'file{index}_iv')
                if iv == 'undefined':
                    iv = None
                file_id = FileStorageDA(
                ).store_file_to_storage(file)
                status = 'available'
                logger.debug(f'FILE STORAGE IDENTIFIER: {file_id}')

                res = FileStorageDA().create_member_file_entry(
                    file_id=file_id,
                    file_name=file_name,
                    member_id=member_id,
                    status=status,
                    file_size_bytes=file_size_bytes,
                    iv=iv)
                if not res:
                    raise FileUploadCreateException

                if len(file_ids_to_delete) > 0:
                    # We are deleting duplicates if the user
                    # requested file overwrites
                    for file_id in file_ids_to_delete:
                        FileStorageDA().delete_file(file_id)

            # Since is is possible that some files are deleted after this
            # upload, we have to push _all_ member files to front
            resp.body = json.dumps({
                "data": FileStorageDA().get_member_files(member),
                "description": "File uploaded successfully",
                "success": True
            }, default_parser=json.parser)
        except FileStorageUploadError as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })
        except Exception as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })

    @staticmethod
    def on_get(req, resp):
        member_id = req.get_param('memberId')
        member = MemberDA().get_member(member_id)
        if member:
            member_files = FileStorageDA().get_member_files(member)
            resp.body = json.dumps({
                "data": member_files if member_files else [],
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Can not get files for un-exising member",
                "success": False
            })

    @staticmethod
    def on_put(req, resp):
        data_dict = req.media
        member_id = data_dict["memberId"]
        member = MemberDA().get_member(member_id)
        if not member:
            resp.body = json.dumps({
                "message": "Member does not exist",
                "status": "warning",
                "success": False
            })
            return
        try:
            for file_to_rename in data_dict["renameItems"]:
                file_id = file_to_rename["fileId"]
                new_file_name = file_to_rename["newKey"]

                logger.debug(("Will attempt to rename file with "
                              f"Id {file_id} to {new_file_name}"))

                FileStorageDA().rename_file(file_id, new_file_name)
            member_files = FileStorageDA().get_member_files(member)
            resp.body = json.dumps({
                "data": member_files if member_files else [],
                "description": 'Synced successfully',
                "success": True
            }, default_parser=json.parser)

        except Exception as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })

    @staticmethod
    def on_delete(req, resp):
        (file_id_list,) = request.get_json_or_form("file_id_list", req=req)
        try:
            for file_id in file_id_list:
                FileStorageDA().delete_file(file_id)

            resp.body = json.dumps({
                "data": file_id_list,
                "description": "File removed successfully",
                "success": True
            }, default_parser=json.parser)
        except Exception:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            })


# A new resource to replace existing once it is finished


class MemberFileCloud(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.member_file_cloud'),
                                    "topic": settings.get('kafka.topics.files')
                                    },
                           "GET": {"event_type": settings.get('kafka.event_types.get.member_file_cloud'),
                                   "topic": settings.get('kafka.topics.files')
                                   },
                           "PUT": {"event_type": settings.get('kafka.event_types.put.member_file_cloud'),
                                   "topic": settings.get('kafka.topics.files')
                                   },
                           "DELETE": {"event_type": settings.get('kafka.event_types.delete.member_file_cloud'),
                                      "topic": settings.get('kafka.topics.files')
                                      },
                           }

    @staticmethod
    def on_get(req, resp):
        '''
            Receives member_id and returns both 'main' and 'bin' file trees
        '''
        session_id = get_session_cookie(req)
        session = validate_session(session_id)
        member_id = session["member_id"]
        member = MemberDA().get_member(member_id)

        if member:
            main_tree = FileTreeDA().get_tree(member_id, "main")
            bin_tree = FileTreeDA().get_tree(member_id, "bin")
            resp.body = json.dumps({
                "main_tree": main_tree,
                "bin_tree": bin_tree,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": "Can not get files for un-exising member",
                "success": False
            })

    @staticmethod
    def on_post(req, resp):
        session_id = get_session_cookie(req)
        session = validate_session(session_id)
        logger.debug((f"Session, {session}"))
        member_id = session["member_id"]
        logger.debug(f"Member id {member_id}")
        member = MemberDA().get_member(member_id)

        if not member:
            resp.body = json.dumps({
                "message": "Member does not exist",
                "status": "warning",
                "success": False
            })
            return

        (metadata,) = request.get_json_or_form("metadata", req=req)

        target_folder_id, nodes_to_bin, nodes_meta = itemgetter(
            "tagetFolderId", "nodesToDelete", "meta")(json.loads(metadata))
        # logger.debug("pusho", json.loads(metadata),
        #  target_folder_id, nodes_to_bin, nodes_meta

        try:
            tree_id = FileTreeDA().get_tree_id(target_id=member_id,
                                               target_type='member', tree_type='main')
            ''' 
                We iterate over nodes_meta starting with the nodes having level 0 and moving down
                We keep an xref between node_temp_id <=> inserted node_id  
            '''

            # 1) Inserting nodes accordingly
            sorted_nodes = sorted(
                nodes_meta, key=itemgetter('level'), reverse=False)

            temp_inserted_node_xref = dict()

            for node in sorted_nodes:
                (node_temp_id,
                 name,
                 isDir,
                 size,
                 parentId,
                 level,
                 iv
                 ) = itemgetter('node_temp_id', 'name', 'isDir', 'size', 'parentId', 'level', 'iv')(node)

                file_entry_id = None
                if not isDir:
                    # upload and insert file first
                    file = req.get_param(f"file_{node_temp_id}")
                    # storage_file_id = FileStorageDA().store_file_to_storage(file)
                    storage_file_id = FileStorageDA().put_file_to_storage(file)
                    # Create member file entry
                    member_file_id = FileTreeDA().create_member_file_entry(
                        file_id=storage_file_id,
                        file_name=name,
                        member_id=member_id,
                        status="available",
                        file_size_bytes=size,
                        iv=iv)
                    if not member_file_id:
                        raise FileUploadCreateException
                    else:
                        file_entry_id = member_file_id

                inserted_id = FileTreeDA().create_file_tree_entry(
                    tree_id=tree_id,
                    # Insert to folder if level == 0, otherwise, check our xref dict for parant
                    parent_id=target_folder_id if level == 0 else temp_inserted_node_xref[
                        parentId],
                    member_file_id=file_entry_id,
                    display_name=name
                )
                temp_inserted_node_xref[node_temp_id] = inserted_id

            # 2) Send overwrited nodes to Bin, if any
            if len(nodes_to_bin) > 0:
                bin_tree_id = FileTreeDA().get_tree_id(target_id=member_id,
                                                       target_type='member', tree_type='bin')
                for node_id in nodes_to_bin:
                    FileTreeDA().delete_branch(node_id, bin_tree_id)

            # 3) Compose and send new trees backj
            main_tree = FileTreeDA().get_tree(member_id, "main")
            bin_tree = FileTreeDA().get_tree(member_id, "bin")
            resp.body = json.dumps({
                "main_tree": main_tree,
                "bin_tree": bin_tree,
                "success": True
            }, default_parser=json.parser)

        except FileStorageUploadError as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })
        except Exception as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })

    @staticmethod
    def on_delete(req, resp):
        ''' Send files to Bin logic '''

        (node_ids,) = request.get_json_or_form(
            "node_ids_list", req=req)

        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            bin_tree_id = FileTreeDA().get_tree_id(member_id, 'member', "bin")
            for node_id in node_ids:
                FileTreeDA().delete_branch(node_id, bin_tree_id)

            main_tree = FileTreeDA().get_tree(member_id, "main")
            bin_tree = FileTreeDA().get_tree(member_id, "bin")
            resp.body = json.dumps({
                "main_tree": main_tree,
                "bin_tree": bin_tree,
                "success": True
            }, default_parser=json.parser)
        except FileStorageUploadError as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })
        except Exception as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })

    @staticmethod
    def on_put(req, resp):
        '''
            Here we change props of existing nodes (rename them and change their parents i.e. move them around the tree)
        '''
        (changes,) = request.get_json_or_form("changes", req=req)

        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]
            main_tree_id = FileTreeDA().get_tree_id(member_id, "member", "main")
            bin_tree_id = FileTreeDA().get_tree_id(member_id, "member", "bin")

            # TODO: Stuff goes here
            for change in changes:
                (node_id, isDir, member_file_id, parent_id,
                 name, isKeepOriginal, deleteId) = itemgetter("node_id", "isDir", "file_id", "parentId",
                                                              "name", "isKeepOriginal", "deleteId")(change)

                if not isDir:
                    # Make changes to member_file table for files
                    FileStorageDA().rename_file(member_file_id, name)

                # Make changes to file_tree_items either way if folder or file

                if isKeepOriginal:
                    # We just create another node using the right parameters, original node stays as is
                    FileTreeDA().create_file_tree_entry(
                        main_tree_id, parent_id, member_file_id, name)
                else:
                    # We just move that original node to another location
                    FileTreeDA().modify_branch(node_id, name, parent_id)

                if deleteId:
                    # Delete a branch if required
                    FileTreeDA().delete_branch(deleteId, bin_tree_id)

            main_tree = FileTreeDA().get_tree(member_id, "main")
            bin_tree = FileTreeDA().get_tree(member_id, "bin")
            resp.body = json.dumps({
                "main_tree": main_tree,
                "bin_tree": bin_tree,
                "success": True
            }, default_parser=json.parser)
        except FileStorageUploadError as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })
        except Exception as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })


class MemberFileBin(object):

    def __init__(self):
        self.kafka_data = {
                           "PUT": {"event_type": settings.get('kafka.event_types.put.member_file_bin'),
                                   "topic": settings.get('kafka.topics.files')
                                   },
                           "DELETE": {"event_type": settings.get('kafka.event_types.delete.member_file_bin'),
                                      "topic": settings.get('kafka.topics.files')
                                      },
                           }

    @staticmethod
    def on_delete(req, resp):
        ''' Delete forever logic goes here '''
        (node_ids,) = request.get_json_or_form("node_ids_list", req=req)
        session_id = get_session_cookie(req)
        session = validate_session(session_id)
        member_id = session["member_id"]
        try:
            for node_id in node_ids:
                FileTreeDA().delete_branch_forever(node_id)

            main_tree = FileTreeDA().get_tree(member_id, "main")
            bin_tree = FileTreeDA().get_tree(member_id, "bin")
            resp.body = json.dumps({
                "main_tree": main_tree,
                "bin_tree": bin_tree,
                "success": True
            }, default_parser=json.parser)

        except FileStorageUploadError as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })
        except Exception as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })

    @staticmethod
    def on_put(req, resp):
        ''' Restore from Bin logic goes here '''
        (node_ids,) = request.get_json_or_form("node_ids_list", req=req)

        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]
            main_tree_id = FileTreeDA().get_tree_id(member_id, "member", "main")

            for node_id in node_ids:
                FileTreeDA().restore_branch(node_id, main_tree_id)

            main_tree = FileTreeDA().get_tree(member_id, "main")
            bin_tree = FileTreeDA().get_tree(member_id, "bin")
            resp.body = json.dumps({
                "main_tree": main_tree,
                "bin_tree": bin_tree,
                "success": True
            }, default_parser=json.parser)
        except FileStorageUploadError as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })
        except Exception as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })


class MemberShareFile(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.member_share_file'),
                                    "topic": settings.get('kafka.topics.files')
                                    },
                           "PUT": {"event_type": settings.get('kafka.event_types.put.member_share_file'),
                                   "topic": settings.get('kafka.topics.files')
                                   },
                           "DELETE": {"event_type": settings.get('kafka.event_types.delete.member_share_file'),
                                      "topic": settings.get('kafka.topics.files')
                                      },
                           }
    @staticmethod
    def on_post(req, resp):
        ''' Receive information over files shared with individuals
            When a file is shared
                => a record in member_shares is created
                => file appears in the tree of the consumer member
        '''

        try:
            (targetType, targets, fileList) = request.get_json_or_form(
                "targetType", "targets", "fileList", req=req)

            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            for target_id in targets:
                for file in fileList:
                    # logger.debug(member_id)
                    branch_root_id = file["id"]
                    # this is the reference to member_files
                    file_id = file["file_id"]
                    name = file["name"]

                    # create file tree entry in target member's tree
                    target_tree_id = FileTreeDA().get_tree_id(target_id, targetType, "main")
                    # Shared files put to root

                    FileTreeDA().share_branch(
                        member_id, target_tree_id, branch_root_id)

            main_tree = FileTreeDA().get_tree(member_id, "main")
            bin_tree = FileTreeDA().get_tree(member_id, "bin")
            resp.body = json.dumps({
                "main_tree": main_tree,
                "bin_tree": bin_tree,
                "success": True
            }, default_parser=json.parser)

        except FileStorageUploadError as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })
        except Exception as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })

    @staticmethod
    def on_delete(req, resp):
        ''' When user unshares the file, or the consumer doesn't want it shared with him anymore'''
        try:
            (share_id,) = request.get_json_or_form("share_id", req=req)

            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]

            logger.debug('yoda', share_id)
            FileTreeDA().unshare_node(share_id)

            main_tree = FileTreeDA().get_tree(member_id, "main")
            bin_tree = FileTreeDA().get_tree(member_id, "bin")
            resp.body = json.dumps({
                "main_tree": main_tree,
                "bin_tree": bin_tree,
                "success": True
            }, default_parser=json.parser)

        except FileStorageUploadError as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })
        except Exception as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })

    @staticmethod
    def on_put(req, resp):
        ''' Here we handle user copying a file that was shared with him (either from group tree of own tree ) '''
        try:
            (node_ids, current_folder_id) = request.get_json_or_form(
                "node_ids", "current_folder_id", req=req)

            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]
            main_tree_id = FileTreeDA().get_tree_id(member_id, "member", "main")

            for node_id in node_ids:
                FileTreeDA().claim_shared_branch(
                    member_id, main_tree_id, node_id, current_folder_id)

            main_tree = FileTreeDA().get_tree(member_id, "main")
            bin_tree = FileTreeDA().get_tree(member_id, "bin")
            resp.body = json.dumps({
                "main_tree": main_tree,
                "bin_tree": bin_tree,
                "success": True
            }, default_parser=json.parser)

        except FileStorageUploadError as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })
        except Exception as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })


class GroupFileCloud(object):

    def __init__(self):
        self.kafka_data = {"POST": {"event_type": settings.get('kafka.event_types.post.group_file_cloud'),
                                    "topic": settings.get('kafka.topics.files')
                                    },
                           "GET": {"event_type": settings.get('kafka.event_types.get.group_file_cloud'),
                                   "topic": settings.get('kafka.topics.files')
                                   },
                           "PUT": {"event_type": settings.get('kafka.event_types.put.group_file_cloud'),
                                   "topic": settings.get('kafka.topics.files')
                                   },
                           "DELETE": {"event_type": settings.get('kafka.event_types.delete.group_file_cloud'),
                                      "topic": settings.get('kafka.topics.files')
                                      },
                           }

    @staticmethod
    def on_get(req, resp, group_id):
        '''
            Returns both 'main' and 'bin' trees for a given group id
        '''
        logger.debug(f"Group tree {group_id}")
        main_tree = FileTreeDA().get_group_tree(group_id, "main")
        bin_tree = FileTreeDA().get_group_tree(group_id, "bin")
        logger.debug(
            f'GroupFileCloud. group_id: {group_id} len of main_tree: {len(main_tree)} main_tree: {main_tree[0]["id"]}')

        if len(main_tree) > 0 and main_tree[0]['id'] is None:
            logger.debug(f'main_tree for groud with id {group_id} not exist. Will create it')
            main_file_tree_id = FileTreeDA().create_group_tree("main")
            bin_file_tree_id = FileTreeDA().create_group_tree("bin")
            logger.debug(f'file_tree id: {main_file_tree_id} {bin_file_tree_id}')
            updated_row_id = FileTreeDA.bind_group_tree_with(main_file_tree_id=main_file_tree_id,
                                                             bin_file_tree_id=bin_file_tree_id,
                                                             member_group_id=group_id)
            logger.debug(f'updated_row_id: {updated_row_id}')
            main_file_tree_root_folder_id = FileTreeDA().create_group_tree_root_folder(main_file_tree_id, 'main folder')
            bin_file_tree_root_folder_id = FileTreeDA().create_group_tree_root_folder(bin_file_tree_id, 'bin folder')
            logger.debug(
                f'root folders for group with id {group_id} created: main: {main_file_tree_root_folder_id} bin: {bin_file_tree_root_folder_id}')

            main_tree = FileTreeDA().get_group_tree(group_id, "main")
            bin_tree = FileTreeDA().get_group_tree(group_id, "bin")
            logger.debug(
                f'GroupFileCloud. group_id: {group_id} len of main_tree: {len(main_tree)} main_tree: {main_tree[0]["id"]}')

        resp.body = json.dumps({
            "main_tree": main_tree,
            "bin_tree": bin_tree,
            "success": True
        }, default_parser=json.parser)

    @staticmethod
    def on_post(req, resp, group_id):
        ''' 
            This allows the group leader to create folders
        '''
        (target_folder_id, folder_name) = request.get_json_or_form(
            "tagetFolderId", "folder_name", req=req)
        if folder_name:
            try:
                tree_id = FileTreeDA().get_tree_id(group_id, "group", "main")
                FileTreeDA().create_file_tree_entry(tree_id, target_folder_id, None, folder_name)
                main_tree = FileTreeDA().get_group_tree(group_id, "main")
                bin_tree = FileTreeDA().get_group_tree(group_id, "bin")
                resp.body = json.dumps({
                    "main_tree": main_tree,
                    "bin_tree": bin_tree,
                    "success": True
                }, default_parser=json.parser)
            except FileStorageUploadError as e:
                resp.body = json.dumps({
                    "message": e,
                    "success": False
                })
            except Exception as e:
                resp.body = json.dumps({
                    "message": e,
                    "success": False
                })
        else:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            logger.debug((f"Session, {session}"))
            member_id = session["member_id"]
            (metadata,) = request.get_json_or_form("metadata", req=req)

            target_folder_id, nodes_to_bin, nodes_meta = itemgetter(
                "tagetFolderId", "nodesToDelete", "meta")(json.loads(metadata))
            # logger.debug("pusho", json.loads(metadata),
            #  target_folder_id, nodes_to_bin, nodes_meta

            try:
                tree_id = FileTreeDA().get_tree_id(group_id, "group", "main")
                # tree_id = FileTreeDA().get_tree_id(target_id=member_id,
                #                                    target_type='member', tree_type='main')
                ''' 
                    We iterate over nodes_meta starting with the nodes having level 0 and moving down
                    We keep an xref between node_temp_id <=> inserted node_id  
                '''

                # 1) Inserting nodes accordingly
                sorted_nodes = sorted(
                    nodes_meta, key=itemgetter('level'), reverse=False)

                temp_inserted_node_xref = dict()

                for node in sorted_nodes:
                    (node_temp_id,
                     name,
                     isDir,
                     size,
                     parentId,
                     level,
                     iv
                     ) = itemgetter('node_temp_id', 'name', 'isDir', 'size', 'parentId', 'level', 'iv')(node)

                    file_entry_id = None
                    if not isDir:
                        # upload and insert file first
                        file = req.get_param(f"file_{node_temp_id}")
                        logger.error('file: ' + str(file))
                        # storage_file_id = FileStorageDA().store_file_to_storage(file)
                        storage_file_id = FileStorageDA().put_file_to_storage(file)
                        # Create member file entry
                        member_file_id = FileTreeDA().create_member_file_entry(
                            file_id=storage_file_id,
                            file_name=name,
                            member_id=member_id,
                            status="available",
                            file_size_bytes=size,
                            iv=iv)
                        if not member_file_id:
                            raise FileUploadCreateException
                        else:
                            file_entry_id = member_file_id

                    inserted_id = FileTreeDA().create_file_tree_entry(
                        tree_id=tree_id,
                        # Insert to folder if level == 0, otherwise, check our xref dict for parant
                        parent_id=target_folder_id if level == 0 else temp_inserted_node_xref[
                            parentId],
                        member_file_id=file_entry_id,
                        display_name=name
                    )
                    temp_inserted_node_xref[node_temp_id] = inserted_id

                # 2) Send overwrited nodes to Bin, if any
                if len(nodes_to_bin) > 0:
                    bin_tree_id = FileTreeDA().get_tree_id(target_id=member_id,
                                                           target_type='member', tree_type='bin')
                    for node_id in nodes_to_bin:
                        FileTreeDA().delete_branch(node_id, bin_tree_id)

                # 3) Compose and send new trees backj
                main_tree = FileTreeDA().get_group_tree(group_id, "main")
                bin_tree = FileTreeDA().get_group_tree(group_id, "bin")
                # main_tree = FileTreeDA().get_tree(member_id, "main")
                # bin_tree = FileTreeDA().get_tree(member_id, "bin")
                resp.body = json.dumps({
                    "main_tree": main_tree,
                    "bin_tree": bin_tree,
                    "success": True
                }, default_parser=json.parser)

            except FileStorageUploadError as e:
                resp.body = json.dumps({
                    "message": e,
                    "success": False
                })
            except Exception as e:
                resp.body = json.dumps({
                    "message": e,
                    "success": False
                })

    @staticmethod
    def on_delete(req, resp, group_id):
        ''' 
            This allows the group leader to send file to bin
        '''
        (node_ids,) = request.get_json_or_form(
            "node_ids_list", req=req)

        try:
            bin_tree_id = FileTreeDA().get_tree_id(group_id, 'group', "bin")
            for node_id in node_ids:
                FileTreeDA().delete_branch(node_id, bin_tree_id)
            main_tree = FileTreeDA().get_group_tree(group_id, "main")
            bin_tree = FileTreeDA().get_group_tree(group_id, "bin")
            resp.body = json.dumps({
                "main_tree": main_tree,
                "bin_tree": bin_tree,
                "success": True
            }, default_parser=json.parser)
        except FileStorageUploadError as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })
        except Exception as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })

    @staticmethod
    def on_put(req, resp, group_id):
        '''This is for moving nodes around'''
        (changes,) = request.get_json_or_form("changes", req=req)
        try:
            for change in changes:
                (node_id, isDir, member_file_id, parent_id,
                 name, isKeepOriginal, deleteId) = itemgetter("node_id", "isDir", "file_id", "parentId",
                                                              "name", "isKeepOriginal", "deleteId")(change)

                FileTreeDA().modify_branch(node_id, name, parent_id)
                main_tree = FileTreeDA().get_group_tree(group_id, "main")
                bin_tree = FileTreeDA().get_group_tree(group_id, "bin")
                resp.body = json.dumps({
                    "main_tree": main_tree,
                    "bin_tree": bin_tree,
                    "success": True
                }, default_parser=json.parser)

        except FileStorageUploadError as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })
        except Exception as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })


class GroupFileBin(object):

    def __init__(self):
        self.kafka_data = {
                           "PUT": {"event_type": settings.get('kafka.event_types.put.group_file_bin'),
                                   "topic": settings.get('kafka.topics.files')
                                   },
                           "DELETE": {"event_type": settings.get('kafka.event_types.delete.group_file_bin'),
                                      "topic": settings.get('kafka.topics.files')
                                      },
                           }
    @staticmethod
    def on_delete(req, resp, group_id):
        ''' Delete forever logic goes here, only available for Group Leader '''
        (node_ids,) = request.get_json_or_form(
            "node_ids_list", req=req)
        try:
            for node_id in node_ids:
                FileTreeDA().delete_branch_forever(node_id)

            main_tree = FileTreeDA().get_group_tree(group_id, "main")
            bin_tree = FileTreeDA().get_group_tree(group_id, "bin")
            resp.body = json.dumps({
                "main_tree": main_tree,
                "bin_tree": bin_tree,
                "success": True
            }, default_parser=json.parser)

        except FileStorageUploadError as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })
        except Exception as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })

    @staticmethod
    def on_put(req, resp, group_id):
        ''' Restore from Bin logic goes here '''
        (node_ids,) = request.get_json_or_form(
            "node_ids_list", req=req)
        try:
            main_tree_id = FileTreeDA().get_tree_id(group_id, "group", "main")

            for node_id in node_ids:
                FileTreeDA().restore_branch(node_id, main_tree_id)

            main_tree = FileTreeDA().get_group_tree(group_id, "main")
            bin_tree = FileTreeDA().get_group_tree(group_id, "bin")
            resp.body = json.dumps({
                "main_tree": main_tree,
                "bin_tree": bin_tree,
                "success": True
            }, default_parser=json.parser)

        except FileStorageUploadError as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })
        except Exception as e:
            resp.body = json.dumps({
                "message": e,
                "success": False
            })


class FileStorageDetail(object):

    def __init__(self):
        self.kafka_data = {
                           "GET": {"event_type": settings.get('kafka.event_types.get.file_storage_detail'),
                                   "topic": settings.get('kafka.topics.files')
                                   },
                           }

    @staticmethod
    def on_get(req, resp, file_id=None):
        member_id = req.get_param('memberId')
        member = MemberDA().get_member(member_id)
        if member:
            file_detail = FileStorageDA().get_file_detail(member, file_id)
            resp.body = json.dumps({
                "data": file_detail,
                "status": "success",
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "message": "Can not get file for un-exising member",
                "status": "warning",
                "success": False
            })


class DownloadStorageFile(object):

    def __init__(self):
        self.kafka_data = {"GET": {"event_type": settings.get('kafka.event_types.get.download_storage_file'),
                                   "topic": settings.get('kafka.topics.files')
                                   }
                           }

    @staticmethod
    def on_get(req, resp, file_id=None):
        item_key = FileStorageDA().store_file_to_static(file_id)
        if item_key:
            resp.body = json.dumps({
                "data": item_key,
                "message": "",
                "status": "Success",
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "message": "Something Went Wrong",
                "status": "warning",
                "success": False
            })


class ShareFile(object):

    @staticmethod
    def on_post(req, resp):
        (file_id_list, group_id, shared_member_id) = request.get_json_or_form(
            "file_id_list", "group_id", "shared_member_id", req=req)
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]
            shared_file_id_list = list()
            for file_id in file_id_list:
                file_share_params = {
                    "member_id": member_id,
                    "group_id": group_id,
                    "file_id": file_id,
                    "shared_member_id": shared_member_id
                }

                shared = ShareFileDA().sharing_file(**file_share_params)
                if shared:
                    shared_file_id_list.append(file_id)
            if shared_file_id_list:
                resp.body = json.dumps({
                    "data": shared_file_id_list,
                    "description": "File Shared successfully",
                    "success": True
                }, default_parser=json.parser)
            else:
                raise FileShareExists()
        except Exception as e:
            raise e

    @staticmethod
    def on_get(req, resp):
        req_type = req.get_param('type')
        session_id = get_session_cookie(req)
        session = validate_session(session_id)
        member_id = session["member_id"]
        member = MemberDA().get_member(member_id)
        if member:
            shared_files = list()
            if req_type == 'member':
                shared_files = ShareFileDA().get_shared_files(member)
            elif req_type == 'group':
                shared_files = ShareFileDA().get_group_files(member)
            resp.body = json.dumps({
                "data": shared_files,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "description": ("Can not get shared files "
                                "for un-existing member"),
                "success": False
            })

    @staticmethod
    def on_delete(req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]
            if member_id:
                (shared_key_list,) = request.get_json_or_form(
                    "shared_key_list", req=req)
                removed_key_list = list()
                for shared_key in shared_key_list:
                    removed_key = ShareFileDA().remove_sharing(shared_key)
                    if removed_key:
                        removed_key_list.append(removed_key)
                if removed_key_list:
                    resp.body = json.dumps({
                        "data": removed_key_list,
                        "description": "Shared file removed successfully!",
                        "success": True
                    }, default_parser=json.parser)
                else:
                    raise FileNotFound
        except Exception as e:
            raise e


class ShareFileDetail(object):
    @staticmethod
    def on_get(req, resp, shared_key=None):
        member_id = req.get_param('memberId')
        member = MemberDA().get_member(member_id)
        if member:
            shared_file_detail = ShareFileDA().get_shared_file_detail(member, shared_key)
            resp.body = json.dumps({
                "data": shared_file_detail,
                "success": True
            }, default_parser=json.parser)
        else:
            resp.body = json.dumps({
                "message": "Can not get shared files for un-exising member",
                "success": False
            })


class DownloadSharedFile(object):
    @staticmethod
    def on_get(req, resp, shared_key=None):
        file_id = ShareFileDA().get_shared_file_id(shared_key)
        if file_id:
            item_key = FileStorageDA().store_file_to_static(file_id)
            if item_key:
                resp.body = json.dumps({
                    "data": item_key,
                    "message": "File Downloaded successfully",
                    "status": "Success",
                    "success": True
                }, default_parser=json.parser)
            else:
                resp.body = json.dumps({
                    "message": "File does not exist",
                    "status": "warning",
                    "success": False
                })


class FileGroupResource(object):

    def __init__(self):
        self.kafka_data = {"GET": {"event_type": settings.get('kafka.event_types.get.file_group_resource'),
                                   "topic": settings.get('kafka.topics.files')
                                   },
                           }
    @staticmethod
    def on_get(req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

        group_list = ShareFileDA().get_group_list(member_id)
        resp.body = json.dumps({
            "data": group_list,
            "message": "All Group",
            "status": "success",
            "success": True
        }, default_parser=json.parser)
