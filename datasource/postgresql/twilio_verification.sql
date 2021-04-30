-- ------------------------------------------------------------------------------
-- Table:        twilio_verification
-- Description:  twilio verification for outgoing caller number
-- ------------------------------------------------------------------------------

CREATE TABLE twilio_verification (

  id                    SERIAL          PRIMARY KEY,

  session_id                          VARCHAR(255) NOT NULL,

  member_id                           INT NOT NULL REFERENCES member (id),

  member_contact_id                          INT NOT NULL REFERENCES member_contact_2 (id),

  create_date                         TIMESTAMP       WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);