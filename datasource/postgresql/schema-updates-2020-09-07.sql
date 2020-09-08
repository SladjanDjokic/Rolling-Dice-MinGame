ALTER TABLE member
   ADD COLUMN job_title_id INT REFERENCES job_title (id) NULL; 

UPDATE member
    SET job_title_id = job_title.id
    FROM job_title
    WHERE member.job_title = job_title.name;

ALTER TABLE member
    DROP COLUMN job_title;

ALTER TABLE member_location
    ALTER COLUMN state TYPE varchar(100);

ALTER TABLE member_contact_2
    ADD CONSTRAINT member_contact_2_device_country_fkey FOREIGN KEY (device_country) REFERENCES country_code (id);