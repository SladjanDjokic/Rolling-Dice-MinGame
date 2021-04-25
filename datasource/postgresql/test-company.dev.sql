INSERT INTO file_storage_engine (storage_engine_id, storage_engine, status) VALUES
    ('https://file-testing.s3.us-east-2.amazonaws.com/hq.jpg', 'S3', 'available'),
    ('https://file-testing.s3.us-east-2.amazonaws.com/hq2.jpg', 'S3', 'available');


INSERT INTO company (logo_storage_id, email, parent_company_id,name, place_id, address_1,address_2, city, state_code_id, postal, country_code_id, main_phone, primary_url)
VALUES 
    (8,'info@megachips.com', null, 'Megachips Corporation', NULL, '1-1-1 Miyahara, Yodogawa-ku', NULL, 'Osaka',NULL,NULL, 392, '663992884', 'www.coriander.com' ),
    (9,'info@ameraiot.com',1, 'Amera IoT Inc.', NULL, '4150 Belt Line Road', NULL, 'Addison',NULL,'75001', 840, '8177980012', 'Ameraiot.com' ),
    (8,'info@jetsilk.org',null, 'Jetsilk', 'ChIJVYBZP-Oxj4ARls-qJ_G3tgM', '1600 Amphitheatre Parkway', 'Suite 616', 'Mountain View',06,94043, 840, '6667777777', 'www.jetsilk.com' ),
    (8,'mark@facebook.com',null, 'Facebook', 'ChIJNcejdWOAhYARhxkvgwjkUx8', '81 Fremont St, San Francisco, CA 94105, United States', 'Suite 2', 'San Franscisco',13,94105, 840, '61982828888', 'www.facebook.com' ),
    (8,'arigato@sony.jp',null, 'Sony', 'ChIJ5776ik-KGGARFq5gxQtNSWw', '1 Chome-7-1 Konan, Minato City, Tokyo, Japan', '24 Sony Street', 'Minato City, Tokyo',null,'108-0075', 392, '12345678', 'www.sony.jp' );

INSERT INTO company_department (company_id, department_id) VALUES
    (1, 11),
    (1, 2),
    (1, 3),
    (1, 4),
    (1, 5),
    (1, 6),
    (1, 7),
    (1, 8),
    (2, 8),
    (2, 9),
    (2, 10),
    (2, 11),
    (2, 2);

INSERT INTO company_member (company_id, member_id) VALUES
    (1, 1),
    (1, 2),
    (1, 3),
    (1, 4),
    (1, 5),
    (1, 6),
    (1, 7),
    (1, 8),
    (1, 9),
    (1, 10),
    (1, 11),
    (1, 12),
    (1, 13),
    (1, 14),
    (1, 15),
    (1, 16),
    (1, 17),
    (1, 18),
    (1, 19),
    (1, 20),
    (1, 21),
    (1, 22),
    (2, 23),
    (2, 24),
    (2, 25),
    (2, 26),
    (2, 27),
    (2, 28),
    (3, 29),
    (3, 30),
    (3, 31);

INSERT INTO company_member_status (company_member_id, company_role, company_department_id, department_status, update_date, update_by) VALUES
    (1, 'administrator', 1, 'standard', CURRENT_TIMESTAMP - INTERVAL '2 hours',1);

INSERT INTO company_member_status (company_member_id, company_role, company_department_id, department_status, update_by) VALUES
    (1, 'owner', 1, 'leader', 1),
    (2, 'standard', 1, 'standard', 1),
    (3, 'standard', 1, 'standard', 1),
    (4, 'standard', 1, 'standard', 1),
    (5, 'standard', 1, 'standard', 1),
    (6, 'standard', 2, 'standard', 1),
    (7, 'standard', 2, 'leader', 1),
    (8, 'standard', 2, 'standard', 1),
    (9, 'standard', 2, 'standard', 1),
    (10, 'standard', 3, 'standard', 1),
    (11, 'standard', 3, 'standard', 1),
    (12, 'standard', 3, 'leader', 1),
    (13, 'standard', 3, 'standard', 1),
    (14, 'standard', 3, 'standard', 1),
    (15, 'standard', 4, 'standard', 1),
    (16, 'standard', 4, 'standard', 1),
    (17, 'standard', 4, 'standard', 1),
    (18, 'standard', 4, 'leader', 1),
    (19, 'standard', 4, 'standard', 1),
    (20, 'standard', 4, 'standard', 1),
    (21, 'standard', 4, 'standard', 1),
    (22, 'standard', 4, 'standard', 1),
    -- company 2
    (23, 'owner', 10, 'standard', 1),
    (24, 'administrator', 10, 'leader', 1),
    (25, 'standard', 11, 'leader', 1),
    (26, 'standard', 11, 'standard', 1),
    (27, 'standard', 11, 'standard', 1),
    (28, 'standard', 11, 'standard', 1),
    -- company 3
    (26, 'administrator', NULL, NULL, 1),
    (27, 'owner', NULL, NULL, 1),
    (28, 'standard', NULL, NULL, 1);

INSERT INTO company_industry (company_id, industry_id) VALUES
    (1, 1),
    (1, 2),
    (1, 3),
    (2, 4),
    (2, 5);


