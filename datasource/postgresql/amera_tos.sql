
-- ------------------------------------------------------------------------------
-- Table:        amera_tos
-- Description:  Amera Terms of Service contracts
-- ------------------------------------------------------------------------------

-- Possible status a contract might have
--
CREATE TYPE contract_status AS ENUM ('active', 'inactive', 'deleted');

CREATE TABLE amera_tos (

  id                    SERIAL          PRIMARY KEY,
  status                contract_status DEFAULT 'inactive',
  contract_text         TEXT            NOT NULL,
  in_service_date       DATE            NULL, 
  suspend_date          DATE            NULL,

  create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP

);


COMMENT ON TABLE amera_tos IS 'Amera Terms Of Service';

COMMENT ON COLUMN amera_tos.id              IS 'Unique identifier for this record';
COMMENT ON COLUMN amera_tos.status          IS 'Status of this contract';
COMMENT ON COLUMN amera_tos.contract_text   IS 'Text of the Terms Of Service';
COMMENT ON COLUMN amera_tos.in_service_date IS 'Date this contract became active';
COMMENT ON COLUMN amera_tos.suspend_date    IS 'Date this contract was deactivated';
COMMENT ON COLUMN amera_tos.create_date     IS 'When record was created';
COMMENT ON COLUMN amera_tos.update_date     IS 'When record was last updated';


-- ------------------------------------------------------------------------------
-- Table:        amera_tos_country
-- Description:  The countries that each Terms of Service contract applies 
-- ------------------------------------------------------------------------------

CREATE TABLE amera_tos_country (

  amera_tos_id          INTEGER         NOT NULL REFERENCES amera_tos (id),
  country_code_id       INTEGER         NOT NULL REFERENCES country_code (id),
  create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP

);

COMMENT ON TABLE amera_tos_country IS 'Countries for each Terms Of Service';

COMMENT ON COLUMN amera_tos_country.amera_tos_id    IS 'Specific Terms Of Service Contract';
COMMENT ON COLUMN amera_tos_country.country_code_id IS 'Country Code where the TOS applies';
COMMENT ON COLUMN amera_tos_country.create_date     IS 'When record was created';

