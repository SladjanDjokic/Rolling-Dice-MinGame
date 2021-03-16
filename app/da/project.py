import logging
from app.util.db import source
logger = logging.getLogger(__name__)


class ProjectDA(object):
    source = source

    @classmethod
    def get_all_projects(cls):
        query = ("""
        SELECT json_agg(result) as projects
        FROM (
                SELECT 
                    project.id as project_id,
                    -- Company info
                    (
                        SELECT row_to_json(row) as company
                        FROM 
                        (
                            SELECT 
                                id as company_id,
                                name
                            FROM company
                            WHERE company_id = company.id
                        ) AS row
                    ),
                    project_title,
                    project_type,
                    project_description,
                    group_id,
                    group_name,
                    exchange_option AS group_exchange_option,
                    -- current owner
                    (
                        SELECT row_to_json(row) as ownership
                        FROM (
                            SELECT 
                                owner_id as current_owner_id,
                                update_date as owner_since_date
                            FROM project_owner_xref
                            WHERE project_owner_xref.project_id = project.id 
                            ORDER BY update_date DESC
                            LIMIT 1
                        ) as row
                    ),
                    -- Project elements
                    (
                        SELECT json_agg(rows) as project_elements
                        FROM (
                            SELECT
                                project_element.id as project_element_id,
                                parent_id,
                                element_type,
                                title,
                                description,
                                contract_id,
                                project_member_contract.project_member_id,
                                est_hours,
                                -- status_history
                                (
                                    SELECT json_agg(rows) as status_history
                                    FROM (
                                        SELECT
                                            id as status_change_id,
                                            element_status,
                                            update_date,
                                            update_by
                                        FROM project_element_status
                                        WHERE project_element_status.project_element_id = project_element.id
                                    ) as rows
                                ),
                                project_element.create_date,
                                project_element.create_by,
                                project_element.update_date,
                                project_element.update_by,
                                -- notes
                                (
                                    SELECT json_agg(rows) as element_notes
                                    FROM (
                                        SELECT
                                            id as element_note_id,
                                            element_note,
                                            create_date,
                                            create_by,
                                            update_date,
                                            update_by
                                        FROM project_element_note
                                        WHERE project_element_id = project_element.id
                                    ) AS rows
                                ),
                                -- time
                                (
                                    SELECT json_agg(rows) as element_time
                                    FROM (
                                        SELECT
                                            id as element_time_id,
                                            element_summary,
                                            element_time,
                                            create_date,
                                            create_by,
                                            update_date,
                                            update_by
                                        FROM project_element_time
                                        WHERE project_element_id = project_element.id
                                    ) AS rows
                                )
                            FROM project_element
                            LEFT JOIN project_member_contract ON project_member_contract.id = project_element.contract_id
                            WHERE project_id = project.id
                        ) AS rows
                    ),
                    start_date,
                    estimated_days,
                    update_by,
                    project.update_date,
                    -- All project members
                    (
                        SELECT json_agg(rows) as project_members
                        FROM (
                            SELECT 
                                project_member.id as project_member_id,
                                member.id as member_id,
                                first_name,
                                middle_name,
                                last_name,
                                company_name,
                                job_title.name as title,
                                department.name as department,
                                file_path(file_storage_engine.storage_engine_id, '/member/file') as amera_avatar_url,
                                -- Roles
                                (
                                    SELECT ARRAY(
                                        SELECT project_role_id
                                        FROM project_role_xref
                                        WHERE project_member_id = project_member.id
                                    ) AS project_roles
                                ),    
                                privileges
                            FROM project_member
                            LEFT JOIN member ON project_member.member_id = member.id
                            LEFT JOIN job_title ON job_title_id = job_title.id
                            LEFT JOIN department ON department_id = department.id
                            LEFT JOIN member_profile ON member.id = member_profile.member_id
                            LEFT JOIN file_storage_engine ON file_storage_engine.id = member_profile.profile_picture_storage_id
                            WHERE project_member.project_id = project.id AND project_member.is_active = TRUE
                        ) AS ROWS
                    ),
                    -- All contracts
                    (
                        SELECT json_agg(rows) as contracts
                        FROM (
                            SELECT
                                project_member_contract.id AS contract_id,
                                project_member_id,
                                pay_rate,
                                rate_type,
                                currency_code_id,
                                -- status
                                (
                                    SELECT json_agg(rows) AS status_history
                                    FROM (
                                        SELECT 
                                            id,
                                            contract_status,
                                            update_date,
                                            update_by
                                        FROM project_contract_status
                                        WHERE contract_id = project_member_contract.id
                                        ORDER BY update_by DESC
                                        LIMIT 10
                                    ) AS rows
                                ),
                                project_member_contract.create_date,
                                project_member_contract.create_by,
                                project_member_contract.update_date,
                                project_member_contract.update_by
                            FROM project_member_contract
                            LEFT JOIN project_member ON project_member.id = project_member_id
                            WHERE project_member.project_id = project.id AND project_member_contract.id IN (
                                -- Only contracts that apply to existing tasks
                                SELECT contract_id
                                FROM project_element
                                WHERE project_id = project.id
                            ) 
                        ) AS rows
                    ),
                    -- defined tasks
                    (
                        SELECT COUNT(*) as defined_tasks
                        FROM (
                            SELECT DISTINCT ON (project_element.id) project_element.id, title, project_element_status.element_status, project_element_status.update_date
                            FROM project_element
                            LEFT JOIN project_element_status ON project_element_status.project_element_id = project_element.id
                            WHERE element_type = 'task' AND project_id = project.id
                            ORDER BY project_element.id, project_element_status.update_date DESC
                        ) AS temp
                        WHERE temp.element_status = 'define'
                    ),
                    -- in progress tasks
                    (
                        SELECT COUNT(*) as in_progress_tasks
                        FROM (
                            SELECT DISTINCT ON (project_element.id) project_element.id, title, project_element_status.element_status, project_element_status.update_date
                            FROM project_element
                            LEFT JOIN project_element_status ON project_element_status.project_element_id = project_element.id
                            WHERE element_type = 'task' AND project_id = project.id
                            ORDER BY project_element.id, project_element_status.update_date DESC
                        ) AS temp
                        WHERE temp.element_status = 'in progress'
                    ),
                    -- completed tasks
                    (
                        SELECT COUNT(*) as completed_tasks
                        FROM (
                            SELECT DISTINCT ON (project_element.id) project_element.id, title, project_element_status.element_status, project_element_status.update_date
                            FROM project_element
                            LEFT JOIN project_element_status ON project_element_status.project_element_id = project_element.id
                            WHERE element_type = 'task' AND project_id = project.id
                            ORDER BY project_element.id, project_element_status.update_date DESC
                        ) AS temp
                        WHERE temp.element_status = 'complete'
                    ),
                    -- cancelled tasks
                    (
                        SELECT COUNT(*) as cancelled_tasks
                        FROM (
                            SELECT DISTINCT ON (project_element.id) project_element.id, title, project_element_status.element_status, project_element_status.update_date
                            FROM project_element
                            LEFT JOIN project_element_status ON project_element_status.project_element_id = project_element.id
                            WHERE element_type = 'task' AND project_id = project.id
                            ORDER BY project_element.id, project_element_status.update_date DESC
                        ) AS temp
                        WHERE temp.element_status = 'cancel'
                    ),
                    -- suspended tasks
                    (
                        SELECT COUNT(*) as suspended_tasks
                        FROM (
                            SELECT DISTINCT ON (project_element.id) project_element.id, title, project_element_status.element_status, project_element_status.update_date
                            FROM project_element
                            LEFT JOIN project_element_status ON project_element_status.project_element_id = project_element.id
                            WHERE element_type = 'task' AND project_id = project.id
                            ORDER BY project_element.id, project_element_status.update_date DESC
                        ) AS temp
                        WHERE temp.element_status = 'suspend'
                    ),
                    -- deleted tasks
                    (
                        SELECT COUNT(*) as deleted_tasks
                        FROM (
                            SELECT DISTINCT ON (project_element.id) project_element.id, title, project_element_status.element_status, project_element_status.update_date
                            FROM project_element
                            LEFT JOIN project_element_status ON project_element_status.project_element_id = project_element.id
                            WHERE element_type = 'task' AND project_id = project.id
                            ORDER BY project_element.id, project_element_status.update_date DESC
                        ) AS temp
                        WHERE temp.element_status = 'delete'
                    ),
                    -- not cancelled or deleted (to get 100 percent)
                    (
                        SELECT COUNT(*) as active_tasks
                        FROM (
                            SELECT DISTINCT ON (project_element.id) project_element.id, title, project_element_status.element_status, project_element_status.update_date
                            FROM project_element
                            LEFT JOIN project_element_status ON project_element_status.project_element_id = project_element.id
                            WHERE element_type = 'task' AND project_id = project.id
                            ORDER BY project_element.id, project_element_status.update_date DESC
                        ) AS temp
                        WHERE temp.element_status != 'cancel' OR temp.element_status != 'delete' OR temp.element_status != 'suspend' 
                    )
            FROM project
            LEFT JOIN member_group ON member_group.id = group_id
        ) as result
        """)
        cls.source.execute(query, None)
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def get_related_projects(cls, member_id):
        query = ("""
            SELECT json_agg(result) as projects
            FROM (
                SELECT 
                    project.id as project_id,
                    -- Company info
                    (
                        SELECT row_to_json(row) as company
                        FROM 
                        (
                            SELECT 
                                id as company_id,
                                name
                            FROM company
                            WHERE company_id = company.id
                        ) AS row
                    ),
                    project_title,
                    project_type,
                    project_description,
                    group_id,
                    group_name,
                    exchange_option AS group_exchange_option,
                    -- current owner
                    (
                        SELECT row_to_json(row) as ownership
                        FROM (
                            SELECT 
                                owner_id as current_owner_id,
                                update_date as owner_since_date
                            FROM project_owner_xref
                            WHERE project_owner_xref.project_id = project.id 
                            ORDER BY update_date DESC
                            LIMIT 1
                        ) as row
                    ),
                    -- Project elements
                    (
                        SELECT json_agg(rows) as project_elements
                        FROM (
                            SELECT
                                project_element.id as project_element_id,
                                parent_id,
                                element_type,
                                title,
                                description,
                                contract_id,
                                project_member_contract.project_member_id,
                                est_hours,
                                -- status_history
                                (
                                    SELECT json_agg(rows) as status_history
                                    FROM (
                                        SELECT
                                            id as status_change_id,
                                            element_status,
                                            update_date,
                                            update_by
                                        FROM project_element_status
                                        WHERE project_element_status.project_element_id = project_element.id
                                    ) as rows
                                ),
                                project_element.create_date,
                                project_element.create_by,
                                project_element.update_date,
                                project_element.update_by,
                                -- notes
                                (
                                    SELECT json_agg(rows) as element_notes
                                    FROM (
                                        SELECT
                                            id as element_note_id,
                                            element_note,
                                            create_date,
                                            create_by,
                                            update_date,
                                            update_by
                                        FROM project_element_note
                                        WHERE project_element_id = project_element.id
                                    ) AS rows
                                ),
                                -- time
                                (
                                    SELECT json_agg(rows) as element_time
                                    FROM (
                                        SELECT
                                            id as element_time_id,
                                            element_summary,
                                            element_time,
                                            create_date,
                                            create_by,
                                            update_date,
                                            update_by
                                        FROM project_element_time
                                        WHERE project_element_id = project_element.id
                                    ) AS rows
                                )
                            FROM project_element
                            LEFT JOIN project_member_contract ON project_member_contract.id = project_element.contract_id
                            WHERE project_id = project.id
                        ) AS rows
                    ),
                    start_date,
                    estimated_days,
                    update_by,
                    project.update_date,
                    -- All project members
                    (
                        SELECT json_agg(rows) as project_members
                        FROM (
                            SELECT 
                                project_member.id as project_member_id,
                                member.id as member_id,
                                first_name,
                                middle_name,
                                last_name,
                                company_name,
                                job_title.name as title,
                                department.name as department,
                                file_path(file_storage_engine.storage_engine_id, '/member/file') as amera_avatar_url,
                                -- Roles
                                (
                                    SELECT ARRAY(
                                        SELECT project_role_id
                                        FROM project_role_xref
                                        WHERE project_member_id = project_member.id
                                    ) AS project_roles
                                ),    
                                privileges
                            FROM project_member
                            LEFT JOIN member ON project_member.member_id = member.id
                            LEFT JOIN job_title ON job_title_id = job_title.id
                            LEFT JOIN department ON department_id = department.id
                            LEFT JOIN member_profile ON member.id = member_profile.member_id
                            LEFT JOIN file_storage_engine ON file_storage_engine.id = member_profile.profile_picture_storage_id
                            WHERE project_member.project_id = project.id
                        ) AS ROWS
                    ),
                    -- All contracts
                    (
                        SELECT json_agg(rows) as contracts
                        FROM (
                            SELECT
                                project_member_contract.id AS contract_id,
                                project_member_id,
                                pay_rate,
                                rate_type,
                                currency_code_id,
                                -- status
                                (
                                    SELECT json_agg(rows) AS status_history
                                    FROM (
                                        SELECT 
                                            id,
                                            contract_status,
                                            update_date,
                                            update_by
                                        FROM project_contract_status
                                        WHERE contract_id = project_member_contract.id
                                        ORDER BY update_by DESC
                                        LIMIT 10
                                    ) AS rows
                                ),
                                project_member_contract.create_date,
                                project_member_contract.create_by,
                                project_member_contract.update_date,
                                project_member_contract.update_by
                            FROM project_member_contract
                            LEFT JOIN project_member ON project_member.id = project_member_id
                            WHERE project_member.project_id = project.id AND project_member_contract.id IN (
                                -- Only contracts that apply to existing tasks
                                SELECT contract_id
                                FROM project_element
                                WHERE project_id = project.id
                            ) 
                        ) AS rows
                    ),
                    -- defined tasks
                    (
                        SELECT COUNT(*) as defined_tasks
                        FROM (
                            SELECT DISTINCT ON (project_element.id) project_element.id, title, project_element_status.element_status, project_element_status.update_date
                            FROM project_element
                            LEFT JOIN project_element_status ON project_element_status.project_element_id = project_element.id
                            WHERE element_type = 'task' AND project_id = project.id
                            ORDER BY project_element.id, project_element_status.update_date DESC
                        ) AS temp
                        WHERE temp.element_status = 'define'
                    ),
                    -- in progress tasks
                    (
                        SELECT COUNT(*) as in_progress_tasks
                        FROM (
                            SELECT DISTINCT ON (project_element.id) project_element.id, title, project_element_status.element_status, project_element_status.update_date
                            FROM project_element
                            LEFT JOIN project_element_status ON project_element_status.project_element_id = project_element.id
                            WHERE element_type = 'task' AND project_id = project.id
                            ORDER BY project_element.id, project_element_status.update_date DESC
                        ) AS temp
                        WHERE temp.element_status = 'in progress'
                    ),
                    -- completed tasks
                    (
                        SELECT COUNT(*) as completed_tasks
                        FROM (
                            SELECT DISTINCT ON (project_element.id) project_element.id, title, project_element_status.element_status, project_element_status.update_date
                            FROM project_element
                            LEFT JOIN project_element_status ON project_element_status.project_element_id = project_element.id
                            WHERE element_type = 'task' AND project_id = project.id
                            ORDER BY project_element.id, project_element_status.update_date DESC
                        ) AS temp
                        WHERE temp.element_status = 'complete'
                    ),
                    -- cancelled tasks
                    (
                        SELECT COUNT(*) as cancelled_tasks
                        FROM (
                            SELECT DISTINCT ON (project_element.id) project_element.id, title, project_element_status.element_status, project_element_status.update_date
                            FROM project_element
                            LEFT JOIN project_element_status ON project_element_status.project_element_id = project_element.id
                            WHERE element_type = 'task' AND project_id = project.id
                            ORDER BY project_element.id, project_element_status.update_date DESC
                        ) AS temp
                        WHERE temp.element_status = 'cancel'
                    ),
                    -- suspended tasks
                    (
                        SELECT COUNT(*) as suspended_tasks
                        FROM (
                            SELECT DISTINCT ON (project_element.id) project_element.id, title, project_element_status.element_status, project_element_status.update_date
                            FROM project_element
                            LEFT JOIN project_element_status ON project_element_status.project_element_id = project_element.id
                            WHERE element_type = 'task' AND project_id = project.id
                            ORDER BY project_element.id, project_element_status.update_date DESC
                        ) AS temp
                        WHERE temp.element_status = 'suspend'
                    ),
                    -- deleted tasks
                    (
                        SELECT COUNT(*) as deleted_tasks
                        FROM (
                            SELECT DISTINCT ON (project_element.id) project_element.id, title, project_element_status.element_status, project_element_status.update_date
                            FROM project_element
                            LEFT JOIN project_element_status ON project_element_status.project_element_id = project_element.id
                            WHERE element_type = 'task' AND project_id = project.id
                            ORDER BY project_element.id, project_element_status.update_date DESC
                        ) AS temp
                        WHERE temp.element_status = 'delete'
                    ),
                    -- not cancelled or deleted (to get 100 percent)
                    (
                        SELECT COUNT(*) as active_tasks
                        FROM (
                            SELECT DISTINCT ON (project_element.id) project_element.id, title, project_element_status.element_status, project_element_status.update_date
                            FROM project_element
                            LEFT JOIN project_element_status ON project_element_status.project_element_id = project_element.id
                            WHERE element_type = 'task' AND project_id = project.id
                            ORDER BY project_element.id, project_element_status.update_date DESC
                        ) AS temp
                        WHERE temp.element_status != 'cancel' OR temp.element_status != 'delete' OR temp.element_status != 'suspend' 
                    )
                FROM project
                LEFT JOIN member_group ON member_group.id = group_id
                WHERE project.id IN (
                    SELECT project_id
                    FROM project_member
                    WHERE project_member.member_id = %s AND 'view'=ANY(project_member.privileges)
                )
            ) as result
        """)
        params = (member_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def get_all_project_roles(cls):
        query = ("""
            SELECT * FROM project_role
        """)
        cls.source.execute(query, None)
        roles = []
        if cls.source.has_results():
            for (id,
                 name
                 ) in cls.source.cursor:
                role = {
                    'id': id,
                    'name': name
                }
                roles.append(role)
        return roles

    @classmethod
    def create_project_entry(cls, params):
        query = ("""
            INSERT INTO project (company_id, project_title, project_type, project_description, start_date, estimated_days, group_id)
            VALUES (%(company_id)s, %(project_title)s, %(project_type)s, %(project_description)s, %(start_date)s, INTERVAL %(estimated_days)s, %(group_id)s)
            RETURNING id            
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[create_project_entry] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def update_project_entry(cls, params):
        query = ("""
            UPDATE project
            SET company_id = %(company_id)s,
                project_title = %(project_title)s,
                project_type = %(project_type)s,
                project_description = %(project_description)s,
                start_date = %(start_date)s,
                estimated_days = %(estimated_days)s,
                update_by = %(author_id)s
            WHERE id = %(project_id)s
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[update_project_entry] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def hard_delete_project_entry(cls, project_id):
        query = ("""
            WITH deleted AS (
                DELETE FROM project WHERE id = %s RETURNING *
            ) SELECT COUNT(*) FROM deleted
        """)
        cls.source.execute(query, (project_id,))
        cls.source.commit()
        if cls.source.has_results():
            if cls.source.cursor.fetchone()[0] == 1:
                return True
            else:
                return None
        else:
            return None

    @classmethod
    def create_project_member(cls, params):
        query = ("""
            INSERT INTO project_member (project_id, member_id, privileges, is_active)
            VALUES (%(project_id)s, %(member_id)s, %(privileges)s::project_privilege[], TRUE) --FIXME: 
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[create_project_member] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def assign_owner(cls, params):
        query = ("""
            INSERT INTO project_owner_xref (project_id, owner_id)
            VALUES (%(project_id)s, %(owner_id)s)
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[assign_owner] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def get_current_owner(cls, project_id):  # return project_member_id
        query = ("""
            SELECT owner_id FROM project_owner_xref WHERE project_id = %s
            ORDER BY update_date DESC
            LIMIT 1
        """)
        cls.source.execute(query, (project_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def assign_project_role(cls, params):
        query = ("""
            INSERT INTO project_role_xref (project_id, project_member_id, project_role_id)
            VALUES (%(project_id)s, %(project_member_id)s, %(project_role_id)s)
            RETURNING project_member_id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[assign_project_role] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def assign_project_privilege(cls, params):
        query = ("""
            UPDATE project_member
            SET privileges = %(privileges)s::project_privilege[]
            WHERE id = %(project_member_id)s
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        logger.debug(
            f"[assign_project_privilege] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def get_project_roles_for_member(cls, params):
        query = ("""
            SELECT ARRAY(
                SELECT project_role_id
                FROM project_role_xref
                WHERE project_id = %(project_id)s AND project_member_id = %(project_member_id)s
            ) AS roles
        """)
        cls.source.execute(query, params)
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def delete_project_member_role(cls, params):
        query = ("""
            WITH deleted AS (
                DELETE FROM project_role_xref
                WHERE project_id = %(project_id)s AND project_member_id = %(project_member_id)s AND project_role_id=%(project_role_id)s
                RETURNING *
            ) SELECT COUNT(*) FROM deleted
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[delete_project_member_role] TRANSACTION IDENTIFIER: {id}")
        if cls.source.has_results():
            return True
        else:
            return None

    @classmethod
    def get_member_ids_for_project(cls, project_id):
        query = ("""
            SELECT ARRAY(
                SELECT member_id
                FROM project_member
                WHERE project_id = %s AND is_active = TRUE
            ) AS member_ids
        """)
        cls.source.execute(query, (project_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def get_project_member_id(cls, project_id, member_id):
        query = ("""
            SELECT id FROM project_member
            WHERE project_id = %(project_id)s AND member_id = %(member_id)s
        """)
        cls.source.execute(
            query, {"project_id": project_id, "member_id": member_id})
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def delete_project_member(cls, project_member_id):
        query = ("""
            UPDATE project_member
                SET is_active = FALSE
                WHERE id = %s
                RETURNING id
        """)
        cls.source.execute(query, (project_member_id,))
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[delete_project_member] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def get_ids_of_family(cls, element_id, tasks_only=False, exclude_status=None):
        query = (f"""
            WITH RECURSIVE parent AS (
                SELECT id, title, element_type, 1 AS level
                FROM project_element
                WHERE id = %s
            UNION ALL
                SELECT pe.id, pe.title, pe.element_type, parent.level + 1 AS level
                FROM project_element pe
                JOIN parent ON pe.parent_id = parent.id
            )
            SELECT ARRAY(
                SELECT DISTINCT ON (parent.id) parent.id FROM parent
                LEFT JOIN project_element_status ON parent.id = project_element_status.project_element_id
                -- The next line allows to limit the output to tasks and/or exclude particular task_status (that will be used to make sure we dont delete/suspend something already deleted)
                {"WHERE " if tasks_only or exclude_status else ""}
                {"element_type = 'task'" if tasks_only else ""}
                {"AND " if tasks_only and exclude_status else ""}
                {"element_status != %s OR element_status IS NULL" if exclude_status else ""}
                ORDER BY parent.id, project_element_status.update_date DESC
            ) AS children_ids
        """)
        params = (element_id, exclude_status) if exclude_status else (
            element_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def get_ids_of_project(cls, project_id, tasks_only=False, exclude_status=None):
        query = (f"""
            SELECT ARRAY(
                SELECT DISTINCT ON (project_element.id) project_element.id 
                FROM project_element
                LEFT JOIN project_element_status ON project_element.id = project_element_status.project_element_id
                -- The next line allows to limit the output to tasks and/or exclude particular task_status (that will be used to make sure we dont delete/suspend something already deleted)
                WHERE project_id = %s
                {" AND element_type = 'task'" if tasks_only else ""}
                {"AND " if tasks_only and exclude_status else ""}
                {"element_status != %s OR element_status IS NULL" if exclude_status else ""}
                ORDER BY project_element.id, project_element_status.update_date DESC
            ) AS ids
        """)
        params = (project_id, exclude_status) if exclude_status else (
            project_id,)
        cls.source.execute(query, params)
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None
    # Element methods

    @classmethod
    def insert_element(cls, params):
        query = ("""
            INSERT INTO project_element (project_id, parent_id, element_type, title, description, contract_id, est_hours, create_by, update_by)
            VALUES (%(project_id)s, %(parent_id)s, %(element_type)s, %(title)s, %(description)s, %(contract_id)s, %(est_hours)s, %(author_id)s, %(author_id)s)
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[insert_element] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def update_element(cls, params):
        query = ("""
            UPDATE project_element
            SET project_id = %(project_id)s,
                parent_id = %(parent_id)s,
                element_type = %(parent_id)s,
                title = %(title)s,
                description = %(description)s,
                project_member_id = %(project_member_id)s,
                est_hours = %(est_hours)s,
                element_status=%(element_status)s,
                update_by = %(author_id)s
            WHERE id = %(element_id)s
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[update_element] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def get_all_elements_of_type(cls, project_id, element_type):
        query = ("""
            SELECT ARRAY (
                SELECT id FROM project_element WHERE project_id = %s AND element_type = %s
            ) AS ids
        """)
        cls.source.execute(query, (project_id, element_type))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def get_elements_project(cls, element_id):
        query = ("""SELECT project_id FROM project_element WHERE id = %s""")
        cls.source.execute(query, (element_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def get_project_by_note_id(cls, note_id):
        query = ("""
            SELECT project_id
            FROM project_element_note
            LEFT JOIN project_element ON project_element_note.project_element_id = project_element.id
            WHERE project_element_note.id = %s
        """)
        cls.source.execute(query, (note_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def get_project_by_time_id(cls, time_id):
        query = ("""
            SELECT project_id
            FROM project_element_time
            LEFT JOIN project_element ON project_element_time.project_element_id = project_element.id
            WHERE project_element_time.id = %s
        """)
        cls.source.execute(query, (time_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

        # Element status
    @classmethod
    def add_element_status_record(cls, element_id, author_id, status='define'):
        query = ("""
            INSERT INTO project_element_status (project_element_id, element_status, update_by)
            VALUES (%(element_id)s, %(status)s, %(author_id)s)    
            RETURNING id
        """)
        params = {"element_id": element_id,
                  "status": status, "author_id": author_id}
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[add_element_status] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def get_last_status(cls, element_id, except_status):
        query = ("""
            SELECT element_status
            FROM project_element_status
            WHERE project_element_id = %s AND element_status != %s
            ORDER BY update_date DESC
            LIMIT 1
        """)
        params = (element_id, except_status)
        cls.source.execute(query, params)
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        else:
            return None

    # Will hard delete children as will via ON DROP CASCADE
    @classmethod
    def hard_delete_element(cls, element_id):
        query = ("""
            WITH deleted AS (
                DELETE FROM project_element WHERE id = %s RETURNING *
            ) SELECT COUNT(*) FROM deleted
        """)
        cls.source.execute(query, (element_id,))
        cls.source.commit()
        if cls.source.has_results():
            return True
        else:
            return None

    # Notes

    @classmethod
    def add_note(cls, params):
        query = ("""
            INSERT INTO project_element_note (project_element_id, element_note, create_by, update_by)
            VALUES (%(project_element_id)s, %(element_note)s, %(author_id)s, %(author_id)s)
            RETURNING id 
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[add_note] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def update_note(cls, params):
        query = ("""
            UPDATE project_element_note
            SET element_note = %(element_note)s,
                update_by = %(author_id)s
            WHERE id = %(note_id)s
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[update_note] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def delete_note(cls, note_id):
        query = ("""
            WITH deleted AS (
                DELETE FROM project_element_note WHERE id = %s RETURNING *
            ) SELECT COUNT(*) FROM deleted
        """)
        cls.source.execute(query, (note_id,))
        cls.source.commit()
        if cls.source.has_results():
            return True
        else:
            return None

    # Time records

    @classmethod
    def add_time(cls, params):
        query = ("""
            INSERT INTO project_element_time (project_element_id, element_summary, element_time, create_by, update_by)
            VALUES (%(project_element_id)s, %(element_summary)s, %(element_time)s, %(author_id)s, %(author_id)s)
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[add_time] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def update_time(cls, params):
        query = ("""
            UPDATE project_element_time
            SET element_summary = %(element_summary)s,
                element_time = %(element_time)s,
                update_by = %(author_id)s
            WHERE id = %(time_id)s
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[update_time] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def delete_time(cls, time_id):
        query = ("""
            WITH deleted AS (
                DELETE FROM project_element_time WHERE id = %s RETURNING *
            ) SELECT COUNT(*) FROM deleted
        """)
        cls.source.execute(query, (time_id,))
        cls.source.commit()
        if cls.source.has_results():
            return True
        else:
            return None

    @classmethod
    def group_id_by_project_id(cls, project_id):
        query = ("""
            SELECT group_id FROM project WHERE id = %s
        """)
        cls.source.execute(query, (project_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    # Contract
    @classmethod
    def create_contract(cls, params):
        query = ("""
            INSERT INTO project_member_contract (project_member_id, pay_rate, rate_type, currency_code_id, create_by, update_by) VALUES
            (%(project_member_id)s, %(pay_rate)s, %(rate_type)s, %(currency_code_id)s, %(author_id)s, %(author_id)s)
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[create_contract] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def create_contract_status_entry(cls, contract_id, contract_status, author_id):
        query = ("""
            INSERT INTO project_contract_status (contract_id, contract_status, update_by) VALUES
            (%s, %s, %s)
            RETURNING id                
        """)
        params = (contract_id, contract_status, author_id)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[create_contract_entry] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def get_id_by_project_member(cls, project_member_id, limit_rate_type=None):
        query = (f"""
            SELECT id
            FROM project_member_contract
            WHERE project_member_id = %s {"AND rate_type = %s" if limit_rate_type else ""}
        """)
        params = (project_member_id,) if not limit_rate_type else (
            project_member_id, limit_rate_type)
        cls.source.execute(query, params)
        cls.source.commit()
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def get_member_default_rate(cls, member_id):
        query = ("""
            SELECT
                pay_rate,
                currency_code_id
            FROM member_rate
            WHERE member_id = %s
        """)
        cls.source.execute(query, (member_id,))
        if cls.source.has_results():
            for (pay_rate, currency_code_id) in cls.source.cursor:
                rate = {
                    "pay_rate": pay_rate,
                    "currency_code_id": currency_code_id
                }
                return rate

    @classmethod
    def update_member_default_rate(cls, member_id, pay_rate, currency_code_id):
        query = ("""
            UPDATE member_rate
            SET pay_rate = %s,
                currency_code_id = %s
            WHERE member_id =%s
            RETURNING member_id
        """)
        params = (pay_rate, currency_code_id, member_id)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[update_member_default_rate] TRANSACTION IDENTIFIER: {id}")
        return id
