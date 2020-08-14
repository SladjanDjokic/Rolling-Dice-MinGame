CREATE TYPE group_exchange_option AS ENUM ('MOST_SECURE', 'VERY_SECURE', 'SECURE', 'LEAST_SECURE');

ALTER TYPE group_member_status ADD VALUE 'invited';

ALTER TABLE member_group
  ADD COLUMN picture_file_id INT NOT NULL REFERENCES file_storage_engine (id),
  ADD COLUMN pin VARCHAR(20) NOT NULL,
  ADD COLUMN exchange_option group_exchange_option DEFAULT 'LEAST_SECURE';