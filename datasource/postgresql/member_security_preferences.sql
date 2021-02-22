-- ------------------------------------------------------------------------------
-- Table:        member_security_preferences
-- Description:  security preferences
-- ------------------------------------------------------------------------------

CREATE TABLE member_security_preferences (

  member_id             INTEGER         NOT NULL REFERENCES member (id),

  -- Settings --

  facial_recognition         BOOLEAN         NOT NULL DEFAULT 'N',

  update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (member_id)
);