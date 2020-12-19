ALTER TABLE mail_header
    ALTER COLUMN message_to TYPE JSON USING message_to::json,
    ALTER COLUMN message_cc TYPE JSON USING message_cc::json,
    ALTER COLUMN message_bcc TYPE JSON USING message_bcc::json;

ALTER TABLE mail_signature RENAME COLUMN mail_setting_id TO member_id;