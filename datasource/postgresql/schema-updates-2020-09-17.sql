ALTER TABLE contact
  ADD COLUMN role_id INT NULL REFERENCES role(id);


-- ------------------------------------------------------------------------------
-- Data Insert:  Role
-- ------------------------------------------------------------------------------
INSERT INTO role ( name ) VALUES

   ( 'Advisor'       ),
   ( 'Client'        ),
   ( 'Co-Worker'     ),
   ( 'Customer'      ),
   ( 'Friend'        ),
   ( 'Reseller'      ),
   ( 'Student'       ),
   ( 'Teacher'       ),
   ( 'Vendor'        ),
   ( 'Worker'        ),
   ( 'Not Available' );

-- <eof> --
