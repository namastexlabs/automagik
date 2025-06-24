-- Migration: Allow NULL user_id in memories table for agent global memory support
-- Related to NMSTX-63: Fix Memory API: Support Agent Global Memory (user_id=None)
-- Date: 2025-05-27 04:00:00

-- Remove NOT NULL constraint from user_id column in memories table
-- This allows agent global memory where user_id=NULL and agent_id is provided

DO $$
DECLARE
    column_nullable text;
BEGIN
    -- Check if user_id column is already nullable
    SELECT is_nullable INTO column_nullable
    FROM information_schema.columns
    WHERE table_name = 'memories' AND column_name = 'user_id';
    
    IF column_nullable = 'YES' THEN
        RAISE NOTICE 'Migration already applied: memories.user_id is already nullable';
    ELSE
        -- Remove NOT NULL constraint from user_id column
        ALTER TABLE memories ALTER COLUMN user_id DROP NOT NULL;
        
        RAISE NOTICE 'Successfully removed NOT NULL constraint from memories.user_id';
        RAISE NOTICE 'Agent global memory (user_id=NULL + agent_id=provided) is now supported';
    END IF;
END $$; 