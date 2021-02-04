-- ------------------------------------------------------------------------------
-- Table:        bug_report
-- Description:  contains bugs/issues reported by members
-- ------------------------------------------------------------------------------

CREATE TYPE bug_status AS ENUM ('new','assigned','deferred','rejected','duplicate', 
                            'open', 'fixed', 're-open', 're-test', 'verified', 'close' );

CREATE TABLE bug_report (
    id                    SERIAL          PRIMARY KEY,
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    description           VARCHAR(255)    NULL,
    screenshot_storage_id INTEGER         NULL REFERENCES member_file (id),
    assignee              VARCHAR(255)    NULL,
    assignee_member_id    INTEGER         NULL REFERENCES member (id),
    status                bug_status      DEFAULT 'new',
    redux_state           JSONB           DEFAULT '{}',
    browser_info          JSONB           DEFAULT '{}',
    referer_url           VARCHAR(255)    NULL,
    current_url           VARCHAR(255)    NULL,
    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);