CREATE TYPE contact_exchange_option AS ENUM ('MOST_SECURE', 'VERY_SECURE','SECURE', 'LEAST_SECURE', 'NO_ENCRYPTION');
CREATE TYPE contact_status AS ENUM ('active', 'inactive', 'disabled','pending', 'requested', 'declined');
CREATE TYPE contact_security_exchange_status AS ENUM ('active', 'inactive', 'disabled', 'pending', 'requested', 'declined');
ALTER TABLE contact
  ADD COLUMN status contact_status DEFAULT 'inactive',
  ADD COLUMN security_picture_storage_id INT NULL REFERENCES file_storage_engine (id),
  ADD COLUMN security_pin VARCHAR(20) NULL,
  ADD COLUMN security_exchange_option contact_exchange_option DEFAULT 'LEAST_SECURE',
  ADD COLUMN security_exchange_status contact_security_exchange_status DEFAULT 'inactive';
CREATE INDEX contact_contact_member_id_idx ON contact (contact_member_id);
CREATE UNIQUE INDEX contact_member_id_contact_member_id_key ON contact(member_id, contact_member_id);