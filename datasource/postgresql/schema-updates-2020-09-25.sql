ALTER TABLE invite
  ADD COLUMN role_id INT NULL REFERENCES role(id);