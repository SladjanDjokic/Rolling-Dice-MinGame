-- ------------------------------------------------------------------------------
-- Table:        event
-- Description:  contains events scheduled by members
-- ------------------------------------------------------------------------------

CREATE TYPE event_types        AS ENUM ('Video','Audio','Chat','Meeting','Webinar','Personal');
CREATE TYPE event_status      AS ENUM ('Active','Cancel','Complete','Reschedule','Suspend');
CREATE TYPE event_recurrence  AS ENUM ('None', 'Daily', 'Weekly', 'Monthly', 'Yearly');
CREATE TYPE occurrence_type   AS ENUM ('First', 'Second', 'Third', 'Fourth', 'Last');


CREATE TABLE event (

  id                    SERIAL          PRIMARY KEY,
  name                  VARCHAR(100)    NOT NULL,
  description           VARCHAR(255)    NULL,
  host_member_id        INTEGER         NOT NULL REFERENCES member (id),
  event_type            event_types      DEFAULT 'Video',
  event_status          event_status    DEFAULT 'Active',
  duration_all_day      BOOLEAN         NOT NULL DEFAULT FALSE,
  start_datetime        TIMESTAMP(0) WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  end_datetime          TIMESTAMP(0) WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  location_address      VARCHAR(255)    NULL,
  location_postal       VARCHAR(60)     NULL,
  event_image           INTEGER         NULL REFERENCES member_file (id),

  recurrence            event_recurrence NOT NULL DEFAULT 'None',
  recr_cycle            INTEGER         NULL,
  recr_day_of_week      INTEGER         NULL,
  recr_day_of_month     INTEGER         NULL,
  recr_month_of_year    INTEGER         NULL,
  recr_occurrence_week  occurrence_type NULL,
  recr_start_date       DATE            NULL,
  recr_end_date         DATE            NULL,
  recr_max_occurrence   INTEGER         NULL,

  create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP

);


COMMENT ON TABLE event IS 'Events scheduled by members';

COMMENT ON COLUMN event.id                   IS 'Unique identifier for this record';
COMMENT ON COLUMN event.name                 IS 'Name of this event';
COMMENT ON COLUMN event.description          IS 'Description of this event';
COMMENT ON COLUMN event.host_member_id       IS 'ID of member hosting this event';
COMMENT ON COLUMN event.event_type           IS 'The type of event being scheduled';
COMMENT ON COLUMN event.event_status         IS 'Status of this event';
COMMENT ON COLUMN event.duration_all_day     IS 'Set as all day event';
COMMENT ON COLUMN event.start_datetime       IS 'When the event starts';
COMMENT ON COLUMN event.end_datetime         IS 'When the event ends';
COMMENT ON COLUMN event.location_address     IS 'Where the event will be held';
COMMENT ON COLUMN event.event_image          IS 'Image for the event';

COMMENT ON COLUMN event.recurrence           IS 'Frequency event repeats (Day,Week,Month,Year)';
COMMENT ON COLUMN event.recr_cycle           IS 'Cycle of repeat (every 1-day, 2-day, 3-day, etc)';
COMMENT ON COLUMN event.recr_day_of_week     IS 'Day of the week   [1-7]';
COMMENT ON COLUMN event.recr_day_of_month    IS 'Day of the month  [1-31]';
COMMENT ON COLUMN event.recr_month_of_year   IS 'Month of the year [1-12]';
COMMENT ON COLUMN event.recr_occurrence_week IS 'Week of repeat (First,Second,Third,Fourth,Last)';
COMMENT ON COLUMN event.recr_start_date      IS 'Range of repeat - Start Date';
COMMENT ON COLUMN event.recr_start_date      IS 'Range of repeat - End Date';
COMMENT ON COLUMN event.recr_max_occurrence  IS 'Range of repeat - Number of repeats';

COMMENT ON COLUMN event.create_date            IS 'When record was created';
COMMENT ON COLUMN event.update_date            IS 'When record was last updated';