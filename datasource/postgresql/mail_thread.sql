CREATE TABLE mail_thread (
    id BIGSERIAL PRIMARY KEY
);
CREATE TABLE mail_thread_item (
    mail_thread_id BIGINT NOT NULL REFERENCES mail_thread (id),
    mail_header_id BIGINT NOT NULL REFERENCES mail_header (id)
);
CREATE INDEX mail_thread_item_mail_thread_id_idx ON mail_thread_item (mail_thread_id);
CREATE INDEX mail_thread_item_mail_header_id_idx ON mail_thread_item (mail_header_id); -- this index is not needed if you use the suggestion below.

ALTER TABLE mail_xref ADD COLUMN mail_thread_id BIGINT;
