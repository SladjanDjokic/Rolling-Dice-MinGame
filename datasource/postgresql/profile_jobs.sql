-- -----------------------
-- TITLE:  profile jobs --
------------------------------------------------------------
-- Industry - Job Title - Certifications - Skills - Tools --
------------------------------------------------------------


-- ---------------------------------------------------------------------------------------
-- Table:        profile_industry
-- Description:  Industries supported within the member profile
-- ---------------------------------------------------------------------------------------

CREATE TABLE profile_industry(

    id                    SERIAL          PRIMARY KEY,
    name                  VARCHAR(64)     NOT NULL,
    display_status        BOOLEAN         DEFAULT TRUE
);


-- ---------------------------------------------------------------------------------------
-- Table:        profile_job_title
-- Description:  Job Titles supported within a profile industry
-- ---------------------------------------------------------------------------------------

CREATE TABLE profile_job_title(

    id                    SERIAL          PRIMARY KEY,
    profile_industry_id   INTEGER         NOT NULL REFERENCES profile_industry (id) ON DELETE CASCADE,
    name                  VARCHAR(64)     NOT NULL,
    description           VARCHAR(2048),
    certificate_info      VARCHAR(512),   -- Temporary; until profile_certificate populated
    display_status        BOOLEAN         DEFAULT TRUE
);
CREATE UNIQUE INDEX profile_job_title_industry_id_name_idx ON profile_job_title (profile_industry_id, name);


-- ---------------------------------------------------------------------------------------
-- Table:        profile_skill   
-- Description:  Skills supported within a profile industry/job title
-- ---------------------------------------------------------------------------------------

CREATE TABLE profile_skill (

    id                    SERIAL          PRIMARY KEY,
    profile_job_title_id  INTEGER         NOT NULL REFERENCES profile_job_title (id) ON DELETE CASCADE,
    name                  VARCHAR(256)    NOT NULL,
    display_status        BOOLEAN         DEFAULT TRUE
);
CREATE UNIQUE INDEX profile_skill_job_title_id_name_idx ON profile_skill (profile_job_title_id, name);


-- ---------------------------------------------------------------------------------------
-- Table:        profile_tool    
-- Description:  Tools supported within a profile industry/job title
-- ---------------------------------------------------------------------------------------

CREATE TABLE profile_tool (

    id                    SERIAL          PRIMARY KEY,
    profile_job_title_id  INTEGER         NOT NULL REFERENCES profile_job_title (id) ON DELETE CASCADE,
    name                  VARCHAR(256)    NOT NULL,
    display_status        BOOLEAN         DEFAULT TRUE
);
CREATE UNIQUE INDEX profile_tool_job_title_id_name_idx ON profile_tool (profile_job_title_id, name);


-- ---------------------------------------------------------------------------------------
-- Table:        profile_certificate
-- Description:  Degrees and Certificates supported within a profile industry/job title
-- ---------------------------------------------------------------------------------------

CREATE TABLE profile_certificate (

    id                    SERIAL          PRIMARY KEY,
    profile_job_title_id  INTEGER         NOT NULL REFERENCES profile_job_title (id) ON DELETE CASCADE,
    name                  VARCHAR(256)    NOT NULL,
    display_status        BOOLEAN         DEFAULT TRUE
);
CREATE UNIQUE INDEX profile_certificate_job_title_id_name_idx ON profile_certificate (profile_job_title_id, name);


--<eof>--
