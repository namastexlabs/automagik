-- First, revoke any existing function privileges from namastex
REVOKE EXECUTE ON FUNCTION create_agents_dev_database(text) FROM namastex;
REVOKE EXECUTE ON FUNCTION drop_agents_dev_database(text) FROM namastex;

-- Drop the existing helper functions for namastex and the generic can_drop_database
DROP FUNCTION IF EXISTS create_agents_dev_database(text);
DROP FUNCTION IF EXISTS drop_agents_dev_database(text);
DROP FUNCTION IF EXISTS can_drop_database(text, text);

-- Now we can safely drop the user
DROP USER IF EXISTS namastex;

-- Create the namastex user with CREATEDB privilege
CREATE USER namastex WITH PASSWORD 'senhosa' CREATEDB;

-- Recreate the functions
-- This function is a general check, but tailored here for namastex's rules
CREATE OR REPLACE FUNCTION can_drop_database(db_name text, user_name text)
RETURNS boolean AS $$
BEGIN
    -- Allow namastex to drop databases with agents_dev_ prefix or the exact name agents_dev
    IF user_name = 'namastex' AND (db_name LIKE 'agents_dev_%' OR db_name = 'agents_dev') THEN
        RETURN true;
    END IF;
    RETURN false;
END;
$$ LANGUAGE plpgsql;

-- Validation function for creating databases for namastex
CREATE OR REPLACE FUNCTION create_agents_dev_database(db_name text)
RETURNS void AS $$
BEGIN
    -- Check if database name starts with agents_dev_ or is agents_dev
    IF NOT (db_name LIKE 'agents_dev_%' OR db_name = 'agents_dev') THEN
        RAISE EXCEPTION 'User namastex can only create databases with prefix "agents_dev_" or the exact name "agents_dev". Database name "%" is not allowed.', db_name;
    END IF;
    -- If the check passes, the function completes. 
    -- The actual CREATE DATABASE command must be run separately by the namastex user.
END;
$$ LANGUAGE plpgsql;

-- Validation function for dropping databases for namastex
CREATE OR REPLACE FUNCTION drop_agents_dev_database(db_name text)
RETURNS void AS $$
BEGIN
    -- Check if database name starts with agents_dev_ or is agents_dev
    IF NOT (db_name LIKE 'agents_dev_%' OR db_name = 'agents_dev') THEN
        RAISE EXCEPTION 'User namastex can only drop databases with prefix "agents_dev_" or the exact name "agents_dev". Database name "%" is not allowed.', db_name;
    END IF;
    -- If the check passes, the function completes.
    -- The actual DROP DATABASE command must be run separately by the namastex user.
END;
$$ LANGUAGE plpgsql;

-- Grant execute permission to namastex on these validation functions
GRANT EXECUTE ON FUNCTION create_agents_dev_database(text) TO namastex;
GRANT EXECUTE ON FUNCTION drop_agents_dev_database(text) TO namastex;

-- Create the database 'agents_dev'
-- Step 1: Validate the database name using the function.
SELECT create_agents_dev_database('agents_dev');

-- Step 2: If Step 1 succeeds without error, then create the database.
CREATE DATABASE agents_dev;

-- Optional: Grant all privileges on the new database to namastex and set owner
ALTER DATABASE agents_dev OWNER TO namastex;
GRANT ALL PRIVILEGES ON DATABASE agents_dev TO namastex;

-- To connect and verify (run manually in psql or your SQL client):
-- \c agents_dev
-- SELECT current_database();
-- SHOW search_path;
-- 
-- Further setup within the agents_dev database can now be done by user namastex.

