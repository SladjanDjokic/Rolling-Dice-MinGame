DROP TABLE company_role_xref; 

ALTER TABLE company
    ADD COLUMN email VARCHAR(255) DEFAULT NULL;