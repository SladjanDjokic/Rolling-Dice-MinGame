INSERT INTO promo_codes (created_by_member_id, promo_code, description, expiration_date) VALUES
 (1, '50OFF','A 50% Off discount for the 3 first months', now() + INTERVAL '2 weeks'),
 (1, '2020CHRISTMAS', 'All AMERA sevices free of charge until Christmas', now() + INTERVAL '2 months');

INSERT INTO promo_code_activations (member_id, promo_code_id) VALUES
	(2, 1);