-- ------------------------------------------------------------------------------
-- Table:        member_tos
-- Description:  contains members Terms Of Service information
-- ------------------------------------------------------------------------------

CREATE TABLE member_tos (

  id                    SERIAL          PRIMARY KEY,
  member_id             INTEGER         NOT NULL REFERENCES member (id),
  amera_tos_id          INTEGER         NOT NULL,
  date_signed           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  subscribe_country     INTEGER         NOT NULL DEFAULT 1,
  ip_address            VARCHAR(45)     NOT NULL,
  host_name             VARCHAR(128)    NOT NULL,

  create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP

);


COMMENT ON TABLE member_tos IS 'Member Terms Of Service Contracts';

COMMENT ON COLUMN member_tos.id                    IS 'Unique identifier for this record';
COMMENT ON COLUMN member_tos.member_id             IS 'Member attached to this contract';
COMMENT ON COLUMN member_tos.amera_tos_id          IS 'Specific Terms Of Service contract';
COMMENT ON COLUMN member_tos.date_signed           IS 'Date contract was signed';
COMMENT ON COLUMN member_tos.subscribe_country     IS 'Country of subscription';
COMMENT ON COLUMN member_tos.ip_address            IS 'IP address used when contract was signed';
COMMENT ON COLUMN member_tos.host_name             IS 'Host used when contract was signed';

COMMENT ON COLUMN member_tos.create_date           IS 'When record was created';
COMMENT ON COLUMN member_tos.update_date           IS 'When record was last updated';