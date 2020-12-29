CREATE TYPE event_freq  AS ENUM ('Daily', 'Weekly', 'Specific days', 'Monthly', 'Bi-monthly', 'Quarterly', 'Yearly', 'No recurrence');
CREATE TYPE end_condition AS ENUM ('End date', 'times');
CREATE TYPE event_2_types AS ENUM ('Meeting', 'Chat', 'Audio', 'Video');
CREATE TYPE event_location_types AS ENUM ('my_locations', 'lookup', 'url', 'none');

CREATE TABLE event_sequence (
  id SERIAL PRIMARY KEY,
  sequence_name VARCHAR(100)    NOT NULL,
  create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE event_2 (
  id                    SERIAL          PRIMARY KEY,
  sequence_id           INTEGER         REFERENCES event_sequence (id) DEFAULT NULL,
  event_color_id        INTEGER         REFERENCES event_color (id),
  event_name            VARCHAR(100)    NOT NULL,
  event_description     VARCHAR(255)    NULL,
  host_member_id        INTEGER         NOT NULL REFERENCES member (id),
  is_full_day           BOOLEAN         NOT NULL,

  event_tz              VARCHAR(255)    NULL,
  start_datetime        TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  end_datetime          TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

  event_type            event_2_types   DEFAULT 'Meeting',
  event_recurrence_freq event_freq      DEFAULT 'No recurrence',
  end_condition         end_condition   DEFAULT 'times',
  repeat_weekdays       VARCHAR(100)    NULL,
  end_date_datetime     TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

  location_mode         event_location_types DEFAULT 'my_locations',
  location_id           INTEGER         REFERENCES member_location (id) DEFAULT NULL,
  location_address      VARCHAR(255)    DEFAULT NULL,
  create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ------------------------------------------------------------------------------
-- Table:        post_event_media
-- Description:  contains agenda, notes, charts, documents, images, video, etc. 
-- ------------------------------------------------------------------------------
-- CREATE TYPE media_types AS ENUM ('Agenda','Notes','Chart','Document','Image','Audio','Video');

CREATE TABLE event_media (

  id                    SERIAL          PRIMARY KEY,
  event_id              INTEGER         NOT NULL REFERENCES event_2 (id),
  -- media_type            media_types     NOT NULL,
  member_file_id        INTEGER         NOT NULL REFERENCES member_file (id),

  create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX event_media_event_id_idx ON event_media (event_id); 

CREATE TABLE event_invite_2 (

  id                    SERIAL          PRIMARY KEY,
  event_id              INTEGER         NOT NULL REFERENCES event_2 (id),

  invite_member_id      INTEGER         NOT NULL REFERENCES member (id),
  invite_status         confirm_status  NOT NULL DEFAULT 'Tentative',

  create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP

);




