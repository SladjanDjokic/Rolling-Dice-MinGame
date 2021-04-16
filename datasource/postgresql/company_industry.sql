-- ------------------------------------------------------------------------------
-- Table:        company_industry
-- Description:  contains the list of industries for a company
-- ------------------------------------------------------------------------------
CREATE TABLE company_industry (
    company_id            INTEGER         NOT NULL REFERENCES company (id),
    industry_id           INTEGER         NOT NULL REFERENCES profile_industry (id),
    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX company_industry_company_id_idx ON company_industry (company_id, industry_id);
-- ------------------------------------------------------------------------------
-- Table:        company_department
-- Description:  contains the list of departments within a company
-- ------------------------------------------------------------------------------
CREATE TABLE company_department (
    id                    SERIAL          PRIMARY KEY,
    company_id            INTEGER         NOT NULL REFERENCES company (id),
    department_id         INTEGER         NOT NULL REFERENCES department (id),
    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX company_department_company_id_idx ON company_department (company_id, department_id);
-- ------------------------------------------------------------------------------
-- Table:        company_member
-- Description:  contains the members within a company
-- ------------------------------------------------------------------------------
CREATE TABLE company_member (
    id                    SERIAL          PRIMARY KEY,
    company_id            INTEGER         NOT NULL REFERENCES company (id),
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX company_member_company_id_idx ON company_member (company_id, member_id);
CREATE INDEX company_member_member_id_idx ON company_member (member_id);
-- ------------------------------------------------------------------------------
-- Table:        company_member_status
-- Description:  contains the changes to member status, department and/or role
-- ------------------------------------------------------------------------------
CREATE TYPE member_company_status    AS ENUM ('active', 'inactive');
CREATE TYPE member_department_status AS ENUM ('leader', 'standard');
CREATE TABLE company_member_status (
    id                    SERIAL          PRIMARY KEY,
    company_member_id     INTEGER         REFERENCES company_member (id),
    company_role          company_role_type        DEFAULT 'standard',
    company_status        member_company_status    DEFAULT 'active',
    company_department_id INTEGER         REFERENCES company_department (id),
    department_status     member_department_status DEFAULT 'standard',
    update_by             INTEGER         REFERENCES member (id),
    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX company_member_status_member_id_idx ON company_member_status (company_member_id);
CREATE INDEX company_member_status_department_id_idx ON company_member_status (company_department_id);
--<eof>--