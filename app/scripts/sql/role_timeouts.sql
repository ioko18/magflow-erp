-- Set timeouts for the app role in the magflow database
-- These settings help prevent long-running transactions and idle connections

-- Set statement timeout to 30 seconds
-- This will cancel any query that runs longer than 30 seconds
ALTER ROLE app IN DATABASE magflow
    SET statement_timeout = '30s';

-- Set idle transaction timeout to 2 minutes
-- This will terminate any transaction that has been idle for more than 2 minutes
ALTER ROLE app IN DATABASE magflow
    SET idle_in_transaction_session_timeout = '120s';

-- Set lock timeout to 5 seconds
-- This will fail any operation that can't get a lock within 5 seconds
ALTER ROLE app IN DATABASE magflow
    SET lock_timeout = '5s';

-- For PostgreSQL 17+ (commented out by default)
-- ALTER ROLE app IN DATABASE magflow
--     SET transaction_timeout = '300s';

-- Display the current settings for verification
SELECT
    rolname,
    datname,
    'statement_timeout' as setting,
    setting as value
FROM pg_db_role_setting
JOIN pg_database ON pg_database.oid = pg_db_role_setting.setdatabase
JOIN pg_roles ON pg_roles.oid = pg_db_role_setting.setrole
CROSS JOIN pg_catalog.current_setting('statement_timeout') as setting
WHERE rolname = 'app' AND datname = 'magflow'

UNION ALL

SELECT
    rolname,
    datname,
    'idle_in_transaction_session_timeout' as setting,
    setting as value
FROM pg_db_role_setting
JOIN pg_database ON pg_database.oid = pg_db_role_setting.setdatabase
JOIN pg_roles ON pg_roles.oid = pg_db_role_setting.setrole
CROSS JOIN pg_catalog.current_setting('idle_in_transaction_session_timeout') as setting
WHERE rolname = 'app' AND datname = 'magflow'

UNION ALL

SELECT
    rolname,
    datname,
    'lock_timeout' as setting,
    setting as value
FROM pg_db_role_setting
JOIN pg_database ON pg_database.oid = pg_db_role_setting.setdatabase
JOIN pg_roles ON pg_roles.oid = pg_db_role_setting.setrole
CROSS JOIN pg_catalog.current_setting('lock_timeout') as setting
WHERE rolname = 'app' AND datname = 'magflow';
