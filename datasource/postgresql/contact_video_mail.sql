-- Contact Video Mail table
CREATE TABLE contact_video_mail (
  id SERIAL PRIMARY KEY,
  subject TEXT,
  message_from INTEGER NOT NULL REFERENCES member (id),
  message_to INTEGER NOT NULL REFERENCES member (id),
  video_storage_id INT REFERENCES file_storage_engine (id),
  read BOOLEAN DEFAULT FALSE,
  create_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
  update_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);