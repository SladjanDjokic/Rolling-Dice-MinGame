-- ALTER TABLE member_file
    -- ADD COLUMN file_owner INTEGER REFERENCES member (id) not null;

CREATE TYPE tree_type AS ENUM ('bin', 'main');
CREATE TABLE file_trees (
  id serial PRIMARY KEY,  
  member_id integer REFERENCES member (id),
  group_id integer REFERENCES member_group (id),
  type tree_type  
);

ALTER TABLE member_group
    ADD COLUMN main_file_tree INTEGER REFERENCES file_trees (id),
    ADD COLUMN bin_file_tree INTEGER REFERENCES file_trees (id);

ALTER TABLE member
    ADD COLUMN main_file_tree INTEGER REFERENCES file_trees (id),
    ADD COLUMN bin_file_tree INTEGER REFERENCES file_trees (id);
