-------------------------08-15------------------------
ALTER TABLE member_scheduler_setting
  DROP COLUMN IF EXISTS id,
  ADD PRIMARY KEY (member_id);


-------------------------08-17------------------------
ALTER TABLE schedule_holiday
  ADD COLUMN IF NOT EXISTS holiday_creator_member_id INT NOT NULL REFERENCES member (id);


-------------------------08-19------------------------
-- Possible Scheduler_DragMethod
CREATE TYPE scheduler_dragmethod AS ENUM ('Drag_Normal', 'Drag_Group');

ALTER TABLE member_scheduler_setting
  ADD COLUMN IF NOT EXISTS drag_method scheduler_dragmethod DEFAULT 'Drag_Normal';


-------------------------08-20------------------------
ALTER TABLE schedule_event
  ADD COLUMN IF NOT EXISTS event_invite_to_list VARCHAR(255) NULL,
  ALTER COLUMN event_image DROP NOT NULL;