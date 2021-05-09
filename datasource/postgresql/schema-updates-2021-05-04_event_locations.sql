ALTER TABLE event_2
    RENAME COLUMN location_id TO member_location_id;

ALTER TABLE event_2
    ADD COLUMN location_id INTEGER REFERENCES location (id);

ALTER TABLE event_2
    ADD COLUMN event_url VARCHAR(255) DEFAULT NULL;

ALTER TABLE event_2
    DROP COLUMN location_address;