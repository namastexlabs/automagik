-- Drop the system_prompt column from the agents table
-- This should only be executed after all data has been migrated to the prompts table
-- using the migrate_agent_prompts.py script

-- First, verify that all agents have a valid active_default_prompt_id or NULL system_prompt
DO $$
DECLARE
    missing_count INTEGER;
BEGIN
    -- Count agents with system_prompt but no active_default_prompt_id
    SELECT COUNT(*) INTO missing_count FROM agents 
    WHERE system_prompt IS NOT NULL 
    AND system_prompt != '' 
    AND active_default_prompt_id IS NULL;
    
    IF missing_count > 0 THEN
        RAISE EXCEPTION 'Cannot drop system_prompt column: % agents have system_prompt but no active_default_prompt_id', missing_count;
    END IF;
END $$;

-- Drop the system_prompt column
ALTER TABLE agents DROP COLUMN system_prompt; 