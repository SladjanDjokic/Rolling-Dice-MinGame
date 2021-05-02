ALTER TYPE location_types ADD VALUE 'bars_restraunts';
ALTER TYPE location_types ADD VALUE 'coffee_shops';
ALTER TYPE location_types ADD VALUE 'meeting_place';

ALTER TABLE location
    ADD COLUMN raw_response JSON DEFAULT NULL;