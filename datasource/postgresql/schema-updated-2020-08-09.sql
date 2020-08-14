CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- CREATE USER amera;
-- CREATE DATABASE ameraiot;
GRANT ALL PRIVILEGES ON DATABASE ameraiot TO amera;
-- On ameraiot database
-- GRANT ALL ON TABLES IN schema public TO amera;
-- GRANT ALL ON ALL SEQUENCES IN schema public TO amera;



-- Possible Calendar_HolidayType
CREATE TYPE calendar_holidaytype AS ENUM ('Local', 'State', 'Federal');

-- Possible Scheduler_Recurrence
CREATE TYPE scheduler_recurrence AS ENUM ('None', 'Weekly', 'Bi-Weekly', 'Monthly', 'Yearly');

-- Possible Event_ConfirmStatus
CREATE TYPE event_confirmstatus AS ENUM ('Accepted', 'Declined', 'Tentative');

-- Possible Event_Type
CREATE TYPE event_type AS ENUM ('Video', 'Audio', 'Chat');

-- Possible Scheduler_DateFormat
CREATE TYPE scheduler_dateformat AS ENUM ('MM/DD/YYYY', 'MM/DD/YY', 'YYYY/MM/DD', 'YY/MM/DD', 'DD/MM/YYYY', 'DD/MM/YY');

-- Possible Scheduler_TimeFormat
CREATE TYPE scheduler_timeformat AS ENUM ('AM/PM', '24Hr');



-- Member_Scheduler_Setting table
CREATE TABLE member_scheduler_setting (
  id SERIAL PRIMARY KEY,
  member_id INT NOT NULL REFERENCES member (id),  
  date_format scheduler_dateformat DEFAULT 'MM/DD/YYYY',
  time_format scheduler_timeformat DEFAULT 'AM/PM',
  start_time INTEGER DEFAULT 8,
  time_interval INTEGER DEFAULT 1,
  start_day INT DEFAULT 1,
  create_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Calendar_Holiday table
CREATE TABLE schedule_holiday (
  id SERIAL PRIMARY KEY,
  holiday_name VARCHAR(255) NOT NULL,
  holiday_type calendar_holidaytype DEFAULT 'Local',
  holiday_recurrence scheduler_recurrence DEFAULT 'None',
  create_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Event table
CREATE TABLE schedule_event (
  id SERIAL PRIMARY KEY,
  event_name VARCHAR(255) NOT NULL,
  event_host_member_id INT NOT NULL REFERENCES member (id),
  event_type event_type DEFAULT 'Video',
  event_datetime_start TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  event_datetime_end TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  event_location_address VARCHAR(255) NULL,
  event_location_postal  VARCHAR(60) NULL,
  event_recurrence scheduler_recurrence DEFAULT 'None',
  event_image INT NOT NULL REFERENCES member_file (id),
  create_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Event_Invite table
CREATE TABLE schedule_event_invite (
  id SERIAL PRIMARY KEY,
  event_id INT NOT NULL REFERENCES schedule_event (id),
  event_invite_to INT NOT NULL REFERENCES member (id),
  event_invite_status event_confirmstatus DEFAULT 'Tentative',
  create_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);



-- Event_Reschedule table
CREATE TABLE schedule_event_reschedule (
  id SERIAL PRIMARY KEY,
  event_id INT NOT NULL REFERENCES schedule_event (id),
  event_rescheduler_id INT NOT NULL REFERENCES member (id),
  event_new_datetime_start TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  event_new_datetime_end TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  event_new_location_address VARCHAR(255) NULL,
  event_new_location_postal  VARCHAR(60) NULL,
  event_reschedule_reason VARCHAR(255) NULL,
  event_reschedule_status event_confirmstatus DEFAULT 'Tentative',
  create_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);