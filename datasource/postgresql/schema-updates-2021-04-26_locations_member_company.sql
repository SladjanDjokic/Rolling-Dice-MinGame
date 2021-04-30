ALTER TABLE company
    ADD COLUMN location_id INTEGER REFERENCES location (id);

ALTER TABLE company
    DROP COLUMN address_1,
    DROP COLUMN address_2,
    DROP COLUMN city,
    DROP COLUMN state_code_id,
    DROP COLUMN postal,
    DROP COLUMN state,
    DROP COLUMN province,
    DROP COLUMN place_id;

ALTER TABLE member_location
    ADD COLUMN location_id INTEGER REFERENCES location (id);

ALTER TABLE member_location
    DROP COLUMN street,
    DROP COLUMN city,
    DROP COLUMN state,
    DROP COLUMN province,
    DROP COLUMN postal,
    DROP COLUMN country,
    DROP COLUMN address_1,
    DROP COLUMN address_2,
    DROP COLUMN country_code_id,
    DROP COLUMN state_code_id;

