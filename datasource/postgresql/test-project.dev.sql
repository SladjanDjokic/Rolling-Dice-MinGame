INSERT INTO project (company_id, project_title, project_type, project_description, start_date, estimated_days)
    VALUES (1, 'Software development', 'software', 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus et diam vestibulum, lobortis ipsum quis, luctus leo. Nam at imperdiet eros, ac facilisis ante. Nullam id cursus dolor, id dapibus tellus. Ut sed arcu suscipit, placerat arcu nec, pellentesque ipsum. Vivamus dictum turpis non lectus convallis, et varius risus iaculis. Nunc non dolor volutpat, lobortis ipsum eu, cursus dui. Donec sem nibh, ornare id laoreet vel, pretium eu ligula. Donec massa tortor, sollicitudin vitae lobortis quis, lobortis quis lacus. In tempor augue bibendum euismod suscipit. Proin sodales sapien quis odio ultricies, eu faucibus nibh iaculis. Pellentesque a fermentum erat, non condimentum arcu. Nulla eu porta ante, ac malesuada ipsum. Cras molestie ullamcorper urna a elementum. Nunc quis massa urna. Ut tortor ipsum, finibus id commodo nec, tristique quis est. Suspendisse potenti.','2021-02-10', '90 days'),
           (1, 'Flyer design', 'marketing', 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vivamus et diam vestibulum, lobortis ipsum quis, luctus leo. Nam at imperdiet eros, ac facilisis ante. Nullam id cursus dolor, id dapibus tellus. Ut sed arcu suscipit, placerat arcu nec, pellentesque ipsum. Vivamus dictum turpis non lectus convallis, et varius risus iaculis. Nunc non dolor volutpat, lobortis ipsum eu, cursus dui. Donec sem nibh, ornare id laoreet vel, pretium eu ligula. Donec massa tortor, sollicitudin vitae lobortis quis, lobortis quis lacus. In tempor augue bibendum euismod suscipit. Proin sodales sapien quis odio ultricies, eu faucibus nibh iaculis. Pellentesque a fermentum erat, non condimentum arcu. Nulla eu porta ante, ac malesuada ipsum. Cras molestie ullamcorper urna a elementum. Nunc quis massa urna. Ut tortor ipsum, finibus id commodo nec, tristique quis est. Suspendisse potenti.','2021-02-11', '45 days');

INSERT INTO project_member (project_id, member_id, pay_rate, pay_type, currency_id, privileges)
    VALUES (1,1,50.0, 'hourly', 666, '{approve, create, view, edit}'),
           (1,2,30.0, 'hourly', 666, '{create, view}'),
           (1,10,10.0, 'hourly', 666, '{view}'),
           (2,1,50.0, 'hourly', 666, '{approve, create, view, edit}'),
           (2,5,30.0, 'hourly', 666, '{create, view}'),
           (2,20,10.0, 'hourly', 666, '{view}');

INSERT INTO project_update (project_id, update_by)
    VALUES (1, 1),
           (2, 4);

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



INSERT INTO project_epic (project_id, epic_title, epic_description, update_by)
    VALUES (1, 'Backend design', 'Design the endpointes', 1),
           (1, 'Frontend design', 'React front-end code', 1),
           (2, 'Design', 'Get PDF designs', 1),
           (2, 'Publishing', 'Print 1000 copies', 1);

INSERT INTO project_tremor (project_epic_id, tremor_title, tremor_description, update_by)
    VALUES (1, 'AWS infrastructure', '', 1);

INSERT INTO project_story (project_tremor_id, story_title, story_description, update_by)
    VALUES (1, 'Some story', 'Some cool title',  1),
           (1, 'Another story', 'Not so cool title', 1);

INSERT INTO project_task (project_story_id, project_member_id, task_status, task_title, task_description, est_hours, due_date, update_by)
    VALUES (1, 2, 'in progress','Task 1', 'lorem ipsum', INTERVAL '6 hours', '2021-03-01',1),
           (1, 4, 'define' ,'Task 2', 'lorem ipsum', INTERVAL '10 hours','2021-03-01',1),
           (1, 2, 'complete' ,'Task 3', 'lorem ipsum', INTERVAL '3 hours','2021-03-01',1);