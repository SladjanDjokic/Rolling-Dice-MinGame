CREATE UNIQUE INDEX member_page_settings_member_id_page_type_idx ON member_page_settings (member_id, page_type);
ALTER TYPE event_types ADD VALUE 'Breakfast';
ALTER TYPE event_types ADD VALUE 'Lunch';
ALTER TYPE event_types ADD VALUE 'Dinner';
ALTER TYPE event_types ADD VALUE 'Party';