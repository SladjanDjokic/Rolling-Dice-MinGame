-- Support Group events

ALTER TABLE event_2 
	ADD COLUMN group_id INTEGER REFERENCES member_group (id) DEFAULT NULL;