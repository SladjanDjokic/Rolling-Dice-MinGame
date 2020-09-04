
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

INSERT INTO amera_tos ( status, contract_text, in_service_date, suspend_date ) VALUES 

  ( 'active', 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. In vulputate, eros sit amet imperdiet luctus, quam lorem eleifend lorem, non pretium leo enim et ante. Pellentesque facilisis tristique lorem sed maximus. Phasellus tincidunt rutrum est, non ullamcorper nisl mattis at. Donec at erat purus. Nulla tincidunt viverra volutpat. Mauris egestas neque ut ex condimentum, vitae pharetra nibh malesuada. Cras ac facilisis nunc, non maximus quam. Sed porttitor magna sed dolor pellentesque faucibus. Sed semper ac neque in pharetra. In iaculis, metus quis pellentesque ultrices, erat dui mollis dui, hendrerit pharetra massa nulla at ex. Vestibulum ac molestie massa, id sodales eros. Vestibulum eu metus condimentum, viverra arcu non, vehicula quam.
Fusce id sagittis arcu. Orci varius natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Aenean velit dui, dictum ac pulvinar et, auctor at metus. Integer ornare volutpat nibh, nec consectetur ante sagittis ac. Nullam nunc tortor, ornare auctor pretium at, venenatis sit amet nisi. Ut tempus commodo velit. Morbi vestibulum tristique justo ac laoreet. Donec vitae nisi vehicula, sagittis eros eget, posuere elit. Maecenas nulla eros, tincidunt nec justo in, maximus facilisis ligula. Donec molestie dolor vel feugiat rutrum. Vivamus eu congue urna.', CURRENT_DATE, CURRENT_DATE ),
  ( 'inactive', 'Inactive contract text', CURRENT_DATE, CURRENT_DATE ),
  ( 'deleted', 'Deleted contract text', CURRENT_DATE, CURRENT_DATE ),
  ( 'active', 'Parle france', CURRENT_DATE, CURRENT_DATE ),
  ( 'active', 'I speak Russian', CURRENT_DATE, CURRENT_DATE );


-- 
INSERT INTO amera_tos_country ( amera_tos_id, country_code_id ) VALUES
  -- Active for US
  ( 1, 840 ),
  -- Inactive for US
  ( 2, 840 ), 
  -- Deleted for US
  ( 3, 840 ),
  -- Active for France
  ( 4, 250 ),
  -- Active for Russian
  ( 5, 643 );