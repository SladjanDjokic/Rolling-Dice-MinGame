-- Video Mail Type
CREATE TYPE video_mail_type AS ENUM ('contact', 'group', 'reply');
CREATE TYPE video_mail_status AS ENUM ('read', 'unread', 'deleted');
CREATE TYPE video_mail_media_type AS ENUM ('video', 'audio');
-- Video Mail table
CREATE TABLE video_mail (
    id SERIAL PRIMARY KEY,
    subject TEXT,
    message_from INTEGER NOT NULL REFERENCES member (id),
    group_id INTEGER REFERENCES member_group (id),
    video_storage_id INT REFERENCES file_storage_engine (id),
    type video_mail_type DEFAULT 'contact',
    media_type video_mail_media_type DEFAULT 'video',
    replied_id INT,
    create_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    update_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE video_mail_xref (
    id                    BIGSERIAL,
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    video_mail_id         INTEGER         NOT NULL REFERENCES video_mail (id),
    status                video_mail_status DEFAULT 'unread',
    create_date           TIMESTAMP       WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);
