ALTER TABLE member
    ADD COLUMN avatar_storage_id INT REFERENCES file_storage_engine (id) NULL;