-- Fixes bad hex-color causing that would hang (!) calendar
UPDATE event_color
SET color = '#7DD8AE'
WHERE color = '#7DAE7AB';