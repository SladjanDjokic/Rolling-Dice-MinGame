ALTER TABLE project_element
    ADD COLUMN rate_type project_contract_rate_type NOT NULL DEFAULT 'hourly';

ALTER TYPE confirm_status ADD VALUE 'Revoked';

CREATE TABLE project_contract_invite (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER REFERENCES project_member_contract (id),
    create_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE project_contract_invite_status (
    id SERIAL PRIMARY KEY,
    project_contract_invite_id INTEGER REFERENCES project_contract_invite (id),
    invite_status confirm_status NOT NULL DEFAULT 'Tentative',
    create_by INTEGER REFERENCES project_member (id),
    create_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);