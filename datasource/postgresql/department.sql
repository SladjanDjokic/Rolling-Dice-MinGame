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

INSERT INTO department ( name ) VALUES

   ( 'Not Available'          ),
   ( 'Accounting'             ),
   ( 'Compliance'             ),
   ( 'Executive'              ),
   ( 'Facilities'             ),
   ( 'Finance'                ),
   ( 'Human Resources'        ),
   ( 'Information Technology' ),
   ( 'Marketing'              ),
   ( 'Operations'             ),
   ( 'Production'             ),
   ( 'Purchasing'             ),
   ( 'Research & Development' ),
   ( 'Sales'                  );

-- <eof>--