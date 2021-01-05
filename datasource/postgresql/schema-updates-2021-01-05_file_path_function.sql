-- ------------------------------------------------------------------------------
-- Function:     file_path
-- Description:  extracts filename from end of first string and adds to end
--               of second string.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION file_path ( p_original_path TEXT,
                                       p_new_dirctory  TEXT )
  RETURNS TEXT AS $r_file_path$
  DECLARE
    file_name           VARCHAR(100);
  BEGIN
    file_name := regexp_replace( p_original_path, '.+/','');
    RETURN  p_new_dirctory || '/' || file_name;
  END;
$r_file_path$
LANGUAGE plpgsql;