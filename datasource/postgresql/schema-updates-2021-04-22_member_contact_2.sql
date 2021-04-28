ALTER TABLE member_contact_2
    ADD COLUMN is_outgoing_caller_verified BOOLEAN NULL,
    ADD COLUMN outgoing_caller BOOLEAN DEFAULT false;