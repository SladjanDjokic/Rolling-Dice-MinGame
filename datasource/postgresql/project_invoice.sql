-- ------------------------------------------------------------------------------
-- Table:        project_invoice
-- Description:  contains invoice data by project element / member contract
-- ------------------------------------------------------------------------------
CREATE TYPE project_invoice_status AS ENUM ('pending','paid','canceled','reinvoiced','deleted');

CREATE TABLE project_invoice (

    id                    SERIAL          PRIMARY KEY,
    project_element_id    INTEGER         REFERENCES project_element (id), 

    inv_title             VARCHAR(100),
    inv_description       VARCHAR(512),
    inv_date              DATE            DEFAULT CURRENT_DATE,
    inv_status            project_invoice_status  DEFAULT 'pending',
    paid_date             DATE,

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    create_by             INTEGER         NOT NULL REFERENCES project_member (id),
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_by             INTEGER         NOT NULL REFERENCES project_member (id)
);
CREATE INDEX project_invoice_project_element_id_idx ON project_invoice (project_element_id);

