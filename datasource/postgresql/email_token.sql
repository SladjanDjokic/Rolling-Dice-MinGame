CREATE TABLE email_token (
-- Cell phone verification
    id SERIAL PRIMARY KEY,
    email VARCHAR(100) NULL,
    token VARCHAR(100) NULL,
    time TIMESTAMP NOT NULL
);