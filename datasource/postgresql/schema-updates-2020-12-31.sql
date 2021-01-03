ALTER TABLE mail_header
    ALTER COLUMN message_to TYPE JSONB USING message_to::json,
    ALTER COLUMN message_cc TYPE JSONB USING message_cc::json,
    ALTER COLUMN message_bcc TYPE JSONB USING message_bcc::json;

ALTER TABLE mail_xref
    ADD COLUMN recent_mail_folder_id BIGINT REFERENCES mail_folder(id) DEFAULT NULL;