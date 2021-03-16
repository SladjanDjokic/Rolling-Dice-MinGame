ALTER TYPE project_member_contract_status ADD VALUE 'cancel';

ALTER TABLE project_member
    ALTER COLUMN is_active SET DEFAULT TRUE;

ALTER TABLE project_member_contract
    DROP COLUMN contract_status,
    DROP COLUMN rate_start_date;


CREATE TABLE project_contract_status (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER REFERENCES project_member_contract (id),
    contract_status project_member_contract_status DEFAULT 'pending',
    update_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_by INTEGER NOT NULL REFERENCES project_member (id)
);