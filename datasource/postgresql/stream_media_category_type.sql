-- ------------------------------------------------------------------------------
-- Table:        stream_media_category
-- Description:  category row on stream page
-- ------------------------------------------------------------------------------

CREATE TABLE stream_media_category (

    id                    SERIAL          PRIMARY KEY,
    name                  VARCHAR(100),

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ------------------------------------------------------------------------------
-- Table:        stream_media_type
-- Description:  type pull down on stream page
-- ------------------------------------------------------------------------------

CREATE TABLE stream_media_type (

    id                    SERIAL          PRIMARY KEY,
    name                  VARCHAR(100),

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Add type & category columns

ALTER TABLE stream_media
    ADD COLUMN type INTEGER [] NOT NULL,
    ADD COLUMN category INTEGER NOT NULL REFERENCES stream_media_category (id);

CREATE INDEX stream_media_category_idx ON stream_media (category);
CREATE INDEX stream_media_type_idx on stream_media USING GIN (type);
