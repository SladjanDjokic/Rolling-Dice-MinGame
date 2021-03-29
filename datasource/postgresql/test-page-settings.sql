INSERT INTO member_page_settings 
    (member_id, page_type, view_type, sort_order)
VALUES 
    (1, 'Contacts', 'table', Array['first_name']),
    (1, 'Groups', 'tile', Array['group_name']),
    (1, 'Calendar', 'week', Array['']),
    (1, 'Drive', 'tile', Array['file_name']),
    (1, 'Mail', 'table', Array['']);
