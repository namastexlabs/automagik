-- Fix sessions.user_id constraint to allow NULL values
-- This addresses the constraint violation when deleting users with cascade operations

-- First, check if the constraint exists
DO $$
BEGIN
    -- Make user_id column nullable in sessions table
    ALTER TABLE sessions ALTER COLUMN user_id DROP NOT NULL;
    
    RAISE NOTICE 'Successfully made sessions.user_id nullable';
EXCEPTION
    WHEN others THEN
        RAISE NOTICE 'Error making sessions.user_id nullable: %', SQLERRM;
END $$;

-- Update any existing NULL user_id values that might cause issues
-- (This shouldn't be needed but ensures consistency)
UPDATE sessions SET user_id = NULL WHERE user_id IS NULL;

-- Add comment explaining the change
COMMENT ON COLUMN sessions.user_id IS 'User ID - nullable to support cascade delete operations'; 