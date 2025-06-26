-- Migration: Add conversation branching support to sessions table
-- Description: Enables creating conversation branches when editing messages
-- Date: 2025-06-24 16:20:00

DO $$
DECLARE
    column_exists_parent BOOLEAN;
    column_exists_branch_point BOOLEAN;
    column_exists_branch_type BOOLEAN;
    column_exists_is_main BOOLEAN;
BEGIN
    -- Check if columns already exist
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'sessions' AND column_name = 'parent_session_id'
    ) INTO column_exists_parent;
    
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'sessions' AND column_name = 'branch_point_message_id'
    ) INTO column_exists_branch_point;
    
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'sessions' AND column_name = 'branch_type'
    ) INTO column_exists_branch_type;
    
    SELECT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'sessions' AND column_name = 'is_main_branch'
    ) INTO column_exists_is_main;
    
    -- Only proceed if columns don't exist
    IF column_exists_parent AND column_exists_branch_point AND column_exists_branch_type AND column_exists_is_main THEN
        RAISE NOTICE 'Migration already applied: session branching columns already exist';
    ELSE
        -- Create enum type for branch types if it doesn't exist
        DO $enum$
        BEGIN
            CREATE TYPE session_branch_type AS ENUM ('edit_branch', 'manual_branch');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $enum$;
        
        -- Add parent_session_id column if it doesn't exist
        IF NOT column_exists_parent THEN
            ALTER TABLE sessions ADD COLUMN parent_session_id UUID;
            RAISE NOTICE 'Added parent_session_id column to sessions table';
        END IF;
        
        -- Add branch_point_message_id column if it doesn't exist
        IF NOT column_exists_branch_point THEN
            ALTER TABLE sessions ADD COLUMN branch_point_message_id UUID;
            RAISE NOTICE 'Added branch_point_message_id column to sessions table';
        END IF;
        
        -- Add branch_type column if it doesn't exist
        IF NOT column_exists_branch_type THEN
            ALTER TABLE sessions ADD COLUMN branch_type session_branch_type;
            RAISE NOTICE 'Added branch_type column to sessions table';
        END IF;
        
        -- Add is_main_branch column if it doesn't exist
        IF NOT column_exists_is_main THEN
            ALTER TABLE sessions ADD COLUMN is_main_branch BOOLEAN DEFAULT true;
            RAISE NOTICE 'Added is_main_branch column to sessions table';
        END IF;
        
        -- Add foreign key constraints
        -- parent_session_id references sessions.id
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE table_name = 'sessions' AND constraint_name = 'sessions_parent_session_id_fkey'
        ) THEN
            ALTER TABLE sessions ADD CONSTRAINT sessions_parent_session_id_fkey
                FOREIGN KEY (parent_session_id) REFERENCES sessions(id) ON DELETE CASCADE;
            RAISE NOTICE 'Added foreign key constraint for parent_session_id';
        END IF;
        
        -- branch_point_message_id references messages.id
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints 
            WHERE table_name = 'sessions' AND constraint_name = 'sessions_branch_point_message_id_fkey'
        ) THEN
            ALTER TABLE sessions ADD CONSTRAINT sessions_branch_point_message_id_fkey
                FOREIGN KEY (branch_point_message_id) REFERENCES messages(id) ON DELETE SET NULL;
            RAISE NOTICE 'Added foreign key constraint for branch_point_message_id';
        END IF;
        
        -- Add indexes for performance
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'sessions' AND indexname = 'idx_sessions_parent_session_id'
        ) THEN
            CREATE INDEX idx_sessions_parent_session_id ON sessions(parent_session_id);
            RAISE NOTICE 'Added index on parent_session_id';
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'sessions' AND indexname = 'idx_sessions_branch_point_message_id'
        ) THEN
            CREATE INDEX idx_sessions_branch_point_message_id ON sessions(branch_point_message_id);
            RAISE NOTICE 'Added index on branch_point_message_id';
        END IF;
        
        IF NOT EXISTS (
            SELECT 1 FROM pg_indexes 
            WHERE tablename = 'sessions' AND indexname = 'idx_sessions_is_main_branch'
        ) THEN
            CREATE INDEX idx_sessions_is_main_branch ON sessions(is_main_branch);
            RAISE NOTICE 'Added index on is_main_branch';
        END IF;
        
        -- Set existing sessions as main branches
        UPDATE sessions SET is_main_branch = true WHERE is_main_branch IS NULL;
        
        RAISE NOTICE 'Successfully added session branching support';
        RAISE NOTICE 'Schema changes:';
        RAISE NOTICE '  - parent_session_id: References parent session for branches';
        RAISE NOTICE '  - branch_point_message_id: Message where branch was created';
        RAISE NOTICE '  - branch_type: Type of branch (edit_branch, manual_branch)';
        RAISE NOTICE '  - is_main_branch: Identifies main conversation thread';
    END IF;
END $$;