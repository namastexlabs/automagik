-- First, check if the column exists and add it if it doesn't
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'agents' AND column_name = 'active_default_prompt_id'
    ) THEN
        ALTER TABLE agents ADD COLUMN active_default_prompt_id INTEGER;
    END IF;
END $$;

-- Then, add a foreign key constraint if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.table_constraints 
        WHERE constraint_name = 'fk_agents_active_default_prompt'
    ) THEN
        ALTER TABLE agents ADD CONSTRAINT fk_agents_active_default_prompt
            FOREIGN KEY (active_default_prompt_id) REFERENCES prompts(id) ON DELETE SET NULL;
    END IF;
END $$;

-- Add an index if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM pg_indexes 
        WHERE indexname = 'idx_agents_active_default_prompt_id'
    ) THEN
        CREATE INDEX idx_agents_active_default_prompt_id ON agents(active_default_prompt_id);
    END IF;
END $$;

-- Finally, update the comments for the new column
COMMENT ON COLUMN agents.active_default_prompt_id IS 'References the ID of the active prompt for the agent''s default status';

-- NOTE: We will rename system_prompt to active_default_prompt_id in data migration script
-- This is a two-step process: 
-- 1. Create the prompts table and add columns (this script)
-- 2. Migrate data from system_prompt to prompts table (separate script)
-- 3. Then drop the system_prompt column after data is migrated (separate script) 