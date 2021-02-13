import uuid
import app.util.json as json
import logging
from pprint import pformat
from datetime import datetime
from dateutil.relativedelta import relativedelta
from urllib.parse import urljoin

import app.util.request as request
from app.util.session import get_session_cookie, validate_session
from app.config import settings
from app.da.file_sharing import FileStorageDA

from app.da.company import CompanyDA
from app.exceptions.session import ForbiddenSession
from app.exceptions.session import InvalidSessionError, UnauthorizedSession

logger = logging.getLogger(__name__)

class CompanyResource(object):

    def on_post(self, req, resp):
        (name, address_1, address_2, city, country_code_id, main_phone, primary_url, logo) = request.get_json_or_form(
            "name", "address_1", "address_2", "city", "country_code_id", "main_phone", "primary_url", "logo", req=req)

        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

        try:
        
            logo_storage_id = None
            if logo is not None:
                logo_storage_id = FileStorageDA().put_file_to_storage(logo)
            
            name = None if name == 'null' else name
            address_1 = None if address_1 == 'null' else address_1
            address_2 = None if address_2 == 'null' else address_2
            city = None if city == 'null' else city
            country_code_id = None if country_code_id == 'null' else country_code_id
            main_phone = None if main_phone == 'null' else main_phone
            primary_url = None if primary_url == 'null' else primary_url

            company_id = CompanyDA().create_company(name, address_1, address_2, city, country_code_id, main_phone, primary_url, logo_storage_id)

            company = CompanyDA.get_company(company_id)
            resp.body = json.dumps({
                "data": company,
                "description": "Company created successfully",
                "success": True
            }, default_parser=json.parser)

        except Exception as e:

            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)
    
    @staticmethod
    def on_get(req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)

        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

        companies = CompanyDA.get_all_companies()
        resp.body = json.dumps({
            "data": companies,
            "success": True
        }, default_parser=json.parser)
    
    def on_get_detail(self, req, resp, company_id=None):
        company = CompanyDA.get_company(company_id)
        resp.body = json.dumps({
            "data": company,
            "message": "Company Detail",
            "status": "success",
            "success": True
        }, default_parser=json.parser)

    def on_delete(self, req, resp):
        (company_ids) = request.get_json_or_form("companyIds", req=req)
        # company_ids = company_ids[0].split(',')

        res = CompanyDA.delete_companies(company_ids[0])
        resp.body = json.dumps({
            "data": res,
            "description": "Group's deleted successfully!",
            "success": True
        }, default_parser=json.parser)

    def on_put_detail(self, req, resp, company_id=None):
      (name, address_1, address_2, city, country_code_id, main_phone, primary_url, logo) = request.get_json_or_form(
          "name", "address_1", "address_2", "city", "country_code_id", "main_phone", "primary_url", "logo", req=req)

      try:
          session_id = get_session_cookie(req)
          session = validate_session(session_id)
      except InvalidSessionError as err:
          raise UnauthorizedSession() from err

      try:

            company = CompanyDA.get_company(company_id)

            logo_storage_id = company["logo_storage_id"]

            if logo is not None:
                logo_storage_id = FileStorageDA().put_file_to_storage(logo)

            name = None if name == 'null' else name
            address_1 = None if address_1 == 'null' else address_1
            address_2 = None if address_2 == 'null' else address_2
            city = None if city == 'null' else city
            country_code_id = None if country_code_id == 'null' else country_code_id
            main_phone = None if main_phone == 'null' else main_phone
            primary_url = None if primary_url == 'null' else primary_url

            CompanyDA().update_company(company_id, name, address_1, address_2, city, country_code_id, main_phone, primary_url, logo_storage_id)
            company = CompanyDA.get_company(company_id)
            resp.body = json.dumps({
                "data": company,
                "description": "Company updated successfully",
                "success": True
            }, default_parser=json.parser)

      except Exception as e:
          resp.body = json.dumps({
              "description": "Something went wrong",
              "success": False
          }, default_parser=json.parser)
    
    def on_post_member(self, req, resp):
        (company_id, member_id, company_role ) = request.get_json_or_form(
            "company_id", "member_id", "company_role", req=req)

        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

        try:

                CompanyDA.add_member(company_id, member_id, company_role)
                company = CompanyDA.get_company(company_id)

                resp.body = json.dumps({
                    "data": company,
                    "description": "Company updated successfully",
                    "success": True
                }, default_parser=json.parser)

        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    def on_delete_member(self, req, resp):
      (company_id, member_id ) = request.get_json_or_form(
          "company_id", "member_id", req=req)

      try:
          session_id = get_session_cookie(req)
          session = validate_session(session_id)
      except InvalidSessionError as err:
          raise UnauthorizedSession() from err

      try:

            CompanyDA.delete_member(company_id, member_id)
            company = CompanyDA.get_company(company_id)
            resp.body = json.dumps({
                "data": company,
                "description": "Company updated successfully",
                "success": True
            }, default_parser=json.parser)

      except Exception as e:
          resp.body = json.dumps({
              "description": "Something went wrong",
              "success": False
          }, default_parser=json.parser)

class CompanyUnregisteredResource(object):

    def on_get(self, req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

        try:
                companies = CompanyDA.get_unregistered_company()

                resp.body = json.dumps({
                    "data": companies,
                    "description": "load successfully",
                    "success": True
                }, default_parser=json.parser)

        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    def on_post(self, req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

        try:
            (company_name, ) = request.get_json_or_form("company_name", req=req)
            company = CompanyDA.create_company_from_name(company_name)
            resp.body = json.dumps({
                "data": company,
                "description": "create a new company successfully",
                "success": True
            }, default_parser=json.parser)

        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    def on_put(self, req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

        try:
            (company_name, new_company_name ) = request.get_json_or_form("company_name", "new_company_name", req=req)
            CompanyDA.update_unregistered_company(company_name, new_company_name)
            resp.body = json.dumps({
                "description": "update company name successfully",
                "success": True
            }, default_parser=json.parser)

        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    def on_delete(self, req, resp):
        try:
            session_id = get_session_cookie(req)
            session = validate_session(session_id)
        except InvalidSessionError as err:
            raise UnauthorizedSession() from err

        try:
            (company_name, ) = request.get_json_or_form("company_name", req=req)
            CompanyDA.delete_unregistered_company(company_name)
            resp.body = json.dumps({
                "description": "delete company name successfully",
                "success": True
            }, default_parser=json.parser)

        except Exception as e:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

