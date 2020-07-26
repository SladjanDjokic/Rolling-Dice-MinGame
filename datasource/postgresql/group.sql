CREATE TABLE member_group (
-- Member Group table
    id SERIAL PRIMARY KEY,
    group_leader_id INT NOT NULL REFERENCES member (id),
    group_name VARCHAR(255) NOT NULL,
    create_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    update_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Possible statuses a member can have in a group membership
CREATE TYPE group_member_status AS ENUM ('active', 'inactive', 'disabled', 'temporary');

-- Group Membership table
CREATE TABLE member_group_membership (
    group_id INT NOT NULL REFERENCES member_group (id),
    member_id INT NOT NULL REFERENCES member (id),
    create_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    update_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    status group_member_status DEFAULT 'inactive',
    PRIMARY KEY (group_id, member_id)
);
