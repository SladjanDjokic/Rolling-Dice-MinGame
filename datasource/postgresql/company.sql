-- ------------------------------------------------------------------------------
-- Table:        company
-- Description:  list of companies and sub_companies
-- ------------------------------------------------------------------------------
CREATE TABLE company (
    id                    SERIAL          PRIMARY KEY,
    parent_company_id     INTEGER         DEFAULT NULL REFERENCES company (id),
    name                  VARCHAR(100),
    address_1             VARCHAR(64),
    address_2             VARCHAR(64),
    city                  VARCHAR(75),
    state_code_id         INTEGER,
    postal                VARCHAR(64),
    country_code_id       INTEGER,
    main_phone            VARCHAR(64),
    main_phone_ext        VARCHAR(64),
    primary_url           VARCHAR(255),
    logo_storage_id       INTEGER         DEFAULT NULL REFERENCES file_storage_engine (id),
    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX company_parent_id_idx ON company (parent_company_id);
-- ------------------------------------------------------------------------------
-- Table:        company_role_xref
-- Description:  contains the role a member has within the company.
-- ------------------------------------------------------------------------------
CREATE TYPE company_role_type AS ENUM ('standard', 'administrator', 'owner');
CREATE TABLE company_role_xref (
    company_id            INTEGER         NOT NULL REFERENCES company (id),
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    company_role          company_role_type        DEFAULT 'standard',
    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX company_role_xref_company_id_member_id_idx ON company_role_xref (company_id, member_id);
CREATE INDEX company_role_xref_member_id_idx ON company_role_xref (member_id);