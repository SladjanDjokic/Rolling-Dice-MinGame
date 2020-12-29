ALTER TABLE event_2 
	ALTER COLUMN event_type DROP DEFAULT,
	ALTER COLUMN event_type
		SET DATA TYPE event_types
		USING event_type::text::event_types,
	ALTER COLUMN event_type SET DEFAULT 'Meeting',
	ALTER COLUMN event_description TYPE text,
	ADD COLUMN event_status event_status DEFAULT 'Active',
	ADD COLUMN repeat_times INTEGER DEFAULT NULL;