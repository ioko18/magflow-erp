-- Set search_path for the app role in the magflow database
-- This eliminates the need to pass search_path via client connection options
-- which can cause issues with PgBouncer

ALTER ROLE app IN DATABASE magflow SET search_path = app, public;
