ALTER TABLE stream_media
    ADD COLUMN thumbnail INTEGER NOT NULL REFERENCES file_storage_engine (id);