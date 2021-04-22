import logging

# import uuid
# from dateutil.relativedelta import relativedelta
from app.util.db import source, formatSortingParams

logger = logging.getLogger(__name__)


class CompanyDA(object):
    source = source

    @classmethod
    def get_company(cls, company_id=None):
        query = ("""
            SELECT row_to_json(row) AS company
            FROM (
                SELECT
                    company.id,
                    company.name,
                    company.place_id,
                    parent_company.id AS parent_company_id,
	                parent_company.name AS parent_company_name,
                    -- industries
                    (
                        SELECT COALESCE(json_agg(rows), '[]'::json) as company_industries
                        FROM (
                            SELECT 
                                company_industry.industry_id,
                                profile_industry.name AS industry_name
                            FROM company_industry
                            LEFT JOIN profile_industry ON profile_industry.id =  company_industry.industry_id
                            WHERE company_id = company.id AND profile_industry.display_Status = TRUE
                        ) AS rows
                    ),
                    -- departments
                    (
                        SELECT COALESCE(json_agg(rows),'[]'::json) AS departments
                        FROM (
                            SELECT 
                                company_department.id AS company_department_id,
                                department_id,
                                department.name AS department_name
                            FROM company_department
                            LEFT JOIN department ON department.id = company_department.department_id
                            WHERE company_id = company.id
                        ) AS rows
                    ),
                    -- members
                    (
                        SELECT COALESCE(json_agg(rows), '[]'::json) AS company_members
                        FROM (
                            SELECT 
                                company_member.id AS company_member_id,
                                ls.company_role,
                                ls.company_department_id,
                                ls.department_name,
                                ls.department_status,
                                ls.update_date AS status_update_date,
                                member.id AS member_id,
                                member.first_name,
                                member.middle_name,
                                member.last_name,
                                member.email,
                                job_title.name,
                                file_path(file_storage_engine.storage_engine_id, '/member/file') AS amera_avatar_url
                            FROM company_member
                            LEFT JOIN (
                                SELECT DISTINCT ON (company_member_id)
                                    company_member_id,
                                    company_role,
                                    company_status,
                                    company_department_id,
                                    department.name AS department_name,
                                    department_status,
                                    company_member_status.update_date
                                FROM company_member_status
                                LEFT JOIN company_department ON company_department.id = company_member_status.company_department_id
                                LEFT JOIN department ON department.id = company_department.department_id
                                ORDER BY company_member_id, update_date DESC
                            ) AS ls ON ls.company_member_id = company_member.id
                            LEFT JOIN member ON company_member.member_id = member.id
                            LEFT JOIN job_title ON job_title_id = job_title.id
                            LEFT JOIN member_profile ON member.id = member_profile.member_id
                            LEFT JOIN file_storage_engine  ON file_storage_engine.id = member_profile.profile_picture_storage_id
                            WHERE company_id = company.id AND ls.company_status = 'active'
                        ) AS rows
                    ),
                    -- children
                    (
                        WITH ch AS (
                            SELECT 
                                company.id,
                                company.name,
                                company.parent_company_id
                            FROM company
                        )
                        SELECT COALESCE(json_agg(rows), '[]'::json) AS child_companies
                        FROM (
                            SELECT 
                                ch.id,
                                ch.name
                            FROM ch
                            WHERE ch.parent_company_id = company.id
                        ) AS rows
                    ),
                    company.address_1,
                    company.address_2,
                    company.city,
                    company.state,
                    company.postal,
                    company.province,
                    company.country_code_id,
                    country_code.name as country,
                    country_code.alpha3,
                    currency_code.id AS currency_code_id,
                    currency_code.currency_code,
                    currency_code.currency_name,
                    company.main_phone,
                    company.primary_url,
                    company.email,
                    company.logo_storage_id,
                    file_path(file_storage_engine.storage_engine_id, '/member/file') as logo_url,
                    company.create_date
                FROM company
                LEFT JOIN country_code ON country_code.id = company.country_code_id
                LEFT JOIN currency_code ON currency_code.id = country_code.currency_code_id
                LEFT JOIN file_storage_engine ON file_storage_engine.id = company.logo_storage_id
                LEFT JOIN company AS parent_company ON parent_company.id = company.parent_company_id
                WHERE company.id = %s
            ) AS row
        """)

        params = (company_id, )

        cls.source.execute(query, params)
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def get_companies(cls, member_id=None, sort_params=None, page_size=None, page_number=None):
        sort_columns_string = 'company.name ASC'
        company_dict = {
            'company_name': 'company.name',
            'address_1': 'company.address_1',
            'address_2': 'company.address_2',
            'city': 'company.city',
            'state': 'company.state',
            'postal': 'company.postal',
            'country_code_id': 'company.country_code_id',
            'country': 'country_code.name',
            'main_phone': 'company.main_phone',
            'primary_url': 'company.primary_url',
            'create_date': 'company.create_date',
            'update_date': 'company.update_date'
        }

        if sort_params:
            sort_columns_string = formatSortingParams(
                sort_params, company_dict) or sort_columns_string

        query = (f"""
            SELECT json_agg(rows) AS companies
            FROM (
                SELECT
                    company.id,
                    company.name,
                    company.place_id,
                    parent_company.id AS parent_company_id,
	                parent_company.name AS parent_company_name,
                    -- industries
                    (
                        SELECT COALESCE(json_agg(rows), '[]'::json) as company_industries
                        FROM (
                            SELECT 
                                company_industry.industry_id,
                                profile_industry.name AS industry_name
                            FROM company_industry
                            LEFT JOIN profile_industry ON profile_industry.id =  company_industry.industry_id
                            WHERE company_id = company.id AND profile_industry.display_Status = TRUE
                        ) AS rows
                    ),
                    -- departments
                    (
                        SELECT COALESCE(json_agg(rows),'[]'::json) AS departments
                        FROM (
                            SELECT 
                                company_department.id AS company_department_id,
                                department_id,
                                department.name AS department_name
                            FROM company_department
                            LEFT JOIN department ON department.id = company_department.department_id
                            WHERE company_id = company.id
                        ) AS rows
                    ),
                    -- members
                    (
                        SELECT COALESCE(json_agg(rows), '[]'::json) AS company_members
                        FROM (
                            SELECT 
                                company_member.id AS company_member_id,
                                ls.company_role,
                                ls.company_department_id,
                                ls.department_name,
                                ls.department_status,
                                ls.update_date AS status_update_date,
                                member.id AS member_id,
                                member.first_name,
                                member.middle_name,
                                member.last_name,
                                member.email,
                                job_title.name,
                                file_path(file_storage_engine.storage_engine_id, '/member/file') AS amera_avatar_url
                            FROM company_member
                            LEFT JOIN (
                                SELECT DISTINCT ON (company_member_id)
                                    company_member_id,
                                    company_role,
                                    company_status,
                                    company_department_id,
                                    department.name AS department_name,
                                    department_status,
                                    company_member_status.update_date
                                FROM company_member_status
                                LEFT JOIN company_department ON company_department.id = company_member_status.company_department_id
                                LEFT JOIN department ON department.id = company_department.department_id
                                ORDER BY company_member_id, update_date DESC
                            ) AS ls ON ls.company_member_id = company_member.id
                            LEFT JOIN member ON company_member.member_id = member.id
                            LEFT JOIN job_title ON job_title_id = job_title.id
                            LEFT JOIN member_profile ON member.id = member_profile.member_id
                            LEFT JOIN file_storage_engine  ON file_storage_engine.id = member_profile.profile_picture_storage_id
                            WHERE company_id = company.id AND ls.company_status = 'active'
                        ) AS rows
                    ),
                    -- children
                    (
                        WITH ch AS (
                            SELECT 
                                company.id,
                                company.name,
                                company.parent_company_id
                            FROM company
                        )
                        SELECT COALESCE(json_agg(rows), '[]'::json) AS child_companies
                        FROM (
                            SELECT 
                                ch.id,
                                ch.name
                            FROM ch
                            WHERE ch.parent_company_id = company.id
                        ) AS rows
                    ),
                    company.address_1,
                    company.address_2,
                    company.city,
                    company.state,
                    company.postal,
                    company.province,
                    company.country_code_id,
                    country_code.name as country,
                    country_code.alpha3,
                    currency_code.id AS currency_code_id,
                    currency_code.currency_code,
                    currency_code.currency_name,
                    company.email,
                    company.main_phone,
                    company.primary_url,
                    company.logo_storage_id,
                    file_path(file_storage_engine.storage_engine_id, '/member/file') as logo_url,
                    company.create_date
                FROM company
                LEFT JOIN country_code ON country_code.id = company.country_code_id
                LEFT JOIN currency_code ON currency_code.id = country_code.currency_code_id
                LEFT JOIN file_storage_engine ON file_storage_engine.id = company.logo_storage_id
                LEFT JOIN company AS parent_company ON parent_company.id = company.parent_company_id
                {"INNER JOIN company_member ON company_member.company_id = company.id WHERE company_member.member_id = %s" if member_id else ''}
                ORDER BY {sort_columns_string}
            ) AS rows
        """)

        companies = []
        params = ()
        if member_id:
            params = (member_id,)

        count_member_where = """
            INNER JOIN company_member ON company_member.company_id = company.id 
            WHERE company_member.member_id = %s
        """

        count_query = (f"""
            SELECT
                COUNT(DISTINCT company.id)
            FROM 
                company
            {count_member_where if member_id else ""}
        """)

        logger.debug(f"Count Query: \n {count_query}")

        count = 0
        cls.source.execute(count_query, params)

        if cls.source.has_results():
            result = cls.source.cursor.fetchone()
            (count, ) = result

        if count == 0:
            return {
                "data": companies,
                "count": count
            }

        if page_size and page_number >= 0:
            query += """LIMIT %s OFFSET %s"""
            offset = 0
            if page_number > 0:
                offset = page_number * page_size
            params = params + (page_size, offset)

        cls.source.execute(query, params)
        if cls.source.has_results():
            companies = cls.source.cursor.fetchone()[0]

        return {
            "data": companies,
            "count": count
        }

    @classmethod
    def create_company(cls, name, place_id, address_1, address_2, city, state, postal, country_code_id, main_phone, primary_url, logo_storage_id, commit=True):
        query = ("""
            INSERT INTO company (name, place_id, address_1, address_2, city, state, postal, country_code_id, main_phone, primary_url, logo_storage_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """)

        params = (name, place_id, address_1, address_2, city,
                  state, postal, country_code_id,
                  main_phone, primary_url, logo_storage_id)
        cls.source.execute(query, params)
        id = cls.source.get_last_row_id()

        if commit:
            cls.source.commit()

        return id

    @classmethod
    def update_company(cls, company_id, name, place_id, address_1, address_2, city, state, postal, country_code_id, main_phone, primary_url, logo_storage_id, commit=True):
        query = ("""
            UPDATE company
            SET
                name = %s,
                place_id = %s,
                address_1 = %s,
                address_2 = %s,
                city = %s,
                state = %s,
                postal = %s,
                country_code_id = %s,
                main_phone = %s,
                primary_url = %s,
                logo_storage_id = %s
            WHERE id = %s
        """)

        params = (name, place_id, address_1, address_2,
                  city, state, postal, country_code_id,
                  main_phone, primary_url, logo_storage_id, company_id)

        cls.source.execute(query, params)

        if commit:
            cls.source.commit()

    @classmethod
    def update_company_picture(cls, company_id, picture_id, commit=True):
        query = ("""
            UPDATE company
            SET logo_storage_id = %s
            WHERE id = %s
            RETURNING id
        """)
        params = (picture_id, company_id)
        cls.source.execute(query, params)
        if commit:
            cls.source.commit()
        id = cls.source.get_last_row_id()
        return id

    @classmethod
    def update_company_details(cls, params, commit=True):
        query = ("""
            UPDATE company
            SET name = %(name)s,
                email = %(email)s,
                primary_url = %(primary_url)s,
                main_phone = %(main_phone)s,
                country_code_id = %(country_code_id)s,
                place_id = %(place_id)s,
                address_1 = %(address_1)s,
                address_2 = %(address_2)s,
                city = %(city)s,
                state = %(state)s,
                postal = %(postal)s,
                province = %(province)s
            WHERE id = %(company_id)s
            RETURNING id
        """)
        cls.source.execute(query, params)
        if commit:
            cls.source.commit()
        id = cls.source.get_last_row_id()
        return id

    # Industries
    @classmethod
    def get_company_industry_ids(cls, company_id):
        query = ("""
            SELECT ARRAY (
                SELECT industry_id
                FROM company_industry
                WHERE company_id = %s
            )
        """)
        cls.source.execute(query, (company_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def add_company_industry(cls, industry_id, company_id, commit=True):
        query = ("""
            INSERT INTO company_industry (industry_id, company_id)
            VALUES (%s, %s)
        """)
        cls.source.execute(query, (industry_id, company_id))
        if commit:
            cls.source.commit()

    @classmethod
    def unlist_company_industry(cls, industry_id, company_id, commit=True):
        query = ("""
            DELETE FROM company_industry
            WHERE industry_id = %s AND company_id = %s
        """)
        cls.source.execute(query, (industry_id, company_id))
        if commit:
            cls.source.commit()

    # Departments
    @classmethod
    def get_company_departments(cls, company_id):
        query = ("""
            SELECT ARRAY (
                SELECT department.id
                FROM company_department
                LEFT JOIN department ON department.id = company_department.department_id
                WHERE company_id = %s
            )
        """)
        cls.source.execute(query, (company_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def add_company_department(cls, company_id, department_id, commit=True):
        query = ("""
            INSERT INTO company_department (company_id, department_id) 
            VALUES (%s, %s)
            RETURNING id
        """)
        cls.source.execute(query, (company_id, department_id))
        if commit:
            cls.source.commit()

    @classmethod
    def unlist_company_department(cls, company_id, department_id, commit=True):
        query = ("""
            DELETE FROM company_department
            WHERE company_id = %s AND department_id = %s
        """)
        cls.source.execute(query, (company_id, department_id))
        if commit:
            cls.source.commit()

    # Company member props update
    @classmethod
    def update_company_member_status(cls, params, commit=True):
        query = ("""
            INSERT INTO company_member_status (company_member_id, company_role, company_department_id, department_status, update_by) 
            VALUES (
                %(company_member_id)s,
                %(company_role)s,
                (
                    SELECT company_department.id 
                    FROM company_department
                    LEFT JOIN department ON department.id = company_department.department_id
                    WHERE department.name = %(department_name)s AND company_id = %(company_id)s
                ),
                %(department_status)s,
                %(author_id)s
            )
        """)
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
    def add_member(cls, company_id, member_id, commit=True):
        try:
            query = ("""
                INSERT INTO company_member (company_id, member_id)
                VALUES (%s, %s)
            """)

            params = (company_id, member_id)
            cls.source.execute(query, params)

            if commit:
                cls.source.commit()
        except Exception:
            logger.exception('Unable to add a member')
            return None

    @classmethod
    def delete_member(cls, company_id, member_id, commit=True):
        try:
            query = ("""
                DELETE
                FROM company_member
                WHERE company_id = %s and member_id = %s
            """)

            params = (company_id, member_id)
            cls.source.execute(query, params)

            if commit:
                cls.source.commit()
        except Exception:
            logger.exception('UNable to remove a member')
            return None

    # Owner and admins
    @classmethod
    def get_member_role(cls, member_id, company_id):
        query = ("""
            SELECT company_role
            FROM company_member
            LEFT JOIN company_member_status ON company_member_status.company_member_id = company_member.id
            WHERE member_id = %s AND company_id = %s
            ORDER BY company_member_status.update_date DESC
            LIMIT 1
        """)
        params = (member_id, company_id)
        cls.source.execute(query, params)
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    # Unregistered
    @classmethod
    def get_unregistered_company(cls, sort_params, page_size=None, page_number=None):
        try:
            sort_columns_string = 'member.company_name ASC'
            company_dict = {
                'company_name': 'member.company_name',
                'total_members': 'total_members'
            }
            if sort_params:
                sort_columns_string = formatSortingParams(
                    sort_params, company_dict) or sort_columns_string

            query = (f"""
                SELECT member.company_name, count(distinct (member.company_name)) as total_members
                FROM member
                WHERE member.company_name IS NOT NULL
                GROUP BY member.company_name
                ORDER BY {sort_columns_string}
            """)
            params = ()

            count_query = (f"""
                SELECT COUNT(*)
                    FROM (
                            SELECT COUNT(DISTINCT member.id)
                            FROM member
                            WHERE member.company_name IS NOT NULL
                            GROUP BY member.company_name
                        ) as sq
            """)

            count = 0
            cls.source.execute(count_query, None)

            if cls.source.has_results():
                result = cls.source.cursor.fetchone()
                (count, ) = result

            if count > 0 and page_size and page_number >= 0:
                query += """LIMIT %s OFFSET %s"""
                offset = 0
                if page_number > 0:
                    offset = page_number * page_size
                params = params + (page_size, offset)

            companies = []
            cls.source.execute(query, params)
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

            return {
                "data": companies,
                "count": count
            }

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
                INSERT INTO company_member (company_id, member_id)
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
