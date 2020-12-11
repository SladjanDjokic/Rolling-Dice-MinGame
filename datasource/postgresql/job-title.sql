-- ------------------------------------------------------------------------------
-- Table:        job_title     
-- Description:  List of recognized job titles within a company
-- ------------------------------------------------------------------------------

CREATE TABLE job_title (

  id                    SERIAL          PRIMARY KEY,
  name                  VARCHAR(64)     NOT NULL 

);

COMMENT ON TABLE job_title IS 'Job titles within a company';

COMMENT ON COLUMN job_title.id        IS 'Numeric primary key';
COMMENT ON COLUMN job_title.name      IS 'Job Title description';


-- ------------------------------------------------------------------------------
-- Data Insert:  Job Titles           
-- ------------------------------------------------------------------------------

INSERT INTO job_title ( id, name ) VALUES

   ( 2, 'Advisor'         ),
   ( 3, 'Board Member'    ),
   ( 4, 'Consultant'      ),
   ( 5, 'CFO'             ),
   ( 6, 'CIO/CTO'         ),
   ( 7, 'CMO'             ),
   ( 8, 'Director'        ),
   ( 9, 'Finance'         ),
   ( 10, 'Human Resources' ),
   ( 11, 'IT Developer'    ),
   ( 12, 'IT Manager'      ),
   ( 13, 'Manager'         ),
   ( 14, 'Marketing'       ),
   ( 15, 'Operations'      ),
   ( 16, 'President/CEO'   ),
   ( 17, 'Purchasing'      ),
   ( 18, 'QA Manager'      ),
   ( 19, 'Sales'           ),
   ( 20, 'Sales Rep'       ),
   ( 21, 'Vice President'  ),
   ( 43, 'Owner'  );

-- <eof>--