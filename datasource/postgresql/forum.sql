-- ------------------------------------------------------------------------------
-- Table:        forum_topic
-- Description:  the subjects/topics for a particular group
-- ------------------------------------------------------------------------------
CREATE TYPE forum_content_status AS ENUM ('active','inactive','complete','suspend','delete');

CREATE TABLE forum_topic (

    id                    SERIAL          PRIMARY KEY,
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    group_id              INTEGER         REFERENCES member_group (id),  

    topic_title           VARCHAR(100),
    topic_content         TEXT,
    topic_status          forum_content_status    DEFAULT 'active',
    cover_image_file_id   INTEGER         REFERENCES file_storage_engine (id),

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX forum_topic_group_id_idx ON forum_topic (group_id);
CREATE INDEX forum_topic_member_id_idx ON forum_topic (member_id);


-- ------------------------------------------------------------------------------
-- Table:        forum_post 
-- Description:  contains posts for a given topic.  
--               parent_post_id is the comment/post to which the post is attached.
--               parent_post_id is null when attached to original topic.
-- ------------------------------------------------------------------------------

CREATE TABLE forum_post (
    id                    SERIAL          PRIMARY KEY,
    forum_topic_id        INTEGER         NOT NULL REFERENCES forum_topic (id),  
    parent_post_id        INTEGER         REFERENCES forum_post (id),  
    member_id             INTEGER         NOT NULL REFERENCES member (id),

    post_content          TEXT,
    post_status           forum_content_status    DEFAULT 'active',

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX forum_post_forum_topic_id_idx ON forum_post (forum_topic_id);
CREATE INDEX forum_post_parent_post_id_idx ON forum_post (parent_post_id);
CREATE INDEX forum_post_member_id_idx      ON forum_post (member_id);


-- ------------------------------------------------------------------------------
-- Table:        forum_post_like 
-- Description:  members that liked a post
-- ------------------------------------------------------------------------------

CREATE TABLE forum_post_like (

    forum_post_id         INTEGER         NOT NULL REFERENCES forum_post (id),  
    member_id             INTEGER         NOT NULL REFERENCES member (id),

    PRIMARY KEY (forum_post_id, member_id)
);


-- ------------------------------------------------------------------------------
-- Table:        forum_media
-- Description:  contains media attached to a topic or post.  
--               forum_post_id is null when media is attached to topic.
-- ------------------------------------------------------------------------------

CREATE TABLE forum_media (

    id                    SERIAL          PRIMARY KEY,
    forum_topic_id        INTEGER         NOT NULL REFERENCES forum_topic (id),
    forum_post_id         INTEGER         REFERENCES forum_post (id),  
    media_file_id        INTEGER         NOT NULL REFERENCES file_storage_engine (id),

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX forum_media_topic_id_idx ON forum_media (forum_topic_id);
CREATE INDEX forum_media_post_id_idx  ON forum_media (forum_topic_id);


--<eof>--
