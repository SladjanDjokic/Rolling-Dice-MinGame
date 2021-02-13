import logging

# import uuid
# from dateutil.relativedelta import relativedelta
from app.util.db import source
from app.exceptions.data import DuplicateKeyError, DataMissingError, \
    RelationshipReferenceError
from app.util.filestorage import amerize_url
from app.util.security import SECURITY_EXCHANGE_OPTIONS

logger = logging.getLogger(__name__)


class CompanyDA(object):
    source = source

    @classmethod
    def get_company(cls, company_id=None):
        query = ("""
            SELECT
                company.id,
                company.name,
                company.address_1,
                company.address_2,
                company.city,
                company.country_code_id,
                country_code.name as country,
                company.main_phone,
                company.primary_url,
                company.logo_storage_id,
                file_path(file_storage_engine.storage_engine_id, '/member/file') as s3_logo_url,
                company.create_date,
                COALESCE(json_agg(DISTINCT t1.*) FILTER (WHERE t1.id IS NOT NULL), '[]') AS members
            FROM company
            LEFT JOIN country_code on country_code.id = company.country_code_id
            LEFT OUTER JOIN file_storage_engine ON file_storage_engine.id = company.logo_storage_id
            LEFT OUTER JOIN company_role_xref crx on crx.company_id = company.id
            LEFT OUTER JOIN (
                SELECT
                    member.id,
                    member.first_name,
                    member.last_name,
                    job_title.name as title
                FROM member
                LEFT OUTER JOIN job_title ON job_title.id = member.job_title_id 
            ) as t1 ON t1.id = crx.member_id
            WHERE company.id = %s
            GROUP BY 
                company.id,
                company.name,
                company.address_1,
                company.address_2,
                company.city,
                company.country_code_id,
                country_code.name,
                company.main_phone,
                company.primary_url,
                company.logo_storage_id,
                file_storage_engine.storage_engine_id,
                company.create_date
        """)
    
        params = (company_id, )

        cls.source.execute(query, params)
        if cls.source.has_results():
            (
                id,
                name,
                address_1,
                address_2,
                city,
                country_code_id,
                country,
                main_phone,
                primary_url,
                logo_storage_id,
                s3_logo_url,
                create_date,
                members
            ) = cls.source.cursor.fetchone()
            return {
                "id": id,
                "name": name,
                "address_1": address_1,
                "address_2": address_2,
                "city": city,
                "country_code_id": country_code_id,
                "country": country,
                "main_phone": main_phone,
                "primary_url": primary_url,
                "logo_storage_id": logo_storage_id,
                "s3_logo_url": s3_logo_url,
                "create_date": create_date,
                "members": members
            }

        return None

    @classmethod
    def get_all_companies(cls):
        query = ("""
            SELECT
                company.id,
                company.name,
                company.address_1,
                company.address_2,
                company.city,
                company.country_code_id,
                country_code.name as country,
                company.main_phone,
                company.primary_url,
                company.logo_storage_id,
                file_path(file_storage_engine.storage_engine_id, '/member/file') as s3_logo_url,
                company.create_date,
                COALESCE(json_agg(DISTINCT t1.*) FILTER (WHERE t1.id IS NOT NULL), '[]') AS members
            FROM company
            LEFT JOIN country_code on country_code.id = company.country_code_id
            LEFT OUTER JOIN file_storage_engine ON file_storage_engine.id = company.logo_storage_id
            LEFT OUTER JOIN company_role_xref crx on crx.company_id = company.id
            LEFT OUTER JOIN (
                SELECT
                    member.id,
                    member.first_name,
                    member.last_name,
                    job_title.name as title
                FROM member
                LEFT OUTER JOIN job_title ON job_title.id = member.job_title_id 
            ) as t1 ON t1.id = crx.member_id
            GROUP BY 
                company.id,
                company.name,
                company.address_1,
                company.address_2,
                company.city,
                company.country_code_id,
                country_code.name,
                company.main_phone,
                company.primary_url,
                company.logo_storage_id,
                file_storage_engine.storage_engine_id,
                company.create_date
        """)
        companies = []

        cls.source.execute(query, None)
        if cls.source.has_results():
            for (
                id,
                name,
                address_1,
                address_2,
                city,
                country_code_id,
                country,
                main_phone,
                primary_url,
                logo_storage_id,
                s3_logo_url,
                create_date,
                members
            ) in cls.source.cursor:
                company = {
                    "id": id,
                    "name": name,
                    "address_1": address_1,
                    "address_2": address_2,
                    "city": city,
                    "country_code_id": country_code_id,
                    "country": country,
                    "main_phone": main_phone,
                    "primary_url": primary_url,
                    "logo_storage_id": logo_storage_id,
                    "s3_logo_url": s3_logo_url,
                    "create_date": create_date,
                    "members": members
                }

                companies.append(company)

        return companies
    
    @classmethod
    def create_company(cls, name, address_1, address_2, city, country_code_id, main_phone, primary_url, logo_storage_id, commit=True):
        query = ("""
            INSERT INTO company (name, address_1, address_2, city, country_code_id, main_phone, primary_url, logo_storage_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """)

        params = (name, address_1, address_2, city, country_code_id, main_phone, primary_url, logo_storage_id)
        cls.source.execute(query, params)
        id = cls.source.get_last_row_id()

        if commit:
            cls.source.commit()

        return id

    @classmethod
    def update_company(cls, company_id, name, address_1, address_2, city, country_code_id, main_phone, primary_url, logo_storage_id, commit=True):
        query = ("""
            UPDATE company
            SET
                name = %s,
                address_1 = %s,
                address_2 = %s,
                city = %s,
                country_code_id = %s,
                main_phone = %s,
                primary_url = %s,
                logo_storage_id = %s
            WHERE id = %s
        """)

        params = (name, address_1, address_2, city, country_code_id, main_phone, primary_url, logo_storage_id, company_id)

        cls.source.execute(query, params)

        if commit:
            cls.source.commit()

    @classmethod
    def delete_companies(cls, company_ids, commit=True):
        query = ("""
            DELETE FROM company WHERE id IN ( {} )
            """.format(company_ids))

        # params = (company_ids,)
        res = cls.source.execute(query, None)
        if commit:
            cls.source.commit()

        return res

    @classmethod
    def add_member(cls, company_id, member_id, company_role, commit=True):
        try:
            query = ("""
                INSERT INTO company_role_xref (company_id, member_id, company_role)
                VALUES (%s, %s, %s)
            """)

            params = (company_id, member_id, company_role)
            cls.source.execute(query, params)

            if commit:
                cls.source.commit()
        except Exception:
            logger.exception('UNable to add a member')
            return None

    @classmethod
    def delete_member(cls, company_id, member_id):
        try:
            query = ("""
                DELETE
                FROM company_role_xref
                WHERE company_id = %s and member_id = %s
            """)

            params = (company_id, member_id )
            cls.source.execute(query, params)

            if commit:
                cls.source.commit()
        except Exception:
            logger.exception('UNable to remove a member')
            return None

    @classmethod
    def get_unregistered_company(cls):
        try: 
            query = ("""
                SELECT member.company_name, count(distinct (member.company_name)) as total_members
                FROM member
                WHERE member.company_name IS NOT NULL
                GROUP BY member.company_name
            """)

            companies = []
            cls.source.execute(query, None)
            if cls.source.has_results():
                for (
                    company_name,
                    total_members
                ) in cls.source.cursor:
                    company = {
                        "company_name": company_name,
                        "total_members": total_members
                    }

                    companies.append(company)

            return companies

        except Exception:
            return None

    @classmethod
    def create_company_from_name(cls, company_name, commit=True):
        try:
            query = ("""
                INSERT INTO company (name)
                VALUES (%s)
                RETURNING id
            """)

            params = (company_name,)
            cls.source.execute(query, params)
            id = cls.source.get_last_row_id()

            if commit:
                cls.source.commit()

            query = ("""
                INSERT INTO company_role_xref (company_id, member_id)
                SELECT %s as company_id, member.id as member_id
                FROM member
                WHERE member.company_name = %s              
            """)

            params = (id, company_name, )
            cls.source.execute(query, params)
            if commit:
                cls.source.commit()

            query = ("""
                UPDATE member
                SET company_name = NULL
                WHERE company_name = %s
            """)

            params = (company_name,)

            cls.source.execute(query, params)
            if commit:
                cls.source.commit()

            return cls.get_company(id)
        except Exception as e:
            raise e 

    @classmethod
    def update_unregistered_company(cls, company_name, new_company_name, commit=True):
        query = ("""
            UPDATE member
            SET company_name = %s
            WHERE company_name = %s
        """)

        params = (new_company_name, company_name, )
        cls.source.execute(query, params)
        if commit:
            cls.source.commit()

    @classmethod
    def delete_unregistered_company(cls, company_name, commit=True):
        query = ("""
            UPDATE member
            SET company_name = NULL
            WHERE company_name = %s
        """)

        params = (company_name, )
        cls.source.execute(query, params)

        if commit:
            cls.source.commit()

def formatSortingParams(sort_by, entity_dict):
    columns_list = sort_by.split(',')
    new_columns_list = list()

    for column in columns_list:
        if column[0] == '-':
            column = column[1:]
            column = entity_dict.get(column)
            if column:
                column = column + ' DESC'
                new_columns_list.append(column)
        else:
            column = entity_dict.get(column)
            if column:
                column = column + ' ASC'
                new_columns_list.append(column)

    return (',').join(column for column in new_columns_list)
