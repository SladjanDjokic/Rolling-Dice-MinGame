ALTER TABLE member_location  ADD COLUMN description  VARCHAR(100);
ALTER TABLE member_contact_2 ADD COLUMN member_location_id  INTEGER;
ALTER TABLE member_profile
   ADD COLUMN  timezone_id     INTEGER,
   ADD COLUMN  timezone_dst    BOOLEAN  NOT NULL DEFAULT FALSE;