
import os
import requests
from requests.exceptions import HTTPError
import argparse
import pprint
import json
import time
from datetime import datetime
import re
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.twofactor.totp import TOTP
from cryptography.hazmat.primitives.hashes import SHA1

pp = pprint.PrettyPrinter(indent=4, compact=False)
"""
https://matrix.bf.sl.attcompute.com/apps/amerashare-sandbox

curl https://api.att.com/oauth/v4/token --request POST --insecure \
--data "client_id=zzvvi0ykvyxkibgst6qbtfzgoxuj89ta\
&client_secret=cyn0dnhom6ms9jxkijlwqgty8qskggik\
&grant_type=client_credentials\
&scope=SMS"
"""
sandbox_client_id = 'zzvvi0ykvyxkibgst6qbtfzgoxuj89ta'
sandbox_client_secret = 'cyn0dnhom6ms9jxkijlwqgty8qskggik'
sandbox_short_code = '29156039'
sandbox_merchant_id='5271449e-6ba8-4c7c-97e7-0e413f8d6fe7'


class Attapi:
    def __init__(self, client_id=sandbox_client_id, client_secret=sandbox_client_secret, 
      short_code=sandbox_short_code, oath_access_token=None, raise_on_err=False):
        self.client_id = client_id
        self.client_secret = client_secret
        self.oath_access_token = oath_access_token
        self.short_code = short_code
        self.raise_on_err = raise_on_err

    def get_att_token(self):

      data = {
        'client_id': self.client_id,
        'client_secret': self.client_secret,
        'grant_type': 'client_credentials',
        'scope': 'SMS'
      }

      try:
          resp = requests.post('https://api.att.com/oauth/v4/token', data=data, verify=False)
          resp.raise_for_status()
          response  = resp.json()

          self.oath_access_token = response["access_token"] 
          print(f'oath_access_token: {self.oath_access_token}')
      except HTTPError as http_err:
        if self.raise_on_err:
            raise http_err
        else:
          print(f'HTTP error occurred: {http_err}')  # >= Python 3.6
      finally:
          return self.oath_access_token

    """
    curl "https://api.att.com/sms/v3/messaging/outbox" \
    --header "Content-Type: application/json" \
    --header "Accept: application/json" \
    --header "Authorization: Bearer BF-ACSI~4~20200827201750~RbCoXiYJpWqfuvB3Bu0TpbFLZkLz0T2N" \
    --data "{\"outboundSMSRequest\":{\"address\":\"tel:+19728049122\",\"message\":\"yeah msg\"}}" \
    --request POST
    """
    def sendsms(self, phone, msg):
      if self.oath_access_token == None:
        self.get_att_token()

      phone = re.sub('\D', '', phone) #ATT only wants digits
      data = "{\"outboundSMSRequest\":{\"address\":\"tel:+1" + \
              phone + \
              "\",\"message\":\"" + msg + "\"}}"

      print(f'data: {data}')
      headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {self.oath_access_token}',
      }

      try:
          return requests.post('https://api.att.com/sms/v3/messaging/outbox', headers=headers, data=data)
      except HTTPError as http_err:
        if self.raise_on_err:
            raise http_err
        else:
          print(f'HTTP error occurred: {http_err}')  # >= Python 3.6
          return False
      else:
          return True

    """

    # Step 1:
    # Authentication parameter. For directions directions on how to obtain the OAuth access
    # token, see the OAuth section.BF
    OAUTH_ACCESS_TOKEN="BF-ACSI~4~20200827201750~RbCoXiYJpWqfuvB3Bu0TpbFLZkLz0T2N"
    # Step 2:
    # Fully qualified domain name for the API Gateway.
    FQDN="https://api.att.com"
    # Enter the registration identifier used to get an SMS message.
    REGISTRATION_ID="29156039"
    # Send the Get SMS method request to the API Gateway.

    curl "${FQDN}/sms/v3/messaging/inbox/${REGISTRATION_ID}" \
    --header "Authorization: Bearer ${OAUTH_ACCESS_TOKEN}" \
    --header "Accept: application/json" \
    --request GET

    curl "https://api.att.com/sms/v3/messaging/inbox/29156039" \
    --header "Authorization: Bearer BF-ACSI~4~20200827220550~RWszbkC1XeZfRirVdppEM1rBot1fmjzZ" \
    --header "Accept: application/json" \
    --request GET

    """
    def getsms_messages(self):

      try:
          response = requests.get(
              f'api.att.com/sms/v3/messaging/inbox/{self.short_code}', 
              headers={'Accept':'application/json',
                      'Authorization': f'Bearer {self.oath_access_token}'})
          return response
      except HTTPError as http_err:
        if self.raise_on_err:
            raise http_err
        else:
          print(f'HTTP error occurred: {http_err}')  # >= Python 3.6
          return False
      else:
          return True

    def generate_totp(self, timeout=30):
        key = os.urandom(20)
        self.totp = TOTP(key, 8, SHA1(), timeout, backend=default_backend())

        self.totpcode = self.totp.generate(time.time()).decode('utf8')
        return self.totpcode

    def verify_totp(self, usertotp):
        success = True
        try:
            # this will fail if user does not acknowledge in time
            self.totp.verify(usertotp.encode('utf8'), time.time())

        except:
            success = False
        finally:
            return success





if __name__ == "__main__":
    prompt = """Amera Registration
    Please enter the one time code below to complete
    your registartion
    """

    parser = argparse.ArgumentParser(description='ATT API for SMS')
    parser.add_argument(
        '--phone', default='(972) 804-9122', type=str,
        dest='phone',
        help='phone number for SMS text')

    parser.add_argument(
        '--msg', default=False, type=bool,
        dest='msg',
        help=f'Call me sometime {datetime.now().strftime("%m/%d/%Y, %H:%M:%S")}')
    
    args = parser.parse_args()

    try:
      attapi = Attapi() #for now, we take all of the sandbox ID and auth 
      totpvalue = attapi.generate_totp()
      #attapi.sendsms(phone=args.phone, msg=f'{prompt} {totpvalue}')
      attapi.sendsms(phone=args.phone, msg=f'code to enter: {totpvalue}')

      print(f'hint: you should see on your phone {totpvalue}')
      usertotp = input("Please enter one time password:\n")  

      totp_ok = attapi.verify_totp(usertotp)
      if totp_ok == True:
          print('congrats you are in')
      else:
          print('the code was incorrect or expired')


    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')  # >= Python 3.6
