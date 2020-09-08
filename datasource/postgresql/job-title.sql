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

INSERT INTO job_title ( name ) VALUES

   ( 'Advisor'         ),
   ( 'Board Member'    ),
   ( 'Consultant'      ),
   ( 'CFO'             ),
   ( 'CIO/CTO'         ),
   ( 'CMO'             ),
   ( 'Director'        ),
   ( 'Finance'         ),
   ( 'Human Resources' ),
   ( 'IT Developer'    ),
   ( 'IT Manager'      ),
   ( 'Manager'         ),
   ( 'Marketing'       ),
   ( 'Operations'      ),
   ( 'President/CEO'   ),
   ( 'Purchasing'      ),
   ( 'Sales'           ),
   ( 'Sales Rep'       ),
   ( 'Vice President'  );


-- <eof>--