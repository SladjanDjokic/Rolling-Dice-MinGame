-- ------------------------------------------------------------------------------
-- Table:        member_profile
-- Description:  contains profile and settings preference
-- ------------------------------------------------------------------------------

CREATE TYPE unit_of_measure_type AS ENUM ('imperial', 'metric');
CREATE TYPE event_date_format AS ENUM ('MM/DD/YYYY', 'MM/DD/YY', 'YYYY/MM/DD', 'YY/MM/DD', 'DD/MM/YYYY', 'DD/MM/YY');
CREATE TYPE event_time_format AS ENUM ('AM/PM', '24Hr');
CREATE TYPE event_drag_method AS ENUM ('Drag_Normal', 'Drag_Group');
CREATE TYPE sort_order_type   AS ENUM ('FirstLast', 'LastFirst');


CREATE TABLE member_profile (

  member_id             INTEGER         NOT NULL REFERENCES member (id),

  -- Settings --

  online_status         BOOLEAN         NOT NULL DEFAULT 'Y',
  view_profile          BOOLEAN         NOT NULL DEFAULT 'Y',
  add_contact           BOOLEAN         NOT NULL DEFAULT 'Y',
  join_date             BOOLEAN         NOT NULL DEFAULT 'Y',
  login_location        BOOLEAN         NOT NULL DEFAULT 'Y',
  unit_of_measure       unit_of_measure_type NOT NULL DEFAULT 'imperial',

  -- Notifications --

  alert_message         BOOLEAN         NOT NULL DEFAULT 'Y',
  alert_contact_request BOOLEAN         NOT NULL DEFAULT 'Y',
  alert_accept_invite   BOOLEAN         NOT NULL DEFAULT 'Y',
  alert_accept_contact  BOOLEAN         NOT NULL DEFAULT 'Y',

  email_message         BOOLEAN         NOT NULL DEFAULT 'Y',
  email_adds_contact    BOOLEAN         NOT NULL DEFAULT 'Y',
  email_accept_invite   BOOLEAN         NOT NULL DEFAULT 'Y',
  email_accept_contact  BOOLEAN         NOT NULL DEFAULT 'Y',

  email_info_requests   BOOLEAN         NOT NULL DEFAULT 'Y',
  email_events          BOOLEAN         NOT NULL DEFAULT 'Y',
  email_new_features    BOOLEAN         NOT NULL DEFAULT 'Y',
  email_promotions      BOOLEAN         NOT NULL DEFAULT 'Y',

  -- Calendar --

  date_format           event_date_format NOT NULL DEFAULT 'MM/DD/YYYY',
  time_format           event_time_format NOT NULL DEFAULT 'AM/PM',
  start_time            TIME              NOT NULL DEFAULT '8:00',
  time_interval         INTEGER           NOT NULL DEFAULT 1,
  start_day             INTEGER           NOT NULL DEFAULT 1,
  drag_method           event_drag_method NOT NULL DEFAULT 'Drag_Normal',

  -- Security --

  picture_pin           BOOLEAN         NOT NULL DEFAULT 'N',
  security_questions    BOOLEAN         NOT NULL DEFAULT 'Y',
  cell_phone_auth       BOOLEAN         NOT NULL DEFAULT 'N',

  -- Other --

  profile_picture_storage_id INT REFERENCES file_storage_engine (id),
  biography             VARCHAR(512)    NULL,
  contact_sort_order    sort_order_type NOT NULL DEFAULT 'FirstLast',
  update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (member_id)

);

COMMENT ON TABLE member_profile IS 'Profile & Settings preferences';

COMMENT ON COLUMN member_profile.member_id       IS 'Unique Member who has these settings';
COMMENT ON COLUMN member_profile.online_status   IS 'Show your online status';
COMMENT ON COLUMN member_profile.view_profile    IS 'Show when you view a profile';
COMMENT ON COLUMN member_profile.add_contact     IS 'Show when you add a contact';
COMMENT ON COLUMN member_profile.join_date       IS 'Show your join date';
COMMENT ON COLUMN member_profile.login_location  IS 'Show your recent login location';
COMMENT ON COLUMN member_profile.unit_of_measure IS 'Member prefered unit of measure';

COMMENT ON COLUMN member_profile.alert_message   IS 'In-App Alert when receive Voice, Video, or Text msg';
COMMENT ON COLUMN member_profile.alert_contact_request IS 'In-App Alert when requested as contact';
COMMENT ON COLUMN member_profile.alert_accept_invite   IS 'In-App Alert when invitation accepted';
COMMENT ON COLUMN member_profile.alert_accept_contact  IS 'In-App Alert when contact accepted';

COMMENT ON COLUMN member_profile.email_message   IS 'Email when receive Voice, Video, or Text msg';
COMMENT ON COLUMN member_profile.email_adds_contact    IS 'Email when someone adds you as contact';
COMMENT ON COLUMN member_profile.email_accept_invite   IS 'Email when someone accepts invitation';
COMMENT ON COLUMN member_profile.email_accept_contact  IS 'Email when someone accepts you as contact';

COMMENT ON COLUMN member_profile.email_info_requests   IS 'Email verifications & information requests';
COMMENT ON COLUMN member_profile.email_events          IS 'Email upcoming events';
COMMENT ON COLUMN member_profile.email_new_features    IS 'Email new features & software updates';
COMMENT ON COLUMN member_profile.email_promotions      IS 'Email promotions & other offers';

COMMENT ON COLUMN member_profile.date_format           IS 'Format to display dates';
COMMENT ON COLUMN member_profile.time_format           IS 'Format to display time';
COMMENT ON COLUMN member_profile.start_time            IS 'Time of day to start calendar';
COMMENT ON COLUMN member_profile.time_interval         IS 'Calendar display interval';
COMMENT ON COLUMN member_profile.start_day             IS 'Day of week to start calendar';
COMMENT ON COLUMN member_profile.drag_method           IS 'Drag and drop method';

COMMENT ON COLUMN member_profile.picture_pin           IS 'Use Picture & PIN Authentication';
COMMENT ON COLUMN member_profile.security_questions    IS 'Use Questions to recover Username & Password';
COMMENT ON COLUMN member_profile.cell_phone_auth       IS 'Use Cell Phone Authentication';

COMMENT ON COLUMN member_profile.profile_picture_storage_id IS 'Reference to id in file storage table';
COMMENT ON COLUMN member_profile.biography             IS 'Member biography';
COMMENT ON COLUMN member_profile.contact_sort_order    IS 'Display contact by First Name or Last Name';
COMMENT ON COLUMN member_profile.update_date           IS 'When record was last updated';