CREATE TABLE currency_code (
    id SERIAL PRIMARY KEY,
    currency_code         VARCHAR(3)          NULL,
    currency_name         VARCHAR(64)         NULL,
    currency_minor_unit   INTEGER             NULL
);

COMMENT ON COLUMN currency_code.currency_code  IS 'ISO 4217 alpha 3 currency code';
COMMENT ON COLUMN currency_code.currency_name  IS 'Name of currency';
COMMENT ON COLUMN currency_code.currency_minor_unit IS 'Number of units past the decimal';


ALTER TABLE country_code 
    DROP currency_code,
    DROP currency_name,
    DROP currency_minor_unit,
    DROP currency_id;

ALTER TABLE country_code 
    ADD COLUMN currency_code_id INTEGER REFERENCES currency_code (id);
