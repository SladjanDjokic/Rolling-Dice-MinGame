ALTER TABLE member
    ADD COLUMN department_id INT REFERENCES department (id) NULL;