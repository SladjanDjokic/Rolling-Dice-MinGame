-- ------------------------------------------------------------------------------
-- Table:        member_achievement
-- Description:  contains degrees, certifications, and professional awards 
-- ------------------------------------------------------------------------------

CREATE TABLE member_achievement (

  id                    SERIAL          PRIMARY KEY,
  member_id             INTEGER         NOT NULL REFERENCES member (id),

  entity                VARCHAR(64)     NOT NULL,
  description           VARCHAR(64)     NOT NULL,
  display_order         INTEGER         NOT NULL,
  update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP

);

COMMENT ON TABLE member_achievement IS 'Member degrees, certifications, and professional awards';

COMMENT ON COLUMN member_achievement.id            IS 'Unique identifier for this record';
COMMENT ON COLUMN member_achievement.member_id     IS 'Member referencing these achievements';
COMMENT ON COLUMN member_achievement.entity        IS 'The university, organization or governing boad';
COMMENT ON COLUMN member_achievement.description   IS 'The degree, certification, or award';
COMMENT ON COLUMN member_achievement.display_order IS 'Member preferred display order';
COMMENT ON COLUMN member_achievement.update_date   IS 'When record was last updated';