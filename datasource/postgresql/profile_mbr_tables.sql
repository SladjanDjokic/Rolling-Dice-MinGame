----------------------------------
-- Profile Jobs : Member tables --
----------------------------------

-- ---------------------------------------------------------------------------------------
-- Table:        member_education 
-- Description:  contains the education information for a member
-- ---------------------------------------------------------------------------------------

CREATE TABLE member_education (

    id                    SERIAL          PRIMARY KEY,
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    school_name           VARCHAR(100)    NOT NULL,
    school_location       VARCHAR(256),                        -- city/state/country, etc.
    degree                VARCHAR(100),                        -- BS, MS, etc.
    field_of_study        VARCHAR(100),                        -- Computer Science
    start_date            DATE            NOT NULL,
    end_date              DATE,
    activity_text         TEXT,                                -- activities/fraternities/societies

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX member_education_member_id_idx ON member_education (member_id);


-- ---------------------------------------------------------------------------------------
-- Table:        member_workhistory
-- Description:  contains the previous employment of a member
-- ---------------------------------------------------------------------------------------

CREATE TYPE workhistory_employment_type AS ENUM ('full-time', 'part-time', 'self-employeed', 'contract', 
	                                         'freelance', 'internship', 'apprenticeship', 'seasonal');
CREATE TABLE member_workhistory (

    id                    SERIAL          PRIMARY KEY,
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    job_title             VARCHAR(100)    NOT NULL,
    employment_type       workhistory_employment_type   NOT NULL,
    company_id            INTEGER         REFERENCES company (id), -- if in our system
    company_name          VARCHAR(100),
    company_location      VARCHAR(256),                            -- city/state/country, etc.
    start_date            DATE            NOT NULL,
    end_date              DATE,

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX member_workhistory_member_id_idx ON member_workhistory (member_id);



---------------------------------------------------------------------------------------------------
-----------------------------------------------------
--       \/  Related to Profile_ tables   \/       --
-----------------------------------------------------

-- ---------------------------------------------------------------------------------------
-- Table:        member_skill
-- Description:  contains the skills a member possesses; relates to profile_skill.
-- ---------------------------------------------------------------------------------------

CREATE TABLE member_skill (

    member_id             INTEGER         NOT NULL REFERENCES member (id),
    profile_skill_id      INTEGER         NOT NULL REFERENCES profile_skill (id)
);
CREATE INDEX member_skill_member_id_idx ON member_skill (member_id);


-- ---------------------------------------------------------------------------------------
-- Table:        member_tool
-- Description:  contains the tools a member possesses; relates to profile_tool.
-- ---------------------------------------------------------------------------------------

CREATE TABLE member_tool (

    member_id             INTEGER         NOT NULL REFERENCES member (id),
    profile_tool_id       INTEGER         NOT NULL REFERENCES profile_tool (id)
);
CREATE INDEX member_tool_member_id_idx ON member_tool (member_id);

-- ---------------------------------------------------------------------------------------
-- Table:        member_certificate
-- Description:  contains the honors, awards and certificates a member possesses
-- ---------------------------------------------------------------------------------------

CREATE TABLE member_certificate (

    id                    SERIAL          PRIMARY KEY,
    member_id             INTEGER         NOT NULL REFERENCES member (id),
    title                 VARCHAR(100)    NOT NULL,
    description           VARCHAR(512),
    date_received         DATE            NOT NULL,

    create_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    update_date           TIMESTAMP       WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX member_certificate_member_id_idx ON member_certificate (member_id);

-- ---------------------------------------------------------------------------------------
-- Members can be in multiple industries, but only one job title per industry.
-- ---------------------------------------------------------------------------------------

ALTER TABLE member_profile ADD COLUMN profile_job_title_id  INT [];



--<eof>--
