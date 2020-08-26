CREATE TYPE group_status AS ENUM ('active', 'deleted', 'disabled');

ALTER TABLE member_group
  ADD status group_status DEFAULT 'active';