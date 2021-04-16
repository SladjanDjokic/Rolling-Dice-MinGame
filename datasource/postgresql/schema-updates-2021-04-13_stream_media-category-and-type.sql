-- Remove type & category columns
ALTER TABLE stream_media
    DROP COLUMN type,
    DROP COLUMN category;

DROP TYPE stream_media_category;

