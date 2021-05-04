ALTER TABLE invite
    ADD COLUMN company_id INTEGER NULL REFERENCES company(id);
