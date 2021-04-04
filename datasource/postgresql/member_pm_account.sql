-- ------------------------------------------------------------------------------
-- Table:        member_pm_account
-- Description:  contains members's password manager account information
-- ------------------------------------------------------------------------------

CREATE TYPE pm_website_type AS ENUM ('bank','blog/forum','company','credit card','crypto currency',
	                                 'financial service','loyalty card','social media','other');

CREATE TABLE member_pm_account (

    id                    SERIAL                 PRIMARY KEY,
    member_id             INTEGER                NOT NULL REFERENCES member (id),

    website_name          VARCHAR(100)           NOT NULL,
    website_type          pm_website_type        NOT NULL,
    website_url           VARCHAR(255), 
    website_auth_url      VARCHAR(1024), 
    website_icon          INTEGER                REFERENCES file_storage_engine (id),

    username              VARCHAR(100)           NOT NULL,
    password              VARCHAR(255)           NOT NULL,

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX member_pm_account_member_id_idx ON member_pm_account (member_id);
