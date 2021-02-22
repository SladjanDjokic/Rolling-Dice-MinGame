-- ------------------------------------------------------------------------------
-- Table:        project
-- Description:  projects within a company
-- ------------------------------------------------------------------------------

CREATE TYPE project_type AS ENUM ('marketing','design','software');

CREATE TABLE project(

    id                    SERIAL          PRIMARY KEY,
    company_id            INTEGER         NOT NULL REFERENCES company (id),

    project_title         VARCHAR(100),
    project_type          project_type,
    project_description   TEXT,
    -- owner_member_id       INTEGER         DEFAULT NULL REFERENCES project_member (id),
    -- created_by            INTEGER         DEFAULT NULL REFERENCES project_member (id),
    -- updated_by            INTEGER         DEFAULT NULL REFERENCES project_member (id),
    start_date            DATE,
    estimated_days        INTERVAL, 
    -- end_date              DATE,

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX project_company_id_idx ON project (company_id);

-- ------------------------------------------------------------------------------
-- Table:        project_member
-- Description:  contains the members assigned to a project
-- ------------------------------------------------------------------------------

CREATE TYPE project_pay_type AS ENUM ('hourly','weekly','monthly','yearly','fixed');
CREATE TYPE project_privilege AS ENUM ('approve', 'create', 'view', 'edit');

CREATE TABLE project_member (

    id                    SERIAL          PRIMARY KEY,
    project_id            INTEGER         NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    pay_rate              DECIMAL(12,3),
    pay_type              project_pay_type    DEFAULT 'hourly',
    currency_id           INTEGER,
    privileges            project_privilege[] DEFAULT '{view}', 

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX project_member_project_id_idx ON project_member (project_id);
CREATE INDEX project_member_member_id_idx ON project_member (member_id);

CREATE TABLE project_update (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    update_by INTEGER NOT NULL REFERENCES project_member (id) ON DELETE CASCADE,
    update_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE project_owner_xref (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    owner_id INTEGER NOT NULL REFERENCES project_member (id) ON DELETE CASCADE,
    update_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------------------------
-- Table:        project_role
-- Description:  contains the list of roles available for a project
-- ------------------------------------------------------------------------------
CREATE TABLE project_role (
    id                    SERIAL          PRIMARY KEY,
    name                  VARCHAR(50)     NOT NULL UNIQUE
);
-- --------------------------- --
-- Data Insert:  project_role  --
-- --------------------------- --
INSERT INTO project_role (name) VALUES
    ( 'Team Lead'         ),
    ( 'Designer'          ),
    ( 'Frontend Developer'),
    ( 'Backend Developer' );


-- ------------------------------------------------------------------------------
-- Table:        project_role_xref
-- Description:  contains the roles a member has within a project
-- ------------------------------------------------------------------------------

CREATE TABLE project_role_xref (

    project_id            INTEGER         NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    project_member_id     INTEGER         NOT NULL REFERENCES project_member (id) ON DELETE CASCADE,
    project_role_id       INTEGER         NOT NULL REFERENCES project_role (id) ON DELETE CASCADE,

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX project_role_xref_project_member_id_idx ON project_role_xref (project_id, project_member_id);


---------------------------------------------------------------------------------------------------------------
-- PROJECT MILESTONES --
---------------------------------------------------------------------------------------------------------------

-- ------------------------------------------------------------------------------
-- Table:        project_epic
-- Description:  contains the epics of a project
-- ------------------------------------------------------------------------------

CREATE TABLE project_epic (

    id                    SERIAL          PRIMARY KEY,
    project_id            INTEGER         NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    epic_title            VARCHAR(100),
    epic_description      VARCHAR(512),

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_by             INTEGER         NOT NULL REFERENCES project_member (id)
);
CREATE INDEX project_epic_project_id_idx ON project_epic (project_id);


-- ------------------------------------------------------------------------------
-- Table:        project_tremor
-- Description:  contains the tremors of an epic
-- ------------------------------------------------------------------------------

CREATE TABLE project_tremor (

    id                    SERIAL          PRIMARY KEY,
    project_epic_id       INTEGER         NOT NULL REFERENCES project_epic (id) ON DELETE CASCADE,
    tremor_title          VARCHAR(100),
    tremor_description    VARCHAR(512),

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_by             INTEGER         NOT NULL REFERENCES project_member (id)
);
CREATE INDEX project_tremor_project_epic_id_idx ON project_tremor (project_epic_id);


-- ------------------------------------------------------------------------------
-- Table:        project_story
-- Description:  contains the stories of a tremor
-- ------------------------------------------------------------------------------

CREATE TABLE project_story (

    id                    SERIAL          PRIMARY KEY,
    project_tremor_id     INTEGER         NOT NULL REFERENCES project_tremor (id) ON DELETE CASCADE,
    story_title           VARCHAR(100),
    story_description     VARCHAR(512),

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_by             INTEGER         NOT NULL REFERENCES project_member (id) 
);
CREATE INDEX project_story_project_tremor_id_idx ON project_story (project_tremor_id);


-- ------------------------------------------------------------------------------
-- Table:        project_task
-- Description:  contains the tasks of a story.
--               each task belongs to one project member.
-- ------------------------------------------------------------------------------

CREATE TYPE project_task_status AS ENUM ('define','in progress','complete','cancel','suspend');

CREATE TABLE project_task (

    id                    SERIAL          PRIMARY KEY,
    project_story_id      INTEGER         NOT NULL REFERENCES project_story (id) ON DELETE CASCADE,
    project_member_id     INTEGER         DEFAULT NULL REFERENCES project_member (id) ON DELETE CASCADE,
    task_status           project_task_status      DEFAULT 'define',
    task_title            VARCHAR(100),
    task_description      VARCHAR(512),
    est_hours             INTERVAL,
    due_date              DATE,

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_by             INTEGER         NOT NULL REFERENCES project_member (id)
);
CREATE INDEX project_task_project_story_id_idx ON project_task (project_story_id);
CREATE INDEX project_task_project_member_id_idx ON project_task (project_member_id);


-- ------------------------------------------------------------------------------
-- Table:        project_task_time
-- Description:  contains the time spent on a task.
-- ------------------------------------------------------------------------------

CREATE TABLE project_task_time (

    id                    SERIAL          PRIMARY KEY,
    project_task_id       INTEGER         NOT NULL REFERENCES project_task (id) ON DELETE CASCADE,
    summary               VARCHAR(512),
    task_time             INTERVAL,

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_by             INTEGER         NOT NULL REFERENCES project_member (id)
);
CREATE INDEX project_task_time_project_task_id_idx ON project_task_time (project_task_id);


-- ------------------------------------------------------------------------------
-- Table:        project_task_comment
-- Description:  contains the comments for each task.
-- ------------------------------------------------------------------------------

CREATE TABLE project_task_comment (

    id                    SERIAL          PRIMARY KEY,
    project_task_id       INTEGER         NOT NULL REFERENCES project_task (id) ON DELETE CASCADE,
    comment               VARCHAR(512),

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_by             INTEGER         NOT NULL REFERENCES project_member (id)
);
CREATE INDEX project_task_comment_project_task_id_idx ON project_task_comment (project_task_id);


--<eof>--
