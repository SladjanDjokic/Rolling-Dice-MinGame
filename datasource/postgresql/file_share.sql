CREATE TABLE file_share (
    id SERIAL PRIMARY KEY,
    original_node INTEGER REFERENCES file_tree_item (id) ON DELETE CASCADE,
    target_node INTEGER REFERENCES file_tree_item (id) ON DELETE CASCADE, --the file tree item created by sharing action
    create_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
)

