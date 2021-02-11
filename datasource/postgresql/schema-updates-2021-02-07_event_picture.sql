ALTER TABLE file_storage_engine
    ADD COLUMN mime_type TEXT DEFAULT NULL,
    ADD COLUMN file_size_bytes BIGINT DEFAULT NULL;

ALTER TABLE event_2
    ADD COLUMN cover_attachment_id INTEGER DEFAULT NULL REFERENCES member_file (id);