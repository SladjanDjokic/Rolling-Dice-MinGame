ALTER TABLE mail_header ADD COLUMN mail_thread_id BIGINT REFERENCES mail_thread (id);
ALTER TABLE mail_xref DROP COLUMN mail_thread_id;