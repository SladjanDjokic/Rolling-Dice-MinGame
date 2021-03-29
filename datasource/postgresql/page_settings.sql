-- ------------------------------------------------------------------------------
-- Table:        member_page_settings
-- Description:  contains the member page setting preferences
-- ------------------------------------------------------------------------------
CREATE TYPE member_page_type AS ENUM ('Contacts','Groups','Calendar','Drive','Mail');
CREATE TYPE member_view_type AS ENUM ('tile','table', 'list', 'master', 'month','week','day');

CREATE TABLE member_page_settings (
    id                    SERIAL          PRIMARY KEY,
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    page_type             member_page_type    NOT NULL, 
    view_type             member_view_type    NOT NULL, 
    page_size             INTEGER         DEFAULT 25,
    sort_order            TEXT []         DEFAULT '{}',
    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX member_page_settings_member_id_idx ON member_page_settings (member_id);
