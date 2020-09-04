-- ------------------------------------------------------------------------------
-- Table:        country_code
-- Description:  Country name to ISO 3166-1 Country Codes
-- ------------------------------------------------------------------------------

CREATE TABLE country_code (

  id                    INTEGER         PRIMARY KEY,
  alpha2                VARCHAR(2)      NOT NULL,
  alpha3                VARCHAR(3)      NOT NULL,
  name                  VARCHAR(64)     NOT NULL,
  display_order         INTEGER         NOT NULL DEFAULT 999

);

COMMENT ON TABLE country_code IS 'Country code and name info (ISO 3166-1)';

COMMENT ON COLUMN country_code.id             IS 'ANSI/ISO 3 digit country code';
COMMENT ON COLUMN country_code.alpha2         IS 'Two character country abreviation';
COMMENT ON COLUMN country_code.alpha3         IS 'Three character country abreviation';
COMMENT ON COLUMN country_code.name           IS 'Sortable name of the country';
COMMENT ON COLUMN country_code.display_order  IS 'Order to display countries before alphabetically';