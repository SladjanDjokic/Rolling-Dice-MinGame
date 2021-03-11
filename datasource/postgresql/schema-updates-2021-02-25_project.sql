--  Groups 
ALTER TABLE project 
    ADD COLUMN group_id INTEGER REFERENCES member_group (id),
    ADD COLUMN update_by INTEGER REFERENCES project_member (id) ON DELETE CASCADE;

CREATE TYPE group_role AS ENUM ('owner', 'administrator', 'standard');

ALTER TABLE member_group_membership 
ADD COLUMN group_role group_role NOT NULL DEFAULT 'standard';


CREATE TYPE group_type AS ENUM ('contact', 'project');
ALTER TABLE member_group 
    ADD COLUMN group_type group_type NOT NULL DEFAULT 'contact',
    ALTER COLUMN group_leader_id DROP NOT NULL;

DROP TABLE project_task_time;
DROP TABLE project_task_comment;
DROP TABLE project_task;
DROP TABLE project_story;
DROP TABLE project_tremor;
DROP TABLE project_epic;
DROP TABLE project_update;
DROP TYPE project_task_status;

-- Removing pay rate from project_member
ALTER TABLE project_member
    DROP COLUMN pay_rate,
    DROP COLUMN pay_type,
    DROP COLUMN currency_id,
    ADD COLUMN is_active BOOLEAN DEFAULT FALSE;

ALTER TYPE project_privilege ADD VALUE 'reports';

-- Add member_rate tale
CREATE TABLE member_rate (
    member_id             INTEGER         NOT NULL REFERENCES member (id) PRIMARY KEY,
    pay_rate              DECIMAL(9,3),
    currency_code_id      INTEGER         NOT NULL REFERENCES currency_code (id)
);


-- ------------------------------------------------------------------------------
-- Table:        project_member_contract
-- Description:  contains the member contract for a project
-- ------------------------------------------------------------------------------
CREATE TYPE project_member_contract_status AS ENUM ('active','final','pending','suspend');
CREATE TYPE project_contract_rate_type AS ENUM ('hourly', 'fixed');

CREATE TABLE project_member_contract (
    id SERIAL PRIMARY KEY,
    project_member_id INTEGER NOT NULL REFERENCES project_member (id) ON DELETE CASCADE,
    pay_rate DECIMAL(9,3),
    rate_type project_contract_rate_type NOT NULL DEFAULT 'hourly',
    currency_code_id INTEGER NOT NULL REFERENCES currency_code (id),
    contract_status project_member_contract_status DEFAULT 'pending',
    rate_start_date DATE,
    create_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    create_by INTEGER NOT NULL REFERENCES project_member (id),
    update_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_by INTEGER NOT NULL REFERENCES project_member (id)
);

-- ------------------------------------------------------------------------------
-- Table:        project_element
-- Description:  contains the project initiatives - hierarchical details
-- ------------------------------------------------------------------------------
CREATE TYPE project_element_type AS ENUM ('epic','tremor','story','task');
CREATE TYPE project_status AS ENUM ('define','in progress','complete','cancel','suspend','delete');

CREATE TABLE project_element (
    id                    SERIAL          PRIMARY KEY,
    project_id            INTEGER         NOT NULL REFERENCES project (id) ON DELETE CASCADE,
    parent_id              INTEGER         DEFAULT NULL,
    element_type          project_element_type     NOT NULL,
    title                 VARCHAR(100),
    description           VARCHAR(512),
    -- est_hours, element_status only used if needed --
    contract_id           INTEGER         REFERENCES project_member_contract (id),
    est_hours             INTERVAL,
    est_rate              DECIMAL(12,3), -- only for fixed
    start_date            DATE,
    end_date              DATE,
    currency_code_id      INTEGER         REFERENCES currency_code (id),
    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    create_by             INTEGER         NOT NULL REFERENCES project_member (id),
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_by             INTEGER         NOT NULL REFERENCES project_member (id)
);
CREATE INDEX project_element_project_id_idx ON project_element (project_id);


-- To keep track over changes in status and move back from suspend and cancel to last active status
CREATE TABLE project_element_status (
    id                    SERIAL          PRIMARY KEY,
    project_element_id    INTEGER         REFERENCES project_element (id) ON DELETE CASCADE,
    element_status        project_status  DEFAULT 'define',
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_by             INTEGER         NOT NULL REFERENCES project_member (id)
);

-- ------------------------------------------------------------------------------
-- Table:        project_element_time
-- Description:  contains the time details for an element
-- ------------------------------------------------------------------------------
CREATE TABLE project_element_time (
    id                    SERIAL          PRIMARY KEY,
    project_element_id    INTEGER         NOT NULL REFERENCES project_element (id) ON DELETE CASCADE,
    element_summary       VARCHAR(512),
    element_time          INTERVAL,
    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    create_by             INTEGER         NOT NULL REFERENCES project_member (id),
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_by             INTEGER         NOT NULL REFERENCES project_member (id)
);
CREATE INDEX project_element_time_project_element_id_idx ON project_element_time (project_element_id);
-- ------------------------------------------------------------------------------
-- Table:        project_element_note
-- Description:  contains the notes and comments for an element
-- ------------------------------------------------------------------------------
CREATE TABLE project_element_note (
    id                    SERIAL          PRIMARY KEY,
    project_element_id    INTEGER         NOT NULL REFERENCES project_element (id) ON DELETE CASCADE,
    element_note          VARCHAR(512),
    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    create_by             INTEGER         NOT NULL REFERENCES project_member (id),
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_by             INTEGER         NOT NULL REFERENCES project_member (id)
);
CREATE INDEX project_element_note_project_element_id_idx ON project_element_note (project_element_id);

