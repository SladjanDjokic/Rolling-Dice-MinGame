import app.util.json as json
import logging
import falcon

import app.util.request as request
from app.util.auth import check_session, check_session_administrator
from app.da.file_sharing import FileStorageDA
from app.da.location import LocationDA

from app.da.company import CompanyDA
from app.exceptions.company import NotEnoughCompanyPrivileges

logger = logging.getLogger(__name__)


class CompanyResource(object):

    def _check_company_update_privileges(self, req, member_role):
        if req.context.auth['session']['user_type'] != 'administrator' \
           and (not member_role or member_role not in ['owner', 'administrator']):
            raise NotEnoughCompanyPrivileges

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
            country_code_id = 840 if country_code_id == 'null' else country_code_id
            main_phone = None if not main_phone else main_phone
            primary_url = None if not primary_url else primary_url

            location_id = LocationDA.insert_location(
                country_code_id=country_code_id)
            company_id = CompanyDA().create_company(name=name, country_code_id=country_code_id,
                                                    main_phone=main_phone, primary_url=primary_url, logo_storage_id=logo_storage_id, location_id=location_id)

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

        data = CompanyDA.get_companies(
            member_id, sort_params, page_size, page_number)
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

    @check_session
    def on_post_picture(self, req, resp, company_id):
        member_id = req.context.auth['session']['member_id']
        try:
            (file, size, mime) = request.get_json_or_form(
                "file", "size", "mime", req=req)

            member_role = CompanyDA.get_member_role(member_id, company_id)
            self._check_company_update_privileges(req, member_role)

            picture_storage_id = None
            picture_storage_id = FileStorageDA().put_file_to_storage(
                file=file, file_size_bytes=size, mime_type=mime)

            CompanyDA.update_company_picture(
                company_id, picture_storage_id)

            company = CompanyDA.get_company(company_id)

            if company:
                resp.body = json.dumps({
                    "description": "Picture updated successfully",
                    "data": company,
                    "success": True
                }, default_parser=json.parser)
            else:
                resp.body = json.dumps({
                    "description": "Something went wrong when updating picture",
                    "success": False
                }, default_parser=json.parser)

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_post_details_update(self, req, resp, company_id):
        member_id = req.context.auth['session']['member_id']
        try:
            (name, industries, email, primary_url, main_phone, country_code_id, place_id, street_address_1, street_address_2, locality, sub_locality, admin_area_1, admin_area_2, postal_code, map_link, latitude, longitude, map_vendor, vendor_formatted_address, raw_response, location_id) = request.get_json_or_form(
                "name", "industries", "email", "primaryUrl", "phone", "countryCode", "placeId", "streetAddress1", "streetAddress2", "locality", "sublocality", "adminArea1", "adminArea2", "postal", "map_link", "latitude", "longitude", "map_vendor", "vendor_formatted_address", "raw_response", "location_id", req=req)

            member_role = CompanyDA.get_member_role(member_id, company_id)
            self._check_company_update_privileges(req, member_role)

            company_data = CompanyDA().get_company(company_id)
            if company_data["location_id"] == location_id:
                # Change location data keeping the id if valid location
                location_id = LocationDA().update_location(location_id=location_id, country_code_id=country_code_id,
                                                           admin_area_1=json.convert_null(
                                                               admin_area_1),
                                                           admin_area_2=json.convert_null(
                                                               admin_area_2),
                                                           locality=json.convert_null(
                                                               locality),
                                                           sub_locality=json.convert_null(
                                                               sub_locality),
                                                           street_address_1=json.convert_null(
                                                               street_address_1),
                                                           street_address_2=json.convert_null(
                                                               street_address_2),
                                                           postal_code=json.convert_null(
                                                               postal_code),
                                                           latitude=json.convert_null(
                                                               latitude),
                                                           longitude=json.convert_null(
                                                               longitude),
                                                           map_vendor=json.convert_null(
                                                               map_vendor),
                                                           map_link=json.convert_null(
                                                               map_link),
                                                           place_id=json.convert_null(
                                                               place_id),
                                                           vendor_formatted_address=json.convert_null(
                                                               vendor_formatted_address),
                                                           raw_response=json.dumps(
                                                               raw_response),
                                                           location_profile_picture_id=None)
            else:
                location_id = LocationDA().insert_location(country_code_id=country_code_id,
                                                           admin_area_1=json.convert_null(
                                                               admin_area_1),
                                                           admin_area_2=json.convert_null(
                                                               admin_area_2),
                                                           locality=json.convert_null(
                                                               locality),
                                                           sub_locality=json.convert_null(
                                                               sub_locality),
                                                           street_address_1=json.convert_null(
                                                               street_address_1),
                                                           street_address_2=json.convert_null(
                                                               street_address_2),
                                                           postal_code=json.convert_null(
                                                               postal_code),
                                                           latitude=json.convert_null(
                                                               latitude),
                                                           longitude=json.convert_null(
                                                               longitude),
                                                           map_vendor=json.convert_null(
                                                               map_vendor),
                                                           map_link=json.convert_null(
                                                               map_link),
                                                           place_id=json.convert_null(
                                                               place_id),
                                                           vendor_formatted_address=json.convert_null(
                                                               vendor_formatted_address),
                                                           raw_response=json.dumps(
                                                               raw_response),
                                                           location_profile_picture_id=None)

            company_params = {"company_id": company_id,
                              "name": name,
                              "email": json.convert_null(email),
                              "primary_url": json.convert_null(primary_url),
                              "main_phone": json.convert_null(main_phone),
                              "location_id": location_id,
                              "country_code_id": country_code_id,
                              }
            CompanyDA.update_company_details(company_params)

            # Industries
            posted_industries = []
            if json.convert_null(industries):
                posted_industries = industries
            listed_industries = CompanyDA.get_company_industry_ids(company_id)

            new_industries = set(posted_industries) - set(listed_industries)
            to_delete_industries = set(
                listed_industries) - set(posted_industries)

            if len(new_industries) > 0:
                for industry_id in new_industries:
                    CompanyDA.add_company_industry(
                        industry_id=industry_id, company_id=company_id)

            if len(to_delete_industries) > 0:
                for industry_id in to_delete_industries:
                    CompanyDA.unlist_company_industry(
                        industry_id=industry_id, company_id=company_id)

            company = CompanyDA.get_company(company_id)

            if company:
                resp.body = json.dumps({
                    "description": "Company details updated successfully",
                    "data": company,
                    "success": True
                }, default_parser=json.parser)
            else:
                resp.body = json.dumps({
                    "description": "Something went wrong when updating company details",
                    "success": False
                }, default_parser=json.parser)

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session
    def on_post_members_update(self, req, resp, company_id):
        member_id = req.context.auth['session']['member_id']
        try:
            (company_members, departments) = request.get_json_or_form(
                "companyMembers", "departments", req=req)

            member_role = CompanyDA.get_member_role(member_id, company_id)
            self._check_company_update_privileges(req, member_role)

            listed_dep_ids = CompanyDA.get_company_departments(company_id)
            incoming_dep_ids = []
            if not departments:
                incoming_dep_ids = []
            if isinstance(departments, list):
                incoming_dep_ids = [dep["department_id"]
                                    for dep in departments]

            to_add_deps = set(incoming_dep_ids) - set(listed_dep_ids)
            to_delete_deps = set(listed_dep_ids) - set(incoming_dep_ids)

            logger.info(f"to_add_deps {to_add_deps}")
            logger.info(f"to_delete_deps {to_delete_deps}")
            if len(to_add_deps) > 0:
                for department_id in to_add_deps:
                    CompanyDA.add_company_department(company_id, department_id)

            if company_members and isinstance(company_members, list):
                if len(company_members) > 0:
                    for company_member in company_members:
                        CompanyDA.update_company_member_status({"company_member_id": company_member["company_member_id"],
                                                                "company_role": company_member["company_role"],
                                                                "department_name": json.convert_null(company_member["department_name"]),
                                                                "company_id": company_id,
                                                                "department_status": company_member["department_status"],
                                                                "author_id": member_id})

            if len(to_delete_deps) > 0:
                for department_id in to_delete_deps:
                    CompanyDA.unlist_company_department(
                        company_id, department_id)

            company = CompanyDA.get_company(company_id)

            if company:
                resp.body = json.dumps({
                    "description": "Company details updated successfully",
                    "data": company,
                    "success": True
                }, default_parser=json.parser)
            else:
                resp.body = json.dumps({
                    "description": "Something went wrong when updating company details",
                    "success": False
                }, default_parser=json.parser)

        except Exception as err:
            logger.exception(err)
            raise err

    @check_session_administrator
    def on_delete(self, req, resp):
        (company_ids) = request.get_json_or_form("companyIds", req=req)
        # company_ids = company_ids[0].split(',')

        res = CompanyDA.delete_companies(company_ids[0])
        resp.body = json.dumps({
            "data": res,
            "description": "Company's deleted successfully!",
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

            CompanyDA().update_company(company_id, name, place_id, address_1, address_2,
                                       city, state, postal, country_code_id, main_phone, primary_url, logo_storage_id)
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
            data = CompanyDA.get_unregistered_company(
                sort_params, page_size, page_number)

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
