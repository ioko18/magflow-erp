-- 01-functions.sql
-- This script creates database functions and triggers

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function for soft delete
CREATE OR REPLACE FUNCTION soft_delete_trigger()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.deleted_at IS NULL AND NEW.deleted_at IS NOT NULL THEN
        NEW.updated_at = CURRENT_TIMESTAMP;
    END IF;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Function to check if a user has a specific permission
CREATE OR REPLACE FUNCTION has_permission(user_id UUID, permission_name VARCHAR(100))
RETURNS BOOLEAN AS $$
DECLARE
    has_perm BOOLEAN;
BEGIN
    SELECT EXISTS (
        SELECT 1 
        FROM user_roles ur
        JOIN role_permissions rp ON ur.role_id = rp.role_id
        JOIN permissions p ON rp.permission_id = p.id
        WHERE ur.user_id = has_permission.user_id 
        AND p.name = has_permission.permission_name
    ) INTO has_perm;
    
    RETURN COALESCE(has_perm, FALSE);
END;
$$ language 'plpgsql' STABLE;

-- Function to get user's full name
CREATE OR REPLACE FUNCTION get_user_full_name(user_id UUID)
RETURNS TEXT AS $$
DECLARE
    full_name TEXT;
BEGIN
    SELECT CONCAT_WS(' ', first_name, last_name)
    INTO full_name
    FROM users
    WHERE id = get_user_full_name.user_id;
    
    RETURN full_name;
END;
$$ language 'plpgsql' STABLE;
