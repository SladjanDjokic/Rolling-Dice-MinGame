-- ------------------------------------------------------------------------------
-- Table:        event_invite 
-- Description:  contains list of invited members
-- ------------------------------------------------------------------------------
CREATE TYPE confirm_status AS ENUM ('Accepted', 'Declined', 'Tentative');


CREATE TABLE event_invite (

  id                    SERIAL          PRIMARY KEY,
  event_id              INTEGER         NOT NULL REFERENCES event (id),

  invite_member_id      INTEGER         NOT NULL REFERENCES member (id),
  invite_status         confirm_status  NOT NULL DEFAULT 'Tentative',

  create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP

--  PRIMARY KEY (event_id, invite_member_id)
--
--  Unless we plan to invite the same member to an event multiple times, 
--  we can remove the serial id and use the primary key above.
);


COMMENT ON TABLE event_invite IS 'List of members invited to event';

COMMENT ON COLUMN event_invite.id                 IS 'Unique identifier for this record';
COMMENT ON COLUMN event_invite.event_id           IS 'ID of scheduled event';
COMMENT ON COLUMN event_invite.invite_member_id   IS 'Member invited to event';
COMMENT ON COLUMN event_invite.invite_status      IS 'Member confirmation status';
COMMENT ON COLUMN event_invite.create_date        IS 'When record was created';
COMMENT ON COLUMN event_invite.update_date        IS 'When record was last updated';