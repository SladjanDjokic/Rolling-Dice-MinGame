-- ------------------------------------------------------------------------------
-- Amera Email Tables
--
-- Initial development for internal email only, however, eventual external
-- communications should be anticipated.
-- ------------------------------------------------------------------------------
-- ------------------------------------------------------------------------------
-- Table:        mail_header
-- Description:  contains header information for email msg.  The subject and 
--               addresses are stored separately from body to facilitate searches
--               and filtering.  Addresses required for external email.
-- ------------------------------------------------------------------------------
CREATE TABLE mail_header (
    id                    BIGSERIAL       PRIMARY KEY,
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    subject               TEXT,
    message_to            TEXT,
    message_cc            TEXT,
    message_bcc           TEXT,
    message_from          TEXT,
    message_ts            TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    number_attachments    INTEGER         DEFAULT 0,
    message_locked        BOOLEAN         DEFAULT TRUE
);
-- ------------------------------------------------------------------------------
-- Table:        mail_body
-- Description:  contains body of email message.  member_id included to
--               facilitated unfiltered message searches (no join necessary).
-- ------------------------------------------------------------------------------
CREATE TABLE mail_body (
    mail_header_id        BIGINT          NOT NULL REFERENCES mail_header (id),
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    message               TEXT
);
-- ------------------------------------------------------------------------------
-- Table:        mail_xref
-- Description:  cross reference of mail messages to members
-- ------------------------------------------------------------------------------
CREATE TYPE recipient_type AS ENUM ('TO', 'CC', 'BCC', 'FROM');
CREATE TYPE message_type   AS ENUM ('internal', 'external');
CREATE TABLE mail_xref (
    id                    BIGSERIAL,
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    mail_header_id        BIGINT          NOT NULL REFERENCES mail_header (id),
    owner_member_id       INTEGER         NOT NULL REFERENCES member (id),
    recipient_type        recipient_type  NOT NULL,
    message_type          message_type    NOT NULL DEFAULT 'internal',
    new_mail              BOOLEAN,
    read                  BOOLEAN         DEFAULT FALSE,
    read_ts               TIMESTAMP       WITH TIME ZONE,
    deleted               BOOLEAN         DEFAULT FALSE,
    deleted_ts            TIMESTAMP       WITH TIME ZONE,
    forward               BOOLEAN         DEFAULT FALSE,
    forward_ts            TIMESTAMP       WITH TIME ZONE,
    forward_id            BIGINT,                        -- REFERENCES mail_header (id)
    replied               BOOLEAN         DEFAULT FALSE,
    replied_ts            TIMESTAMP       WITH TIME ZONE,
    replied_id            BIGINT,                        -- REFERENCES mail_header (id)
    mail_category_id      INTEGER,                       -- REFERENCES mail_category (id)
    PRIMARY KEY (id)
);
-- ------------------------------------------------------------------------------
-- Table:        mail_category
-- Description:  categories to sort email
-- ------------------------------------------------------------------------------
CREATE TABLE mail_category (
    id                    SERIAL          PRIMARY KEY,
    member_id             INTEGER,
    name                  VARCHAR(64)     NOT NULL
);
-- ------------------------------------------------------------------------------
-- Table:        mail_folder
-- Description:  folders to organize email
-- ------------------------------------------------------------------------------
CREATE TABLE mail_folder (
    id                    SERIAL          PRIMARY KEY,
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    parent_id             INTEGER,                      -- REFERENCES mail_folder (id)
    child_id              INTEGER,                      -- REFERENCES mail_folder (id)
    name                  VARCHAR(64)     NOT NULL
);
-- ------------------------------------------------------------------------------
-- Table:        mail_attachment
-- Description:  attachments to a mail message.
-- ------------------------------------------------------------------------------
CREATE TABLE mail_attachment (
    mail_header_id      BIGINT            NOT NULL REFERENCES mail_header (id),
    file_id             INTEGER           NOT NULL REFERENCES file_storage_engine (id),
    filename            VARCHAR(256),
    filesize            INTEGER,
    filetype            VARCHAR(64)
);
-- ------------------------------------------------------------------------------
-- Table:        mail_blocking
-- Description:  blocked_id is a member_id that is blocked from sending email
--               to this member.  Internal mail blocking only at present.
-- ------------------------------------------------------------------------------
CREATE TABLE mail_blocking (
    id                    SERIAL          PRIMARY KEY,
    member_id             INTEGER         NOT NULL,
    blocked_id            INTEGER         NOT NULL
);
-- ------------------------------------------------------------------------------
-- Table:        mail_folder_xref
-- Description:  middle table for many to many relation between xref and folders table
-- ------------------------------------------------------------------------------
CREATE TABLE mail_folder_xref (
    mail_xref_id      BIGINT     NOT NULL REFERENCES mail_xref(id) ON DELETE CASCADE ,
    mail_folder_id    BIGINT     NOT NULL REFERENCES mail_folder(id) ON DELETE CASCADE
);
-- ------------------------------------------------------------------------------
-- Table:        mail_setting
-- Description:  table for email settings
-- ------------------------------------------------------------------------------
CREATE TABLE mail_setting (
    member_id                   BIGINT        NOT NULL UNIQUE REFERENCES member(id) ON DELETE CASCADE ,
    default_style               JSON          NOT NULL DEFAULT '{}',
    grammar                     BOOLEAN       NOT NULL DEFAULT TRUE,
    spelling                    BOOLEAN       NOT NULL DEFAULT TRUE,
    autocorrect                 BOOLEAN       NOT NULL DEFAULT TRUE,
    reply_forward_signature     INTEGER,
    compose_signature           INTEGER,
    PRIMARY KEY (member_id)
);
-- ------------------------------------------------------------------------------
-- Table:        mail_signature
-- Description:  signature table for members mail setting
-- ------------------------------------------------------------------------------
CREATE TABLE mail_signature (
    id                  SERIAL,
    mail_setting_id     BIGINT          NOT NULL REFERENCES mail_setting(member_id) ON DELETE CASCADE ,
    name                VARCHAR(64)     NOT NULL,
    content             TEXT            NOT NULL DEFAULT '',
    PRIMARY KEY (id)
);


ALTER TABLE mail_xref
    ADD FOREIGN KEY (replied_id) REFERENCES mail_header (id) ON DELETE SET NULL ,
    ADD FOREIGN KEY (forward_id) REFERENCES mail_header (id) ON DELETE SET NULL;

ALTER TABLE mail_setting
    ADD FOREIGN KEY (reply_forward_signature) REFERENCES mail_signature(id) ON DELETE SET NULL ,
    ADD FOREIGN KEY (compose_signature) REFERENCES mail_signature(id) ON DELETE SET NULL;

CREATE INDEX mail_xref_member_id_idx ON mail_xref(member_id);
