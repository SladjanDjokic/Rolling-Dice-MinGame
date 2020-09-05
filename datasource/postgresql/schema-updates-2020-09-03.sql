-- ------------------------------------------------------------------------------
-- Table:        country_code
-- Description:  ISO 3166-1 Country Codes and ISO 4217 Currency Codes
--               with International Phone Dialing Digits and Top Level Domain
-- ------------------------------------------------------------------------------

CREATE TABLE country_code (

  id                    INTEGER         PRIMARY KEY,
  alpha2                VARCHAR(2)      NOT NULL,
  alpha3                VARCHAR(3)      NOT NULL,
  name                  VARCHAR(64)     NOT NULL,
  phone                 INTEGER             NULL,
  currency_code         VARCHAR(3)          NULL,
  currency_name         VARCHAR(64)         NULL,
  currency_id           INTEGER             NULL,
  currency_minor_unit   INTEGER             NULL,
  domain                VARCHAR(4)          NULL,
  display_order         INTEGER         NOT NULL DEFAULT 999

);

COMMENT ON TABLE country_code IS 'Country code and name info (ISO 3166-1, 4217)';

COMMENT ON COLUMN country_code.id             IS 'ANSI/ISO numeric country code';
COMMENT ON COLUMN country_code.alpha2         IS 'Two character country abreviation';
COMMENT ON COLUMN country_code.alpha3         IS 'Three character country abreviation';
COMMENT ON COLUMN country_code.name           IS 'Sortable name of the country';
COMMENT ON COLUMN country_code.phone          IS 'International phone country code';

COMMENT ON COLUMN country_code.currency_code  IS 'ISO 4217 alpha 3 currency code';
COMMENT ON COLUMN country_code.currency_name  IS 'Name of currency';
COMMENT ON COLUMN country_code.currency_id    IS 'Numeric ID, often country of origin id';
COMMENT ON COLUMN country_code.currency_minor_unit IS 'Number of units past the decimal';
COMMENT ON COLUMN country_code.domain         IS 'Top Level Domain for this country';
COMMENT ON COLUMN country_code.display_order  IS 'Order to display countries before alphabetically';
