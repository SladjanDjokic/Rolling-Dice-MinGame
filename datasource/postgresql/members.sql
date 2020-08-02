CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- CREATE USER amera;
-- CREATE DATABASE ameraiot;
GRANT ALL PRIVILEGES ON DATABASE ameraiot TO amera;
-- On ameraiot database
-- GRANT ALL ON TABLES IN schema public TO amera;
-- GRANT ALL ON ALL SEQUENCES IN schema public TO amera;


-- Possible statuses a member can have
CREATE TYPE member_status AS ENUM ('active', 'inactive', 'disabled', 'temporary');

-- Membership table
CREATE TABLE member (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) NOT NULL UNIQUE,
  email_confirmation_timestamp TIMESTAMP WITH TIME ZONE,
  create_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  update_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  username VARCHAR(255) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  status member_status DEFAULT 'inactive',
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL
);

-- Possible types of phone number and email a member can have 
CREATE TYPE phone_types AS ENUM ('cell', 'home', 'work', 'other');
CREATE TYPE email_types AS ENUM ('personal', 'home', 'work', 'other');
-- Member Contact Info Table
CREATE TABLE member_contact (
  id SERIAL PRIMARY KEY,
  member_id INT NOT NULL REFERENCES member (id),
  phone_number VARCHAR(100) NULL,
  phone_type phone_types DEFAULT 'cell',
  email VARCHAR(100) NULL,
  email_type email_types DEFAULT 'personal',
  create_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Possible types of location a member can have
CREATE TYPE location_types AS ENUM ('billing', 'home', 'work', 'other');
-- Member Location Info Table
CREATE TABLE member_location (
  id SERIAL PRIMARY KEY,
  member_id INT NOT NULL REFERENCES member (id),
  location_type location_types DEFAULT 'billing',
  street   VARCHAR(100) NOT NULL,
  city     VARCHAR(75) NOT NULL,
  state    VARCHAR(10) NULL,
  province VARCHAR(10) NULL,
  postal   VARCHAR(60) NOT NULL,
  country  VARCHAR(100) NOT NULL
);

-- Table for managing invite key codes, expirations, etc.
-- inviter_member_id here references the user doing the invite
CREATE TABLE invite (
  id SERIAL PRIMARY KEY,
  invite_key VARCHAR(255) NOT NULL UNIQUE,
  email VARCHAR(255) NOT NULL UNIQUE,
  expiration TIMESTAMP WITH TIME ZONE NOT NULL,
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  inviter_member_id INT REFERENCES member(id) NOT NULL,
  registered_member_id INT REFERENCES member(id) NULL
);

-- Role Definition Lookup table
CREATE TABLE role (
  id SERIAL PRIMARY KEY,
  name VARCHAR(50) NOT NULL UNIQUE
);

-- Cross Reference between member and Roles, optional until we add roles
CREATE TABLE member_role_xref (
  role_id INT NOT NULL REFERENCES role(id) ON DELETE CASCADE,
  member_id INT NOT NULL REFERENCES member (id) ON DELETE CASCADE
);

-- Whose online type table, maintains session information
CREATE TYPE member_session_status AS ENUM ('online', 'inactive');
CREATE TABLE member_session (
  session_id VARCHAR(255) NOT NULL PRIMARY KEY,
  member_id INT NOT NULL REFERENCES member (id),
  email VARCHAR(255) NOT NULL,
  username VARCHAR(255) NOT NULL,
  status member_session_status DEFAULT 'inactive',
  first_name VARCHAR(100) NOT NULL,
  last_name VARCHAR(100) NOT NULL,
  create_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  update_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expiration_date TIMESTAMP WITH TIME ZONE NOT NULL
);

-- file storage engine table
CREATE TABLE file_storage_engine (
  id SERIAL PRIMARY KEY,
  storage_engine_id VARCHAR(255) NOT NULL UNIQUE,
  storage_engine VARCHAR(255) NOT NULL,
  status VARCHAR(255) NOT NULL,
  create_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  update_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- member_file table
CREATE TABLE member_file (
  id SERIAL PRIMARY KEY,
  file_id INT NOT NULL REFERENCES file_storage_engine (id),
  file_name VARCHAR(255) NOT NULL,
  status VARCHAR(255) NOT NULL,
  member_id INT NOT NULL REFERENCES member (id),
  categories VARCHAR(255) NULL
);

-- shared_file table
CREATE TABLE shared_file (
  id SERIAL PRIMARY KEY,
  file_id INT NOT NULL REFERENCES file_storage_engine (id),
  shared_unique_key VARCHAR(255) NOT NULL UNIQUE,
  member_id INT NOT NULL REFERENCES member (id),
  shared_member_id INT NULL REFERENCES member (id),
  group_id VARCHAR(255) NULL,
  create_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  update_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);