ALTER TABLE member_session ALTER COLUMN status SET DEFAULT 'online';
ALTER TYPE member_session_status ADD VALUE 'disconnected';
ALTER TYPE member_session_status ADD VALUE 'expired';