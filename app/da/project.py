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
                            id as project_id,
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
                            -- current owner
                            (
                                SELECT row_to_json(row) as ownership
                                FROM (
                                    SELECT 
                                        owner_id as current_owner_id,
                                        update_date as owner_since_date
                                    FROM project_owner_xref
                                    WHERE project_owner_xref.project_id = project.id 
                                    AND update_date = (
                                        SELECT max(update_date)
                                        FROM project_owner_xref
                                        WHERE project_owner_xref.project_id = project.id
                                    )
                                ) as row
                            ),
                            -- last updated
                            (
                                SELECT row_to_json(row) as updated
                                FROM (
                                    SELECT 
                                    update_by as last_updated_by_id,
                                    update_date
                                        FROM project_update
                                        WHERE project_update.project_id = project.id 
                                        AND update_date = (
                                            SELECT max(update_date)
                                            FROM project_update
                                            WHERE project_update.project_id = project.id
                                    )
                                ) as row
                            ),

                            -- Epics
                            (
                                SELECT json_agg(rows) as epics
                                FROM
                                (
                                    SELECT
                                        id as epic_id,
                                        epic_title,
                                        epic_description,
                                        update_by,
                                        update_date,
                                        -- Tremors
                                        (
                                            SELECT json_agg(rows) as tremors
                                            FROM
                                            (
                                                SELECT 
                                                    id as tremor_id,
                                                    tremor_title,
                                                    tremor_description,
                                                    update_by,
                                                    update_date,
                                                    -- Stories
                                                    (
                                                        SELECT json_agg(rows) as stories
                                                        FROM
                                                        (
                                                            SELECT 
                                                                id as story_id,
                                                                story_title,
                                                                story_description,
                                                                update_by,
                                                                update_date,
                                                                -- Tasks
                                                                (
                                                                    SELECT json_agg(rows) as tasks
                                                                    FROM
                                                                        (
                                                                            SELECT
                                                                                id as task_id,
                                                                                task_status,
                                                                                task_description,
                                                                                est_hours,
                                                                                due_date,
                                                                                update_by,
                                                                                update_date,
                                                                                project_member_id,
                                                                                -- task_time
                                                                                (
                                                                                    SELECT json_agg(rows) as task_time
                                                                                    FROM (
                                                                                        SELECT 
                                                                                            id as task_time_id,
                                                                                            summary,
                                                                                            task_time,
                                                                                            update_date,
                                                                                            update_by
                                                                                        FROM project_task_time
                                                                                        WHERE project_task_time.project_task_id = project_task.id
                                                                                    ) as rows
                                                                                ),
                                                                                -- task_comment
                                                                                (
                                                                                    SELECT json_agg(rows) as task_comments
                                                                                    FROM (
                                                                                        SELECT
                                                                                            id as task_comment_id,
                                                                                            comment,
                                                                                            update_date,
                                                                                            update_by
                                                                                        FROM project_task_comment
                                                                                        WHERE project_task_comment.project_task_id = project_task.id
                                                                                    ) as rows
                                                                                )
                                                                            FROM project_task
                                                                            WHERE project_task.project_story_id = project_story.id
                                                                        ) as rows
                                                                )
                                                            FROM project_story
                                                            WHERE project_story.project_tremor_id = project_tremor.id
                                                        ) as rows
                                                    )
                                                FROM project_tremor
                                                WHERE project_tremor.project_epic_id = project_epic.id
                                            ) as rows
                                        )                            
                                    FROM project_epic
                                    WHERE project_id = project.id
                                ) as rows
                            ),
                            start_date,
                            estimated_days,
                            update_date,
                            -- All project members
                            (
                                SELECT json_agg(rows) as project_members
                                FROM (
                                    SELECT 
                                        project_member.id as project_member_id,
                                        pay_rate,
                                        member.id as member_id,
                                        first_name,
                                        middle_name,
                                        last_name,
                                        company_name,
                                        job_title.name as title,
                                        department.name as department,
                                        file_path(file_storage_engine.storage_engine_id, '/member/file') as amera_avatar_url,
                                        pay_type,
                                        currency_id,
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
                            -- completed tasks
                            (
                                SELECT COUNT(DISTINCT project_task.id) as completed_tasks_count
                                    FROM project_task
                                LEFT JOIN project_story ON project_task.project_story_id = project_story.id
                                LEFT JOIN project_tremor ON project_story.project_tremor_id = project_tremor.id
                                LEFT JOIN project_epic ON project_tremor.project_epic_id = project_epic.id
                                WHERE project_epic.project_id = project.id AND task_status = 'complete'
                            ),
                            -- defined tasks
                            (
                                SELECT COUNT(DISTINCT project_task.id) as defined_tasks_count
                                    FROM project_task
                                LEFT JOIN project_story ON project_task.project_story_id = project_story.id
                                LEFT JOIN project_tremor ON project_story.project_tremor_id = project_tremor.id
                                LEFT JOIN project_epic ON project_tremor.project_epic_id = project_epic.id
                                WHERE project_epic.project_id = project.id AND task_status = 'define'
                            ),
                            -- cancelled tasks
                            (
                                SELECT COUNT(DISTINCT project_task.id) as cancelled_tasks_count
                                    FROM project_task
                                LEFT JOIN project_story ON project_task.project_story_id = project_story.id
                                LEFT JOIN project_tremor ON project_story.project_tremor_id = project_tremor.id
                                LEFT JOIN project_epic ON project_tremor.project_epic_id = project_epic.id
                                WHERE project_epic.project_id = project.id AND task_status = 'cancel'
                            ),
                            -- suspended tasks
                            (
                                SELECT COUNT(DISTINCT project_task.id) as suspended_tasks_count
                                    FROM project_task
                                LEFT JOIN project_story ON project_task.project_story_id = project_story.id
                                LEFT JOIN project_tremor ON project_story.project_tremor_id = project_tremor.id
                                LEFT JOIN project_epic ON project_tremor.project_epic_id = project_epic.id
                                WHERE project_epic.project_id = project.id AND task_status = 'suspend'
                            ),
                            -- in progress tasks
                            (
                                SELECT COUNT(DISTINCT project_task.id) as in_progress_tasks_count
                                    FROM project_task
                                LEFT JOIN project_story ON project_task.project_story_id = project_story.id
                                LEFT JOIN project_tremor ON project_story.project_tremor_id = project_tremor.id
                                LEFT JOIN project_epic ON project_tremor.project_epic_id = project_epic.id
                                WHERE project_epic.project_id = project.id AND task_status = 'in progress'
                            ),
                            -- not_cancelled
                            (
                                SELECT COUNT(DISTINCT project_task.id) as not_cancelled_tasks_count
                                    FROM project_task
                                LEFT JOIN project_story ON project_task.project_story_id = project_story.id
                                LEFT JOIN project_tremor ON project_story.project_tremor_id = project_tremor.id
                                LEFT JOIN project_epic ON project_tremor.project_epic_id = project_epic.id
                                WHERE project_epic.project_id = project.id AND task_status != 'cancel'
                            )
                        FROM project
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
                    id as project_id,
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
                    -- current owner
                    (
                        SELECT row_to_json(row) as ownership
                        FROM (
                            SELECT 
                                owner_id as current_owner_id,
                                update_date as owner_since_date
                            FROM project_owner_xref
                            WHERE project_owner_xref.project_id = project.id 
                            AND update_date = (
                                SELECT max(update_date)
                                FROM project_owner_xref
                                WHERE project_owner_xref.project_id = project.id
                            )
                        ) as row
                    ),
                    -- last updated
                    (
                        SELECT row_to_json(row) as updated
                        FROM (
                            SELECT 
                            update_by as last_updated_by_id,
                            update_date
                                FROM project_update
                                WHERE project_update.project_id = project.id 
                                AND update_date = (
                                    SELECT max(update_date)
                                    FROM project_update
                                    WHERE project_update.project_id = project.id
                            )
                        ) as row
                    ),

                    -- Epics
                    (
                        SELECT json_agg(rows) as epics
                        FROM
                        (
                            SELECT
                                id as epic_id,
                                epic_title,
                                epic_description,
                                update_by,
                                update_date,
                                -- Tremors
                                (
                                    SELECT json_agg(rows) as tremors
                                    FROM
                                    (
                                        SELECT 
                                            id as tremor_id,
                                            tremor_title,
                                            tremor_description,
                                            update_by,
                                            update_date,
                                            -- Stories
                                            (
                                                SELECT json_agg(rows) as stories
                                                FROM
                                                (
                                                    SELECT 
                                                        id as story_id,
                                                        story_title,
                                                        story_description,
                                                        update_by,
                                                        update_date,
                                                        -- Tasks
                                                        (
                                                            SELECT json_agg(rows) as tasks
                                                            FROM
                                                                (
                                                                    SELECT
                                                                        id as task_id,
                                                                        task_status,
                                                                        task_description,
                                                                        est_hours,
                                                                        due_date,
                                                                        update_by,
                                                                        update_date,
                                                                        project_member_id,
                                                                        -- task_time
                                                                        (
                                                                            SELECT json_agg(rows) as task_time
                                                                            FROM (
                                                                                SELECT 
                                                                                    id as task_time_id,
                                                                                    summary,
                                                                                    task_time,
                                                                                    update_date,
                                                                                    update_by
                                                                                FROM project_task_time
                                                                                WHERE project_task_time.project_task_id = project_task.id
                                                                            ) as rows
                                                                        ),
                                                                        -- task_comment
                                                                        (
                                                                            SELECT json_agg(rows) as task_comments
                                                                            FROM (
                                                                                SELECT
                                                                                    id as task_comment_id,
                                                                                    comment,
                                                                                    update_date,
                                                                                    update_by
                                                                                FROM project_task_comment
                                                                                WHERE project_task_comment.project_task_id = project_task.id
                                                                            ) as rows
                                                                        )
                                                                    FROM project_task
                                                                    WHERE project_task.project_story_id = project_story.id
                                                                ) as rows
                                                        )
                                                    FROM project_story
                                                    WHERE project_story.project_tremor_id = project_tremor.id
                                                ) as rows
                                            )
                                        FROM project_tremor
                                        WHERE project_tremor.project_epic_id = project_epic.id
                                    ) as rows
                                )                            
                            FROM project_epic
                            WHERE project_id = project.id
                        ) as rows
                    ),
                    start_date,
                    estimated_days,
                    update_date,
                    -- All project members
                    (
                        SELECT json_agg(rows) as project_members
                        FROM (
                            SELECT 
                                project_member.id as project_member_id,
                                pay_rate,
                                member.id as member_id,
                                first_name,
                                middle_name,
                                last_name,
                                company_name,
                                job_title.name as title,
                                department.name as department,
                                file_path(file_storage_engine.storage_engine_id, '/member/file') as amera_avatar_url,
                                pay_type,
                                currency_id,
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
                    -- completed tasks
                    (
                        SELECT COUNT(DISTINCT project_task.id) as completed_tasks_count
                            FROM project_task
                        LEFT JOIN project_story ON project_task.project_story_id = project_story.id
                        LEFT JOIN project_tremor ON project_story.project_tremor_id = project_tremor.id
                        LEFT JOIN project_epic ON project_tremor.project_epic_id = project_epic.id
                        WHERE project_epic.project_id = project.id AND task_status = 'complete'
                    ),
                    -- defined tasks
                    (
                        SELECT COUNT(DISTINCT project_task.id) as defined_tasks_count
                            FROM project_task
                        LEFT JOIN project_story ON project_task.project_story_id = project_story.id
                        LEFT JOIN project_tremor ON project_story.project_tremor_id = project_tremor.id
                        LEFT JOIN project_epic ON project_tremor.project_epic_id = project_epic.id
                        WHERE project_epic.project_id = project.id AND task_status = 'define'
                    ),
                    -- cancelled tasks
                    (
                        SELECT COUNT(DISTINCT project_task.id) as cancelled_tasks_count
                            FROM project_task
                        LEFT JOIN project_story ON project_task.project_story_id = project_story.id
                        LEFT JOIN project_tremor ON project_story.project_tremor_id = project_tremor.id
                        LEFT JOIN project_epic ON project_tremor.project_epic_id = project_epic.id
                        WHERE project_epic.project_id = project.id AND task_status = 'cancel'
                    ),
                    -- suspended tasks
                    (
                        SELECT COUNT(DISTINCT project_task.id) as suspended_tasks_count
                            FROM project_task
                        LEFT JOIN project_story ON project_task.project_story_id = project_story.id
                        LEFT JOIN project_tremor ON project_story.project_tremor_id = project_tremor.id
                        LEFT JOIN project_epic ON project_tremor.project_epic_id = project_epic.id
                        WHERE project_epic.project_id = project.id AND task_status = 'suspend'
                    ),
                    -- in progress tasks
                    (
                        SELECT COUNT(DISTINCT project_task.id) as in_progress_tasks_count
                            FROM project_task
                        LEFT JOIN project_story ON project_task.project_story_id = project_story.id
                        LEFT JOIN project_tremor ON project_story.project_tremor_id = project_tremor.id
                        LEFT JOIN project_epic ON project_tremor.project_epic_id = project_epic.id
                        WHERE project_epic.project_id = project.id AND task_status = 'in progress'
                    ),
                    -- not_cancelled
                    (
                        SELECT COUNT(DISTINCT project_task.id) as not_cancelled_tasks_count
                            FROM project_task
                        LEFT JOIN project_story ON project_task.project_story_id = project_story.id
                        LEFT JOIN project_tremor ON project_story.project_tremor_id = project_tremor.id
                        LEFT JOIN project_epic ON project_tremor.project_epic_id = project_epic.id
                        WHERE project_epic.project_id = project.id AND task_status != 'cancel'
                    )
                FROM project
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
            INSERT INTO project (company_id, project_title, project_type, project_description, start_date, estimated_days)
            VALUES (%(company_id)s, %(project_title)s, %(project_type)s, %(project_description)s, %(start_date)s, INTERVAL %(estimated_days)s)
            RETURNING id            
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[create_project_entry] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def create_project_member(cls, params):
        query = ("""
            INSERT INTO project_member (project_id, member_id, pay_rate, pay_type, currency_id, privileges)
            VALUES (%(project_id)s, %(member_id)s, %(pay_rate)s, %(pay_type)s, %(currency_id)s, %(privileges)s::project_privilege[])
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
            DELETE FROM project_role_xref
            WHERE project_id = %(project_id)s AND project_member_id = %(project_member_id)s AND project_role_id=%(project_role_id)s
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[delete_project_member_role] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def get_member_ids_for_project(cls, project_id):
        query = ("""
            SELECT ARRAY(
                SELECT member_id
                FROM project_member
                WHERE project_id = %s 
            ) AS member_ids
        """)
        cls.source.execute(query, (project_id,))
        if cls.source.has_results():
            return cls.source.cursor.fetchone()[0]
        return None

    @classmethod
    def delete_project_member(cls, params):
        query = ("""
            DELETE FROM project_member
            WHERE project_id = %(project_id)s AND member_id = %(member_id)s
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[delete_project_member] TRANSACTION IDENTIFIER: {id}")
        return id

    # Epic

    @classmethod
    def insert_epic(cls, params):
        query = ("""
            INSERT INTO project_epic (project_id, epic_title, epic_description, update_by)
            VALUES (%(project_id)s, %(epic_title)s, %(epic_description)s, (SELECT id FROM project_member WHERE project_id=%(project_id)s AND member_id=%(member_id)s))
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[insert_epic] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def update_epic(cls, params):
        query = ("""
            UPDATE project_epic
            SET epic_title = %(epic_title)s,
                epic_description = %(epic_description)s,
                update_by = (
                        SELECT id 
                        FROM project_member 
                        WHERE project_id= (
                            SELECT project_id
                            FROM project_epic
                            WHERE id = %(epic_id)s
                        ) AND member_id=%(member_id)s
                    )
            WHERE id = %(epic_id)s
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[update_epic] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def delete_epic(cls, epic_id):
        query = ("""
            DELETE FROM project_epic 
            WHERE id = %s
            RETURNING id
        """)
        cls.source.execute(query, (epic_id,))
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[delete_epic] TRANSACTION IDENTIFIER: {id}")
        return id

    # Tremors

    @classmethod
    def insert_tremor(cls, params):
        query = ("""
            INSERT INTO project_tremor (project_epic_id, tremor_title, tremor_description, update_by)
            VALUES (%(project_epic_id)s, %(tremor_title)s, %(tremor_description)s, (SELECT id FROM project_member WHERE project_id=%(project_id)s AND member_id=%(member_id)s))
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[insert_tremor] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def update_tremor(cls, params):
        query = ("""
            UPDATE project_tremor
            SET tremor_title = %(tremor_title)s,
                tremor_description = %(tremor_description)s,
                update_by = (
                        SELECT id 
                        FROM project_member 
                        WHERE project_id=%(project_id)s AND member_id=%(member_id)s
                    )
            WHERE id = %(tremor_id)s
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[update_tremor] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def delete_tremor(cls, tremor_id):
        query = ("""
            DELETE FROM project_tremor 
            WHERE id = %s
            RETURNING id
        """)
        cls.source.execute(query, (tremor_id,))
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[delete_tremor] TRANSACTION IDENTIFIER: {id}")
        return id

    # Story

    @classmethod
    def insert_story(cls, params):
        query = ("""
            INSERT INTO project_story (project_tremor_id, story_title, story_description, update_by)
            VALUES (%(project_tremor_id)s, %(story_title)s, %(story_description)s, (SELECT id FROM project_member WHERE project_id=%(project_id)s AND member_id=%(member_id)s))
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[insert_story] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def update_story(cls, params):
        query = ("""
            UPDATE project_story
            SET story_title = %(story_title)s,
                story_description = %(story_description)s,
                update_by = (
                        SELECT id 
                        FROM project_member 
                        WHERE project_id=%(project_id)s AND member_id=%(member_id)s
                    )
            WHERE id = %(story_id)s
            RETURNING id
        """)
        cls.source.execute(query, params)
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[update_story] TRANSACTION IDENTIFIER: {id}")
        return id

    @classmethod
    def delete_story(cls, story_id):
        query = ("""
            DELETE FROM project_story 
            WHERE id = %s
            RETURNING id
        """)
        cls.source.execute(query, (story_id,))
        cls.source.commit()
        id = cls.source.get_last_row_id()
        logger.debug(
            f"[delete_story] TRANSACTION IDENTIFIER: {id}")
        return id
