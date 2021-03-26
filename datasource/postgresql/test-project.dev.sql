INSERT INTO member_group (group_leader_id, group_name, picture_file_id, pin, exchange_option, status, main_file_tree, bin_file_tree, group_type) VALUES 
    (1, '1st project group', 1, '123456','MOST_SECURE', 'active', NULL, NULL, 'project'),
    (1, '2nd project group', 1, '123456','MOST_SECURE', 'active', NULL, NULL, 'project');

INSERT INTO member_group_membership (group_id, member_id, status, group_role) VALUES 
    (47, 1, 'active', 'owner'),
    (48, 1, 'active', 'owner');

INSERT INTO project (company_id, project_title, project_type, project_description, start_date, estimated_days, group_id)
    VALUES (1, 'Software development', 'software', 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus et diam vestibulum, lobortis ipsum quis, luctus leo. Nam at imperdiet eros, ac facilisis ante. Nullam id cursus dolor, id dapibus tellus. Ut sed arcu suscipit, placerat arcu nec, pellentesque ipsum. Vivamus dictum turpis non lectus convallis, et varius risus iaculis. Nunc non dolor volutpat, lobortis ipsum eu, cursus dui. Donec sem nibh, ornare id laoreet vel, pretium eu ligula. Donec massa tortor, sollicitudin vitae lobortis quis, lobortis quis lacus. In tempor augue bibendum euismod suscipit. Proin sodales sapien quis odio ultricies, eu faucibus nibh iaculis. Pellentesque a fermentum erat, non condimentum arcu. Nulla eu porta ante, ac malesuada ipsum. Cras molestie ullamcorper urna a elementum. Nunc quis massa urna. Ut tortor ipsum, finibus id commodo nec, tristique quis est. Suspendisse potenti.','2021-02-10', '90 days', 47),
           (1, 'Flyer design', 'marketing', 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus et diam vestibulum, lobortis ipsum quis, luctus leo. Nam at imperdiet eros, ac facilisis ante. Nullam id cursus dolor, id dapibus tellus. Ut sed arcu suscipit, placerat arcu nec, pellentesque ipsum. Vivamus dictum turpis non lectus convallis, et varius risus iaculis. Nunc non dolor volutpat, lobortis ipsum eu, cursus dui. Donec sem nibh, ornare id laoreet vel, pretium eu ligula. Donec massa tortor, sollicitudin vitae lobortis quis, lobortis quis lacus. In tempor augue bibendum euismod suscipit. Proin sodales sapien quis odio ultricies, eu faucibus nibh iaculis. Pellentesque a fermentum erat, non condimentum arcu. Nulla eu porta ante, ac malesuada ipsum. Cras molestie ullamcorper urna a elementum. Nunc quis massa urna. Ut tortor ipsum, finibus id commodo nec, tristique quis est. Suspendisse potenti.','2021-02-11', '45 days', 48);

INSERT INTO project_member (project_id, member_id, privileges)
    VALUES (1,1, '{approve, create, view, edit}'),
           (1,2, '{create, view}'),
           (1,10, '{view}'),
           (2,1, '{approve, create, view, edit}'),
           (2,2, '{create, view}'),
           (2,20,'{view}');

UPDATE project
    SET update_by = 1
    WHERE id = 1;

UPDATE project
    SET update_by = 1
    WHERE id = 2;

INSERT INTO project_owner_xref (project_id, owner_id)
    VALUES (1,1),
           (2,4);


INSERT INTO project_role_xref (project_id, project_member_id, project_role_id)
    VALUES (1, 1, 1),
           (1, 1, 4),
           (1, 2, 3),
           (1, 3, 4),
           (1, 4, 1),
           (1, 4, 2),
           (1, 5, 4),
           (1, 6, 3);

-- Epics
INSERT INTO project_element (project_id, title, parent_id, element_type, description, create_by, update_by) VALUES
    (1,'Backend design',NULL,'epic','Design the endpointes', 1,1),
    (1,'Frontend design',NULL,'epic','React front-end code', 1,1),
    (2,'Design',NULL,'epic','Get PDF designs', 1,1),
    (2,'Publishing',NULL,'epic','Print 1000 copies', 1,1);

-- Tremors
INSERT INTO project_element (project_id, title, parent_id, element_type, description, create_by, update_by) VALUES
    (1,'AWS infrastructure',1,'tremor','', 1,1),
    (1,'Fixed tremor',1,'tremor','', 1,1);

-- Stories
INSERT INTO project_element (project_id, title, parent_id, element_type, description, create_by, update_by) VALUES
    (1,'Some story',5,'story','Some cool title', 1,1),
    (1,'Another story',5,'story','Not so cool title', 1,1),
    (1,'Fixed story',5,'story','Some description', 1,1);

INSERT INTO project_member_contract (project_member_id, pay_rate, rate_type, currency_code_id, create_by, update_by) VALUES 
    (1, 40, 'hourly', 132,  1, 1),
    (2, 30, 'hourly', 132,  1, 1),
    (2, 500, 'fixed', 132,  1, 1),
    (4, 30, 'hourly', 132,  1, 1),
    (5, 25, 'hourly', 132,  1, 1),
    (6, 30, 'hourly', 132,  1, 1);

INSERT INTO project_contract_status (contract_id, contract_status, update_by, update_date) VALUES
    (1, 'pending', 1, CURRENT_TIMESTAMP - INTERVAL '3 weeks'),
    (1, 'active', 1,  CURRENT_TIMESTAMP - INTERVAL '1 weeks'),
    (2, 'pending', 1, CURRENT_TIMESTAMP - INTERVAL '3 weeks'),
    (2, 'active', 1,  CURRENT_TIMESTAMP - INTERVAL '1 weeks'),
    (3, 'pending', 1, CURRENT_TIMESTAMP - INTERVAL '3 weeks'),
    (3, 'active', 1,  CURRENT_TIMESTAMP - INTERVAL '1 weeks'),
    (4, 'pending', 1, CURRENT_TIMESTAMP - INTERVAL '3 weeks'),
    (4, 'active', 1,  CURRENT_TIMESTAMP - INTERVAL '1 weeks'),
    (5, 'pending', 1, CURRENT_TIMESTAMP - INTERVAL '3 weeks'),
    (5, 'active', 1,  CURRENT_TIMESTAMP - INTERVAL '1 weeks'),
    (6, 'pending', 1, CURRENT_TIMESTAMP - INTERVAL '3 weeks'),
    (6, 'active', 1,  CURRENT_TIMESTAMP - INTERVAL '1 weeks');

-- Task
INSERT INTO project_element (project_id, title, parent_id, element_type, description, create_by, update_by, est_hours, contract_id, currency_code_id) VALUES
    (1,'Task 1',8,'task','lorem ipsum', 1,1, INTERVAL '6 hours', 1, 132),
    (1,'Task 2',8,'task','lorem ipsum', 1,1, INTERVAL '3 hours', 2 ,132),
    (1,'Task 3',7,'task','lorem ipsum', 1,1, NULL,3, 132);

-- Status history
INSERT INTO project_element_status (project_element_id, element_status, update_date, update_by) VALUES 
    (10, 'define', CURRENT_TIMESTAMP - interval '5 hours', 1),
    (10, 'in progress', CURRENT_TIMESTAMP - interval '3 hours', 2),
    (10, 'complete', CURRENT_TIMESTAMP - interval '2 hours', 2),
    (11, 'define', CURRENT_TIMESTAMP - interval '10 hours', 1),
    (11, 'in progress', CURRENT_TIMESTAMP - interval '8 hours', 2),
    (11, 'suspend', CURRENT_TIMESTAMP - interval '6 hours', 1),
    (11, 'in progress', CURRENT_TIMESTAMP - interval '4 hours', 2),
    (12, 'define', CURRENT_TIMESTAMP - interval '4 hours', 1),
    (12, 'in progress', CURRENT_TIMESTAMP - interval '3 hours', 4);

INSERT INTO project_element_time (project_element_id, element_summary, element_time, create_by, update_by) VALUES
    (10, 'Started the job', INTERVAL '3 hours', 2,2),
    (10, 'Finalized it ', INTERVAL '3 hours', 2,2),
    (11, 'It was a difficult task and I needed more time', INTERVAL '4 hours', 4,4);

INSERT INTO project_element_note (project_element_id, element_note, create_by, update_by) VALUES
    (10, 'Hey, how is it going with the task?', 1,1),
    (10, 'Expecting it to be finalized soon', 2,2),
    (11, 'Hey Test, I seem to need more than the expected time, it that ok?', 4,4),
    (11, 'Sure, take your time, but we are not going to pay you more', 4,4);

INSERT INTO project_contract_invite (contract_id)
VALUES (2), 
       (5),
       (5),
       (3);

INSERT INTO project_contract_invite_status (project_contract_invite_id, invite_status, create_by, create_date)
VALUES (1, 'Tentative', 1, CURRENT_TIMESTAMP - interval '1 day'),
       (2, 'Revoked', 4, CURRENT_TIMESTAMP - interval '1 day'),
       (3, 'Tentative', 4, CURRENT_TIMESTAMP - interval '1 hour'),
       (4, 'Tentative', 1, CURRENT_TIMESTAMP);