ALTER TABLE invite
  ADD COLUMN country_code INTEGER REFERENCES country_code (id)