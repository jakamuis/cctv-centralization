-- Manual creation of branches table as per migration 3f2c1b8d
CREATE TABLE IF NOT EXISTS branches (
    id UUID PRIMARY KEY NOT NULL,
    name VARCHAR NOT NULL,
    code VARCHAR NOT NULL UNIQUE,
    location VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Manual creation of cameras table as per migration add_camera_table_001
CREATE TABLE IF NOT EXISTS cameras (
    id UUID PRIMARY KEY NOT NULL UNIQUE,
    branch_id UUID NOT NULL REFERENCES branches(id),
    name VARCHAR(255) NOT NULL,
    stream_name VARCHAR(255) NOT NULL UNIQUE,
    rtsp_channel VARCHAR(50),
    status VARCHAR(50),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Create index on cameras.branch_id
CREATE INDEX IF NOT EXISTS ix_cameras_branch_id ON cameras(branch_id);