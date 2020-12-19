import logging

from app.da.file_sharing import FileStorageDA
from app.da.mail import DraftMailDA, InboxMailDa, StarMailDa, TrashMailDa, ArchiveMailDa, MailSettingsDA, SentMailDA
from app.util import request, json
from app.util.auth import inject_member
from app.exceptions.data import HTTPBadRequest
# from app.util.email import send_text_email_with_content_type
from app.util.validators import validate_mail, receiver_dict_validator

logger = logging.getLogger(__name__)


class MailAttachmentResource(object):

    @inject_member
    def on_post(self, req, response, member):
        (mail_id, file) = request.get_json_or_form("mail_id", "file", req=req)

        if not mail_id:
            raise HTTPBadRequest("Email is not specified")

        file_storage_id = FileStorageDA().store_file_to_storage(file)
        filename, filetype = DraftMailDA.save_file_for_mail(file_storage_id, file, mail_id, member["member_id"])
        response.body = json.dumps({
            "file_name": str(filename),
            "file_type": str(filetype),
            "file_id": str(file_storage_id)
        })

    @inject_member
    def on_delete_attachment(self, req, response, member, mail_id, attachment_id):
        file_id = DraftMailDA.delete_file_for_mail(attachment_id, mail_id, member["member_id"])
        response.body = json.dumps({
            "file_id": file_id
        })


class MailBaseResource(object):

    @property
    def main_da_class(self):
        raise NotImplemented

    @inject_member
    def on_get_list(self, req, response, member):
        start = req.params.get('start', -1)
        try:
            start = int(start)
        except ValueError:
            raise HTTPBadRequest("Start is not valid")
        size = req.params.get('size', 20)
        try:
            size = int(size)
        except ValueError:
            raise HTTPBadRequest("Size of list is not valid")
        search = req.params.get('se', None)
        sort = req.params.get('sr', None)
        order = req.params.get('or', 1)
        try:
            order = int(order)
        except ValueError:
            raise HTTPBadRequest("Only number is acceptable for order")
        if order not in (-1, 1):
            raise HTTPBadRequest("Order is not valid number. order can be -1 or 1")
        data, total = self.main_da_class.list_folder(member["member_id"], start, size,
                                                     ("%" + str(search) + "%") if search else None, sort, order)
        response.body = json.dumps({
            "total": total,
            "data": data
        })

    @inject_member
    def on_get_detail(self, req, response, member, mail_id):
        if not mail_id:
            raise HTTPBadRequest("Email is not specified")
        return_data = self.main_da_class.get_mail_detail(mail_id, member["member_id"])
        response.body = json.dumps(return_data)

    @inject_member
    def on_post_forward(self, req, response, member):
        (receiver, mail_id, bcc, cc) = request.get_json_or_form(
            "receivers", "mail_id", "bcc", "cc", req=req)
        if not mail_id:
            raise HTTPBadRequest("Email is not specified")
        if receiver and not (type(receiver) == dict and ("amera" in receiver and "external" in receiver)):
            raise HTTPBadRequest("Receiver is not a valid object")

        if receiver:
            if "external" in receiver:
                receiver_mail_list = []
                for eachMail in receiver["external"]:
                    validated_mail = validate_mail(eachMail)
                    if validated_mail:
                        receiver_mail_list.append(validated_mail)
                receiver["external"] = receiver_mail_list
        else:
            receiver = {
                "amera": [],
                "external": []
            }
        receiver = receiver_dict_validator(receiver)
        if cc:
            cc = receiver_dict_validator(cc, False)
        if bcc:
            bcc = receiver_dict_validator(bcc, False)

        return_data = self.main_da_class.forward_mail(member["member_id"], mail_id, receiver, cc, bcc)
        response.body = json.dumps(return_data)


class MailDraftComposeResource(MailBaseResource):
    main_da_class = DraftMailDA

    @inject_member
    def on_post(self, req, response, member):
        (subject, body, receiver, bcc, cc, mail_id, reply_id) = request.get_json_or_form(
            "subject", "body", "receivers", "bcc", "cc", "mail_id", "reply_id", req=req)

        if receiver and not (type(receiver) == dict and ("amera" in receiver and "external" in receiver)):
            raise HTTPBadRequest("Receiver is not a valid object")

        if receiver:
            receiver_mail_list = []
            for eachMail in receiver["external"]:
                validated_mail = validate_mail(eachMail)
                if validated_mail:
                    receiver_mail_list.append(validated_mail)
            receiver["external"] = receiver_mail_list
        else:
            receiver = {
                "amera": [],
                "external": []
            }
        draft_id = DraftMailDA.cu_draft_mail_for_member(
            member,
            subject,
            body,
            receiver,
            update=False if not mail_id else True,
            mail_header_id=mail_id,
            reply_id=reply_id,
            cc=cc,
            bcc=bcc
        )

        response.body = json.dumps({
            "draft_id": str(draft_id)
        })

    @inject_member
    def on_post_send(self, req, response, member):
        self.on_post(req, response)
        (mail_id,) = request.get_json_or_form(
            "mail_id", req=req)

        if not mail_id:
            raise HTTPBadRequest("Email is not specified")

        failed_receivers = DraftMailDA.process_send_mail(mail_id, member["member_id"], )

        response.body = json.dumps({
            "fails": failed_receivers
        })
        #         for eachRecive in receiver_mail_list:
        #             send_text_email_with_content_type()
        # send_text_email_with_content_type()

    @inject_member
    def on_delete_draft(self, req, response, member, mail_id):
        if not mail_id:
            raise HTTPBadRequest("Email is not specified")
        DraftMailDA.delete_draft_mail(mail_id, member["member_id"])
        response.body = json.dumps({
            "id": mail_id
        })


class MailInboxResource(MailBaseResource):
    main_da_class = InboxMailDa


class MailStaredResource(MailBaseResource):
    main_da_class = StarMailDa

    @inject_member
    def on_post(self, req, res, member):

        (mail_id, rm) = request.get_json_or_form(
            "mail_id", "rm", req=req)

        if not mail_id:
            raise HTTPBadRequest("Email is not specified")

        if not rm:
            rm = False
        else:
            try:
                rm = bool(rm)
            except ValueError:
                raise HTTPBadRequest("Only boolean is allowed for 'rm'")
        self.main_da_class.add_remove_mail_to_star(mail_id, member["member_id"], not rm)


class MailTrashResource(MailBaseResource):
    main_da_class = TrashMailDa

    @inject_member
    def on_post(self, req, res, member):

        (mail_id,) = request.get_json_or_form(
            "mail_id", req=req)

        if not mail_id:
            raise HTTPBadRequest("Email is not specified")

        self.main_da_class.add_to_trash(mail_id, member["member_id"])

    @inject_member
    def on_delete_detail(self, req, response, member, mail_id):
        if not mail_id:
            raise HTTPBadRequest("Email is not specified")
        self.main_da_class.delete_mail(mail_id, member["member_id"])

    @inject_member
    def on_post_remove(self, req, response, member):
        (mail_id,) = request.get_json_or_form(
            "mail_id", req=req)
        self.main_da_class.remove_from_trash(mail_id, member["member_id"])

    @inject_member
    def on_post_archive(self, req, response, member):
        (mail_id,) = request.get_json_or_form(
            "mail_id", req=req)
        self.main_da_class.add_to_archive(mail_id, member["member_id"])


class MailArchiveResource(MailBaseResource):
    main_da_class = ArchiveMailDa

    @inject_member
    def on_post(self, req, res, member):

        (mail_id,) = request.get_json_or_form(
            "mail_id", req=req)

        if not mail_id:
            raise HTTPBadRequest("Email is not specified")

        self.main_da_class.add_to_archive(mail_id, member["member_id"])

    @inject_member
    def on_delete_detail(self, req, response, member, mail_id):
        if not mail_id:
            raise HTTPBadRequest("Email is not specified")
        self.main_da_class.delete_mail(mail_id, member["member_id"])

    @inject_member
    def on_post_remove(self, req, response, member):
        (mail_id,) = request.get_json_or_form(
            "mail_id", req=req)
        self.main_da_class.remove_from_archive(mail_id, member["member_id"])

    @inject_member
    def on_post_trash(self, req, response, member):
        (mail_id,) = request.get_json_or_form(
            "mail_id", req=req)
        self.main_da_class.add_to_trash(mail_id, member["member_id"])


class MailSentResource(MailBaseResource):
    main_da_class = SentMailDA


class MailSettingsResource(object):

    @inject_member
    def on_get(self, req, response, member):
        response.body = json.dumps(MailSettingsDA.settings_get(member["member_id"]))

    @inject_member
    def on_post(self, req, response, member):
        (default_style, grammar, spelling, autocorrect) = request.get_json_or_form(
            "default_style", "grammar", "spelling", "autocorrect", req=req)

        # if not default_style or not grammar or not spelling or not autocorrect:
        if not default_style:
            default_style = "{}"
        if grammar is None or spelling is None or autocorrect is None:
            raise HTTPBadRequest("Invalid data")
        MailSettingsDA.settings_cu(member["member_id"], default_style, grammar, spelling, autocorrect)
        response.body = json.dumps({})

    @inject_member
    def on_post_sign(self, req, response, member):
        (sign_id, name, content) = request.get_json_or_form(
            "id", "name", "content", req=req)
        if not content or not name:
            raise HTTPBadRequest("content and name are required")
        sign = MailSettingsDA.cu_setting_signature(member["member_id"], name, content,
                                                   sign_id if sign_id else None, True if sign_id else False)
        response.body = json.dumps({
            "sign_id": sign
        })

    @inject_member
    def on_delete_sign(self, req, response, member):
        (sign_id,) = request.get_json_or_form(
            "sign_id", req=req)
        if not sign_id:
            raise HTTPBadRequest("signature id is not specified")
        sign = MailSettingsDA.setting_signature_delete(member["member_id"], sign_id)
        response.body = json.dumps({
            "sign_id": sign
        })

    @inject_member
    def on_get_list(self, req, response, member):
        data = MailSettingsDA.setting_signature_list(member["member_id"])
        response.body = json.dumps(data)
