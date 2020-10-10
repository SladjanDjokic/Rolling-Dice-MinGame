-- Unset titles 

INSERT INTO job_title ( name ) VALUES ('Unset');
INSERT INTO department ( name ) VALUES ('Unset');

-- Country codes
ALTER TABLE country_code
    ADD COLUMN is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN cell_regexp VARCHAR (255) NULL;

