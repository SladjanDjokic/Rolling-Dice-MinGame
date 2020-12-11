-- ------------------------------------------------------------------------------
-- Table:        department
-- Description:  List of recognized departments within a company
-- ------------------------------------------------------------------------------

CREATE TABLE department (

  id                    SERIAL          PRIMARY KEY,
  name                  VARCHAR(64)     NOT NULL

);

COMMENT ON TABLE department IS 'Departments within a company';

COMMENT ON COLUMN department.id        IS 'Numeric primary key';
COMMENT ON COLUMN department.name      IS 'Department description';


-- ------------------------------------------------------------------------------
-- Data Insert: Departments
-- ------------------------------------------------------------------------------

INSERT INTO department ( id, name ) VALUES

   ( 2, 'Accounting'             ),
   ( 3, 'Compliance'             ),
   ( 4, 'Executive'              ),
   ( 5, 'Facilities'             ),
   ( 6, 'Finance'                ),
   ( 7, 'Human Resources'        ),
   ( 8, 'Information Technology' ),
   ( 9, 'Marketing'              ),
   ( 10, 'Operations'             ),
   ( 11, 'Production'             ),
   ( 12, 'Purchasing'             ),
   ( 13, 'Research & Development' ),
   ( 14, 'Sales'                  );

-- <eof>--