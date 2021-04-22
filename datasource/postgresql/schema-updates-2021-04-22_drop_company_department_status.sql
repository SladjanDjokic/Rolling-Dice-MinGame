ALTER TABLE company_member_status
    DROP CONSTRAINT company_member_status_company_department_id_fkey;

ALTER TABLE company_member_status
    ADD CONSTRAINT company_member_status_company_department_id_fkey 
    FOREIGN KEY (company_department_id) 
    REFERENCES company_department (id)
    ON DELETE CASCADE;