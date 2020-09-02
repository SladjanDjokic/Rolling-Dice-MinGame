ALTER TABLE member
   ADD COLUMN middle_name  VARCHAR(64) NULL,
   ADD COLUMN company_name VARCHAR(100) NULL,
   ADD COLUMN job_title_id INT REFERENCES job_title (id) NULL;