ALTER TABLE mail_xref
    ADD COLUMN archived         BOOLEAN         DEFAULT FALSE,
    ADD COLUMN archived_ts      TIMESTAMP       WITH TIME ZONE,
    ADD COLUMN starred          BOOLEAN         DEFAULT FALSE,
    ADD COLUMN starred_ts       TIMESTAMP       WITH TIME ZONE;
