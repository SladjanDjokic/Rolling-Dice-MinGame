import logging
import falcon
import app.util.json as json

import app.util.request as request
from datetime import datetime
from app.da.member import MemberDA
from app.exceptions.member import ForgotDataNotFound, ForgotKeyExpired
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class MemberResetPasswordResource(object):

    def on_post(self, req, resp, forgot_key):
        logger.debug('{}'.format(forgot_key))
        forgot_key = forgot_key.hex
        (password) = request.get_json_or_form("password", req=req)
        password = password[0]
        if not password:
            raise falcon.HTTPError("400",
                                    title="Invalid Password",
                                    description="Please Provide Password.")
        
        data = MemberDA.get_password_reset_info_by_forgot_key(forgot_key)

        utc_expiration = data["expiration"].replace(tzinfo=None)
        utc_now = datetime.utcnow()

        if utc_now > utc_expiration:
            raise falcon.HTTPGone("410",
                                title= "forgot_key expired.",
                                description= "")
        if data:
            try:
                id = data['id']
                member_id = data['member_id']
                MemberDA.update_member_password(member_id=member_id, password=password)
                #expire forgot_key by setting current time (need to look further)
                # MemberDA.expire_reset_password_key(
                #     expiration=utc_now,
                #     forgot_key=forgot_key
                # )
                MemberDA.delete_reset_password_info(id=id)
            except Exception as e:
                    resp.body = json.dumps({
                        "message": e,
                        "success": False
                    })             

        resp.body = json.dumps({
                "success": True
            })
    
    
    def on_get(self, req, resp, forgot_key):
        if not forgot_key:
            raise falcon.HTTPError("400",
                                    title="Invalid forgot_key",
                                    description="Please Provide forgot_key.")

        # We store the key in hex format in the database
        forgot_key = forgot_key.hex

        logger.debug("Forgot Key: {}".format(forgot_key))

        data = MemberDA.get_password_reset_info_by_forgot_key(forgot_key)

        logger.debug("forgot data: {}".format(data))

        if not data:
            raise ForgotDataNotFound(forgot_key)

        utc_expiration = data["expiration"].replace(tzinfo=None)
        utc_now = datetime.utcnow()

        if utc_now > utc_expiration:
            raise ForgotKeyExpired(forgot_key)

        resp.body = json.dumps(data, default_parser=str)