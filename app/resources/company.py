import app.util.json as json
import logging
import falcon

import app.util.request as request
from app.util.auth import check_session, check_session_administrator
from app.da.file_sharing import FileStorageDA

from app.da.company import CompanyDA

logger = logging.getLogger(__name__)


class CompanyResource(object):

    @check_session_administrator
    def on_post(self, req, resp):
        (name, place_id, address_1, address_2, city,
         state, postal, country_code_id,
         main_phone, primary_url, logo) = request.get_json_or_form(
            "name", "place_id", "address_1", "address_2", 
            "city", "state", "postal", "country_code_id",
            "main_phone", "primary_url", "logo", req=req)

        try:

            logo_storage_id = None
            if logo is not None:
                logo_storage_id = FileStorageDA().put_file_to_storage(logo)
            
            name = None if not name else name
            place_id = None if not place_id else place_id
            address_1 = None if not address_1 else address_1
            address_2 = None if not address_2 else address_2
            city = None if not city else city
            state = None if not state else state
            postal = None if postal == 'null' else postal
            country_code_id = None if country_code_id == 'null' else country_code_id
            main_phone = None if not main_phone else main_phone
            primary_url = None if not primary_url else primary_url

            company_id = CompanyDA().create_company(name, place_id, address_1, address_2, city, state, postal, country_code_id, main_phone, primary_url, logo_storage_id)

            company = CompanyDA.get_company(company_id)
            resp.body = json.dumps({
                "data": company,
                "description": "Company created successfully",
                "success": True
            }, default_parser=json.parser)
        except Exception:

            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    def on_get(self, req, resp):
        member_id = req.get_param_as_int('member_id')
        sort_params = req.get_param('sort')
        page_size = req.get_param_as_int('page_size')
        page_number = req.get_param_as_int('page_number')

        data = CompanyDA.get_companies(member_id, sort_params, page_size, page_number)
        resp.body = json.dumps({
            "data": data,
            "description": "load successfully",
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

    @check_session_administrator
    def on_delete(self, req, resp):
        (company_ids) = request.get_json_or_form("companyIds", req=req)
        # company_ids = company_ids[0].split(',')

        res = CompanyDA.delete_companies(company_ids[0])
        resp.body = json.dumps({
            "data": res,
            "description": "Group's deleted successfully!",
            "success": True
        }, default_parser=json.parser)

    @check_session_administrator
    def on_put_detail(self, req, resp, company_id=None):
        (name, place_id, address_1, address_2, city,
         state, postal, country_code_id,
         main_phone, primary_url, logo) = request.get_json_or_form(
          "name", "place_id", "address_1", "address_2",
          "city", "state", "postal", "country_code_id",
          "main_phone", "primary_url", "logo", req=req)

        try:

            company = CompanyDA.get_company(company_id)

            logo_storage_id = company["logo_storage_id"]

            if logo is not None:
                logo_storage_id = FileStorageDA().put_file_to_storage(logo)

            name = None if not name else name
            place_id = None if not place_id else place_id
            address_1 = None if not address_1 else address_1
            address_2 = None if not address_2 else address_2
            city = None if not city else city
            state = None if not state else state
            postal = None if postal == 'null' else postal
            country_code_id = None if country_code_id == 'null' else country_code_id
            main_phone = None if not main_phone else main_phone
            primary_url = None if not primary_url else primary_url

            CompanyDA().update_company(company_id, name, place_id, address_1, address_2, city, state, postal, country_code_id, main_phone, primary_url, logo_storage_id)
            company = CompanyDA.get_company(company_id)
            resp.body = json.dumps({
                "data": company,
                "description": "Company updated successfully",
                "success": True
            }, default_parser=json.parser)

        except Exception:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    @check_session_administrator
    def on_post_member(self, req, resp):
        (company_id, member_id, company_role) = request.get_json_or_form(
            "company_id", "member_id", "company_role", req=req)

        try:

            CompanyDA.add_member(company_id, member_id, company_role)
            company = CompanyDA.get_company(company_id)

            resp.body = json.dumps({
                "data": company,
                "description": "Company updated successfully",
                "success": True
            }, default_parser=json.parser)

        except Exception:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    @check_session_administrator
    def on_delete_member(self, req, resp):
        (company_id, member_id) = request.get_json_or_form(
            "company_id", "member_id", req=req)

        try:

            CompanyDA.delete_member(company_id, member_id)
            company = CompanyDA.get_company(company_id)
            resp.body = json.dumps({
                "data": company,
                "description": "Company updated successfully",
                "success": True
            }, default_parser=json.parser)

        except Exception:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)


class CompanyUnregisteredResource(object):

    def on_get(self, req, resp):
        sort_params = req.get_param('sort')
        page_size = req.get_param_as_int('page_size')
        page_number = req.get_param_as_int('page_number')

        try:
            data = CompanyDA.get_unregistered_company(sort_params, page_size, page_number)

            resp.body = json.dumps({
                "data": data,
                "description": "load successfully",
                "success": True
            }, default_parser=json.parser)

        except Exception:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    @check_session_administrator
    def on_post(self, req, resp):

        try:
            (company_name, ) = request.get_json_or_form(
                "company_name", req=req)
            company = CompanyDA.create_company_from_name(company_name)
            resp.body = json.dumps({
                "data": company,
                "description": "New company created successfully",
                "success": True
            }, default_parser=json.parser)

        except Exception:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    @check_session_administrator
    def on_put(self, req, resp):
        try:
            (company_name, new_company_name) = request.get_json_or_form(
                "company_name", "new_company_name", req=req)
            CompanyDA.update_unregistered_company(
                company_name, new_company_name)
            resp.body = json.dumps({
                "description": "update company name successfully",
                "success": True
            }, default_parser=json.parser)

        except Exception:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)

    @check_session_administrator
    def on_delete(self, req, resp):
        try:
            (company_name, ) = request.get_json_or_form(
                "company_name", req=req)
            CompanyDA.delete_unregistered_company(company_name)
            resp.body = json.dumps({
                "description": "delete company name successfully",
                "success": True
            }, default_parser=json.parser)

        except Exception:
            resp.body = json.dumps({
                "description": "Something went wrong",
                "success": False
            }, default_parser=json.parser)
