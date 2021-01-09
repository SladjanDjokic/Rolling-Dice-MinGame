ALTER TABLE activity_trace
   ADD COLUMN topic                VARCHAR(100),
   ADD COLUMN referer_url          VARCHAR(255),
   ALTER COLUMN session_data       TYPE JSONB,
   ALTER COLUMN headers            TYPE JSONB,
   ALTER COLUMN request_params     TYPE JSONB,
   ALTER COLUMN request_url_params TYPE JSONB,
   ALTER COLUMN request_data       TYPE JSONB,
   ALTER COLUMN response           TYPE JSONB;

CREATE INDEX activity_trace_req_params_grp_idx ON activity_trace USING BTREE ((request_params->>'groupId'));
CREATE INDEX activity_trace_req_params_type_idx ON activity_trace USING BTREE ((request_params->>'type'));
CREATE INDEX activity_trace_event_type_idx ON activity_trace (event_type);
CREATE INDEX activity_trace_event_key_idx ON activity_trace (event_key);
