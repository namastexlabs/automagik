-- Drop the system_prompt column from the agents table if it exists.
-- This migration is now idempotent: it safely exits when the column has already been removed or was never present.

DO $$
DECLARE
    missing_count INTEGER;
BEGIN
    -- Proceed only if the column exists
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'agents'
          AND column_name = 'system_prompt'
    ) THEN
        -- Count any agents that still have legacy data in system_prompt but no prompt row
        SELECT COUNT(*) INTO missing_count
        FROM agents
        WHERE system_prompt IS NOT NULL
          AND TRIM(system_prompt) <> ''
          AND active_default_prompt_id IS NULL;

        IF missing_count > 0 THEN
            RAISE EXCEPTION 'Cannot drop system_prompt column: % agents still rely on it', missing_count;
        END IF;

        -- Finally, drop the legacy column
        ALTER TABLE agents DROP COLUMN system_prompt;
    END IF;
END $$; 