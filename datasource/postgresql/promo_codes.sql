CREATE TABLE promo_codes (
	id SERIAL PRIMARY KEY NOT NULL,
	promo_code varchar(255) UNIQUE NOT NULL,
	created_by_member_id INT REFERENCES member (id) NOT NULL,
	description TEXT,
	active boolean DEFAULT true,
	create_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
	expiration_date TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE promo_code_activations (
	id SERIAL PRIMARY KEY NOT NULL,
	member_id INT REFERENCES member (id) NOT NULL,
	promo_code_id INT REFERENCES promo_codes (id),
	activation_date TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);