CREATE TABLE file_tree_item (
    id            SERIAL  PRIMARY KEY,
    file_tree_id       INTEGER REFERENCES file_tree (id),
    -- root_id        INTEGER DEFAULT NULL,
    is_tree_root BOOLEAN DEFAULT FALSE,
    parent_id      INTEGER DEFAULT NULL,
    member_file_id INTEGER REFERENCES member_file (id) ON DELETE CASCADE DEFAULT NULL,  
    display_name   VARCHAR(255),
    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);