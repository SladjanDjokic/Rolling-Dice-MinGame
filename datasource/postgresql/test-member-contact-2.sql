do $$
      begin
          for r in 1..71 loop
              INSERT INTO member_contact_2 (member_id, description, device, device_type, device_country, device_confirm_date, method_type, display_order, enabled, primary_contact, create_date, update_date) VALUES (r, 'Cell phone', '9721713771', 'cell', 840, '2021-01-26 22:41:46.147990', 'voice', 2, true, true, '2021-01-26 22:41:46.147990', '2021-01-26 22:41:46.147990');
              INSERT INTO member_contact_2 (member_id, description, device, device_type, device_country, device_confirm_date, method_type, display_order, enabled, primary_contact, create_date, update_date) VALUES (r, 'Office phone', '9723343333', 'landline', 840, '2021-01-26 22:41:46.147990', 'voice', 3, true, false, '2021-01-26 22:41:46.147990', '2021-01-26 22:41:46.147990');
              INSERT INTO member_contact_2 (member_id, description, device, device_type, device_country, device_confirm_date, method_type, display_order, enabled, primary_contact, create_date, update_date) VALUES (r, 'Office email', 'test@email.com', 'email', 840, '2021-01-26 22:41:46.147990', 'html', 1, true, true, '2021-01-26 22:41:46.147990', '2021-01-26 22:41:46.147990');

              end loop;
  end;
$$;