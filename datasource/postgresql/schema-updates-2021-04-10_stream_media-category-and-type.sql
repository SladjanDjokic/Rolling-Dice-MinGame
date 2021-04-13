CREATE TYPE stream_media_category AS ENUM ('streaming_now','upcoming_streams','past_streams');

ALTER TABLE stream_media
    RENAME COLUMN category TO type;

ALTER TABLE stream_media
    ADD COLUMN category stream_media_category NOT NULL;