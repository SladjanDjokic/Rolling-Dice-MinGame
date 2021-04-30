-- ------------------------------------------------------------------------------
-- Table:        location
-- Description:  contains the locations stored in the system.
-- ------------------------------------------------------------------------------
CREATE TYPE map_vendors    AS ENUM ('google', 'mapquest', 'bing');

CREATE TABLE location (

    id                    SERIAL          PRIMARY KEY,

    country_code_id       INTEGER         NOT NULL REFERENCES country_code (id),
    admin_area_1          VARCHAR(100)    NULL,         -- state/province/district/region
    admin_area_2          VARCHAR(100)    NULL,         -- county/region/ - secondary to area 1
    locality              VARCHAR(100)    NULL,         -- city/town
    sub_locality          VARCHAR(100)    NULL,         -- village/hamlet/neighborhood
    street_address_1      VARCHAR(100)    NULL,
    street_address_2      VARCHAR(100)    NULL,
    postal_code           VARCHAR(60)     NULL, 
    vendor_formatted_address VARCHAR(255)    NULL,

    latitude              FLOAT,
    longitude             FLOAT,
    map_vendor            map_vendors,
    map_link              VARCHAR(8000),
    place_id              TEXT,     

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);


-- ------------------------------------------------------------------------------
-- Table:        location_data_labels
-- Description:  contains the label for the data held in each column of the
--               location table by country.
-- ------------------------------------------------------------------------------
CREATE TABLE location_data_labels (

    country_code_id       INTEGER        NOT NULL REFERENCES country_code (id),
    admin_area_1          VARCHAR(20)    NULL, 
    admin_area_2          VARCHAR(20)    NULL, 
    locality              VARCHAR(20)    NULL, 
    sub_locality          VARCHAR(20)    NULL, 
    street_address_1      VARCHAR(20)    NULL,
    street_address_2      VARCHAR(20)    NULL,
    postal_code           VARCHAR(20)    NULL, 

    PRIMARY KEY (country_code_id)
);

