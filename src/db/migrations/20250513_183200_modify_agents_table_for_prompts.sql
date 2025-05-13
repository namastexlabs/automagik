-- First, create a new column for the active default prompt ID
ALTER TABLE agents ADD COLUMN active_default_prompt_id INTEGER;

-- Then, add a foreign key constraint referencing the prompts table
ALTER TABLE agents ADD CONSTRAINT fk_agents_active_default_prompt
    FOREIGN KEY (active_default_prompt_id) REFERENCES prompts(id) ON DELETE SET NULL;

-- Add an index on active_default_prompt_id for faster lookups
CREATE INDEX idx_agents_active_default_prompt_id ON agents(active_default_prompt_id);

-- Finally, update the comments for the new column
COMMENT ON COLUMN agents.active_default_prompt_id IS 'References the ID of the active prompt for the agent''s default status';

-- NOTE: We will rename system_prompt to active_default_prompt_id in data migration script
-- This is a two-step process: 
-- 1. Create the prompts table and add columns (this script)
-- 2. Migrate data from system_prompt to prompts table (separate script)
-- 3. Then drop the system_prompt column after data is migrated (separate script) 