CREATE TYPE user_type AS ENUM ('standard', 'administrator', 'system');
ALTER TABLE member ADD COLUMN user_type user_type NOT NULL DEFAULT 'standard';

CREATE UNIQUE INDEX member_role_xref_role_id_member_id_key ON member_role_xref (role_id, member_id);