ALTER TABLE bug_report ALTER COLUMN member_id DROP NOT NULL;
ALTER TABLE bug_report DROP CONSTRAINT bug_report_screenshot_storage_id_fkey;
SELECT bg.screenshot_storage_id, file_id INTO TEMPORARY TABLE bug_report_disconnect FROM bug_report AS bg INNER JOIN member_file AS mf ON (screenshot_storage_id = mf.id);
UPDATE bug_report SET screenshot_storage_id = brd.file_id FROM bug_report_disconnect AS brd WHERE brd.screenshot_storage_id = bug_report.screenshot_storage_id;
DELETE FROM member_file WHERE id IN (SELECT file_id FROM bug_report_disconnect);
ALTER TABLE bug_report ADD CONSTRAINT bug_report_screenshot_storage_id_fkey FOREIGN KEY (screenshot_storage_id) REFERENCES file_storage_engine (id);