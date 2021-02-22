-- ------------------------------------------------------------------------------
-- Table:       state_code
-- Description: This table contains state and province names and abbreviations
-- ------------------------------------------------------------------------------

CREATE TABLE state_code (

  id                    SERIAL                  PRIMARY KEY,
  country_code_id       INTEGER REFERENCES country_code (id) NOT NULL,
  short_name            VARCHAR(4)              NOT NULL,
  name                  VARCHAR(64)             NOT NULL

);
CREATE INDEX state_code_country_code_id_idx ON state_code (country_code_id);

