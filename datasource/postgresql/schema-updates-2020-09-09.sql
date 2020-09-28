ALTER TYPE event_type ADD VALUE 'Meeting';

ALTER TYPE scheduler_recurrence ADD VALUE 'Daily';

ALTER TABLE schedule_event
    ALTER COLUMN event_datetime_end DROP NOT NULL,
    ADD COLUMN event_duration_all_day BOOLEAN DEFAULT FALSE;