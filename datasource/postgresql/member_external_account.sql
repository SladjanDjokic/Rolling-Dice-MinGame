-- ------------------------------------------------------------------------------
-- Table:        member_external_account
-- Description:  contains external connections outside amera
-- ------------------------------------------------------------------------------
CREATE TYPE external_account_type AS ENUM ('github','microsoft','salesforce','trello');
CREATE TABLE member_external_account (
    id                    SERIAL                 PRIMARY KEY,
    member_id             INTEGER                NOT NULL REFERENCES member (id),
    external_account      external_account_type  NOT NULL,
    external_username     VARCHAR(100),
    external_email        VARCHAR(100),
    profile_link          VARCHAR(255),
    company               VARCHAR(100),
    scope                 JSONB,
    token                 VARCHAR(255),

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX member_external_account_member_id_idx ON member_external_account (member_id);
