-- ------------------------------------------------------------------------------
-- Table:        news_topic
-- Description:  the news feed subjects/topics
-- ------------------------------------------------------------------------------
CREATE TYPE news_content_status AS ENUM ('active','inactive','complete','suspend','delete');

CREATE TABLE news_topic (

    id                    SERIAL          PRIMARY KEY,
    member_id             INTEGER         NOT NULL REFERENCES member (id),

    topic_title           VARCHAR(100),
    topic_content         TEXT,
    topic_status          news_content_status    DEFAULT 'active',

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX news_topic_member_id_idx ON news_topic (member_id);


-- ------------------------------------------------------------------------------
-- Table:        news_post 
-- Description:  contains posts for a given news feed topic.
--               parent_post_id is the comment/post to which the post is attached.
--               parent_post_id is null when attached to original topic.
-- ------------------------------------------------------------------------------

CREATE TABLE news_post (
    id                    SERIAL          PRIMARY KEY,
    news_topic_id         INTEGER         NOT NULL REFERENCES news_topic (id),  
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    post_content          TEXT,
    post_status           news_content_status    DEFAULT 'active',

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX news_post_news_topic_id_idx ON news_post (news_topic_id);
CREATE INDEX news_post_member_id_idx      ON news_post (member_id);


-- ------------------------------------------------------------------------------
-- Table:        news_media
-- Description:  contains media attached to a topic or post.  
--               news_post_id is null when media is attached to topic.
-- ------------------------------------------------------------------------------

CREATE TABLE news_media (

    id                    SERIAL          PRIMARY KEY,
    news_topic_id         INTEGER         NOT NULL REFERENCES news_topic (id),
    news_post_id          INTEGER         REFERENCES news_post (id),  
    news_file_id          INTEGER         NOT NULL REFERENCES file_storage_engine (id),

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX news_media_topic_id_idx ON news_media (news_topic_id);
CREATE INDEX news_media_post_id_idx  ON news_media (news_post_id);


--<eof>--
