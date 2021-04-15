-- ------------------------------------------------------------------------------
-- Table:        stream_media
-- Description:  contains streaming media available on stream page
-- ------------------------------------------------------------------------------
CREATE TYPE stream_media_status AS ENUM ('active','inactive','suspend','delete');

CREATE TABLE stream_media (

    id                    SERIAL          PRIMARY KEY,
    member_id             INTEGER         NOT NULL REFERENCES member (id),

    title                 VARCHAR(100),
    description           TEXT,
    category              TEXT [],
    duration              INTERVAL,

    stream_file_id        INTEGER         NOT NULL REFERENCES file_storage_engine (id),
    stream_status         stream_media_status    DEFAULT 'active',
    stream_start_date     DATE,
    stream_end_date       DATE,

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX stream_media_member_id_idx ON stream_media (member_id);
CREATE INDEX stream_media_stream_date_idx ON stream_media (stream_start_date, stream_end_date);