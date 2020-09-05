CREATE TABLE cell_token (
-- Cell phone verification
    id SERIAL PRIMARY KEY,
    cell_phone VARCHAR(100) NULL,
    token VARCHAR(100) NULL,
    time TIMESTAMP NOT NULL,
    sms_sid VARCHAR(100) NULL
)