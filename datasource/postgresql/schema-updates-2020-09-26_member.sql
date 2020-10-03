-- We rename memeber.avatar_Storage_id to security_picture_storage_id

ALTER TABLE member
    RENAME COLUMN avatar_storage_id TO security_picture_storage_id;