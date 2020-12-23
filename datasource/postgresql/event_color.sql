CREATE TABLE event_color (
    id SERIAL PRIMARY KEY,
    color VARCHAR(255) NOT NULL
);

INSERT INTO event_color (color) 
VALUES 
    ('#E5511F'),
    ('#F686AE'),
    ('#F2BD2C'),
    ('#C7BBED'),
    ('#7DAE7AB'),
    ('#F2F2F0');