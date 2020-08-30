import mimetypes

import logging
import app.util.json as json
import app.util.request as request
from app.da.member import MemberDA
from app.da.file_sharing import FileStorageDA, ShareFileDA
from app.util.session import get_session_cookie, validate_session
from app.exceptions.file_sharing import FileShareExists, FileNotFound, \
    FileUploadCreateException, FileStorageUploadError

logger = logging.getLogger(__name__)


class FileStorage(object):
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
                iv = req.get_param(f'file{index}.iv')

                file_id = FileStorageDA().store_file_to_storage(file)
                status = 'available'

                logger.debug(f'FILE STORAGE IDENTIFIER: {file_id}')

                res = FileStorageDA().create_member_file_entry(
                    file_id=file_id,
                    file_name=file_name,
                    member_id=member_id,
                    status=status,
                    file_size_bytes=file_size_bytes,
                    iv=iv
                )
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
                logger.debug(
                    f"Will attempt to rename file with Id {file_id} to {new_file_name}")
                rename_success = FileStorageDA().rename_file(member, file_id, new_file_name)
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
        (file_id_list, ) = request.get_json_or_form("file_id_list", req=req)
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


class FileStorageDetail(object):
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
        (file_id_list, group_id, shared_member_id) = request.get_json_or_form("file_id_list", "group_id",
                                                                              "shared_member_id", req=req)
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
                "description": "Can not get shared files for un-existing member",
                "success": False
            })

    @staticmethod
    def on_delete(req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
            member_id = session["member_id"]
            if member_id:
                (shared_key_list, ) = request.get_json_or_form(
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
