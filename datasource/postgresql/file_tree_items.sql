CREATE TABLE file_tree_items (
    id            SERIAL  PRIMARY KEY,
    tree_id       INTEGER REFERENCES file_trees (id),
    -- root_id        INTEGER DEFAULT NULL,
    is_tree_root BOOLEAN DEFAULT FALSE,
    parent_id      INTEGER DEFAULT NULL,
    member_file_id INTEGER REFERENCES member_file (id) ON DELETE CASCADE DEFAULT NULL,  
    display_name   VARCHAR(255),
    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);