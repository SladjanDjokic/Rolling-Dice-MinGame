ALTER TABLE member
    ADD COLUMN department_id INT REFERENCES department (id) NULL,
    ADD COLUMN pin VARCHAR(20) NULL;

-- Required since these are null right after "slim" register
ALTER TABLE member_location
    ALTER street DROP NOT NULL,
    ALTER city DROP NOT NULL;