-- Create enum type
CREATE TYPE app.user_role AS ENUM (
    'admin',
    'user'
);

-- Create users table
CREATE TABLE app.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_superuser BOOLEAN NOT NULL DEFAULT false,
    last_login TIMESTAMP WITH TIME ZONE,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    last_failed_login TIMESTAMP WITH TIME ZONE,
    email_verified BOOLEAN NOT NULL DEFAULT false,
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create roles table
CREATE TABLE app.roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    is_system_role BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create permissions table
CREATE TABLE app.permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create user_roles join table
CREATE TABLE app.user_roles (
    user_id INTEGER NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES app.roles(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

-- Create role_permissions join table
CREATE TABLE app.role_permissions (
    role_id INTEGER NOT NULL REFERENCES app.roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES app.permissions(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (role_id, permission_id)
);

-- Create refresh_tokens table
CREATE TABLE app.refresh_tokens (
    id SERIAL PRIMARY KEY,
    token VARCHAR(512) NOT NULL UNIQUE,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_revoked BOOLEAN NOT NULL DEFAULT false,
    user_agent VARCHAR(255),
    ip_address VARCHAR(45),
    user_id INTEGER NOT NULL REFERENCES app.users(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_refresh_tokens_user_id ON app.refresh_tokens(user_id);

-- Insert initial data
INSERT INTO app.roles (name, description, is_system_role) VALUES 
    ('admin', 'Administrator with full access', true),
    ('user', 'Regular user with basic access', true);

-- Insert some common permissions
INSERT INTO app.permissions (name, description) VALUES 
    ('users:read', 'View user accounts'),
    ('users:write', 'Create and update user accounts'),
    ('users:delete', 'Delete user accounts'),
    ('roles:read', 'View roles and permissions'),
    ('roles:write', 'Create and update roles and permissions'),
    ('roles:delete', 'Delete roles and permissions');

-- Create admin user with password 'admin123'
INSERT INTO app.users (email, hashed_password, full_name, is_active, is_superuser, email_verified) VALUES 
    ('admin@example.com', '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW', 'Admin User', true, true, true);

-- Assign admin role to admin user
INSERT INTO app.user_roles (user_id, role_id) 
    VALUES (1, (SELECT id FROM app.roles WHERE name = 'admin'));

-- Assign all permissions to admin role
INSERT INTO app.role_permissions (role_id, permission_id)
    SELECT (SELECT id FROM app.roles WHERE name = 'admin'), id FROM app.permissions;
