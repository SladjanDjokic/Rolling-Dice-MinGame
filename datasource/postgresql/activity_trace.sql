-- noinspection SqlNoDataSourceInspectionForFile
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE TYPE activity_status AS ENUM ('started', 'ended');
CREATE TABLE activity_trace (
  id                    UUID            PRIMARY KEY  DEFAULT uuid_generate_v4(),
  event_key             UUID            DEFAULT uuid_generate_v4(),
  member_id             INTEGER         REFERENCES member(id),
  event_type            VARCHAR(100),
  url                   VARCHAR(255),
  session_key           VARCHAR(255),
  session_data          JSON            DEFAULT '{}',
  headers               JSON            DEFAULT '{}',
  request_params        JSON            DEFAULT '{}',
  request_url_params    JSON            DEFAULT '{}',
  request_data          JSON            DEFAULT '{}',
  response              JSON            DEFAULT '{}',
  http_status           VARCHAR(60),
  status                activity_status NOT NULL DEFAULT 'started',
  create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX activity_trace_member_id_idx ON activity_trace (member_id);