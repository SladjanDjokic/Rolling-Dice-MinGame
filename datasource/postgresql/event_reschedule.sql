  
-- ------------------------------------------------------------------------------
-- Table:        event_reschedule
-- Description:  Events that have been rescheduled
-- ------------------------------------------------------------------------------

CREATE TABLE event_reschedule (

  id                    SERIAL          PRIMARY KEY,
  event_id              INTEGER         NOT NULL REFERENCES event (id),

  start_datetime        TIMESTAMP(0) WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  end_datetime          TIMESTAMP(0) WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  location_address      VARCHAR(255)    NULL,
  location_postal       VARCHAR(60)     NULL,
  reschedule_reason     VARCHAR(255)    NULL,

  create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP

);


COMMENT ON TABLE event_reschedule IS 'Events that have been rescheduled';

COMMENT ON COLUMN event_reschedule.id                 IS 'Unique identifier for this record';
COMMENT ON COLUMN event_reschedule.event_id           IS 'Unique identifier for event table';
COMMENT ON COLUMN event_reschedule.start_datetime     IS 'When the event starts';
COMMENT ON COLUMN event_reschedule.end_datetime       IS 'When the event ends';
COMMENT ON COLUMN event_reschedule.location_address   IS 'Where the event will be held';
COMMENT ON COLUMN event_reschedule.reschedule_reason  IS 'Why the event was rescheduled';

COMMENT ON COLUMN event_reschedule.create_date        IS 'When record was created';
COMMENT ON COLUMN event_reschedule.update_date        IS 'When record was last updated';