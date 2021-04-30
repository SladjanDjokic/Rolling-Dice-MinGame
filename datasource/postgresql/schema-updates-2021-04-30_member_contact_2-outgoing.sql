ALTER TABLE member_contact_2
    RENAME COLUMN is_outgoing_caller_verified TO outgoing_caller_verified;
ALTER TABLE member_contact_2 
    ALTER COLUMN outgoing_caller_verified SET DEFAULT false; 