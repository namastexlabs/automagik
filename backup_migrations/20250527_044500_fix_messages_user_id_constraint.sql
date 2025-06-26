-- Migration: Fix messages.user_id constraint conflict 
-- Related to NMSTX-36: Fix database constraint violation during user deletion
-- Date: 2025-05-27 04:45:00

-- The issue: messages.user_id has NOT NULL constraint but foreign key is ON DELETE SET NULL
-- This causes: "null value in column "user_id" of relation "messages" violates not-null constraint"
-- Solution: Allow NULL in messages.user_id column

DO $$
DECLARE
    column_nullable text;
BEGIN
    -- Check if user_id column in messages is already nullable
    SELECT is_nullable INTO column_nullable
    FROM information_schema.columns
    WHERE table_name = 'messages' AND column_name = 'user_id';
    
    IF column_nullable = 'YES' THEN
        RAISE NOTICE 'Migration already applied: messages.user_id is already nullable';
    ELSE
        -- Remove NOT NULL constraint from user_id column in messages table
        ALTER TABLE messages ALTER COLUMN user_id DROP NOT NULL;
        
        RAISE NOTICE 'Successfully removed NOT NULL constraint from messages.user_id';
        RAISE NOTICE 'User deletion will now properly set messages.user_id to NULL instead of failing';
    END IF;
END $$; 