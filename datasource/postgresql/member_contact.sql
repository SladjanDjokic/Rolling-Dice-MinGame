-- ------------------------------------------------------------------------------
-- Table:        member_contact_2
-- Description:  contains the list of contact devices availble for a member
-- Temporarily this table is named `member_contact_2` until a further update 
-- renames it back to normal
-- ------------------------------------------------------------------------------

-- Possible types of devices and ways of communicating with those devices
--
CREATE TYPE  device_types AS ENUM ('email', 'cell', 'landline', 'TDD', 'other');
CREATE TYPE  method_types AS ENUM ('text', 'html', 'sms', 'voice', 'other');

CREATE TABLE member_contact_2 (

  id                    SERIAL          PRIMARY KEY,
  member_id             INTEGER         NOT NULL REFERENCES member (id),

  description           VARCHAR(100)    NOT NULL,
  device                VARCHAR(100)    NOT NULL,
  device_type           device_types    NOT NULL DEFAULT 'email',
  device_country        INTEGER         NOT NULL,
  device_confirm_date   TIMESTAMP       WITH TIME ZONE,
  method_type           method_types    NOT NULL DEFAULT 'text',
  display_order         INTEGER         NOT NULL,
  enabled               BOOLEAN         NOT NULL DEFAULT 'Y',
  primary_contact       BOOLEAN         NOT NULL DEFAULT 'N',

  create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP

);

COMMENT ON TABLE member_contact_2 IS 'List of contacts linked to a member';

COMMENT ON COLUMN member_contact_2.id              IS 'Unique identifier for this record';
COMMENT ON COLUMN member_contact_2.member_id       IS 'Member owning this contact device';
COMMENT ON COLUMN member_contact_2.description     IS 'Member provided alias/name for this contact';
COMMENT ON COLUMN member_contact_2.device          IS 'Specific communications device (email address, phone number, etc)';
COMMENT ON COLUMN member_contact_2.device_type     IS 'Type of device (email, cell phone, land line, TDD, etc)';
COMMENT ON COLUMN member_contact_2.device_country  IS 'Country of origin; Link to country_code';
COMMENT ON COLUMN member_contact_2.device_confirm_date IS 'Timestamp when divice was confirmed';
COMMENT ON COLUMN member_contact_2.method_type     IS 'Communications method used for this device (text, html, sms, etc)';
COMMENT ON COLUMN member_contact_2.display_order   IS 'Member preferred display/usage order';
COMMENT ON COLUMN member_contact_2.enabled         IS 'Member setting to enable/disable this notification (Y/N)';
COMMENT ON COLUMN member_contact_2.primary_contact IS 'Member has designated this as the primary contact (Y/N)';
COMMENT ON COLUMN member_contact_2.create_date     IS 'When record was created';
COMMENT ON COLUMN member_contact_2.update_date     IS 'When record was last updated';

