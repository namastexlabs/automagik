-- Final migration to ensure usage column exists with proper configuration
-- PostgreSQL Compatible Version  

-- Ensure usage column exists with proper default and constraints
DO $$
BEGIN
    -- Add usage column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'messages' AND column_name = 'usage'
    ) THEN
        ALTER TABLE messages ADD COLUMN usage JSONB DEFAULT '{}';
    END IF;
    
    -- Ensure default value is set for existing NULL values
    UPDATE messages SET usage = '{}' WHERE usage IS NULL;
END
$$;

-- Ensure all required indexes exist
CREATE INDEX IF NOT EXISTS idx_messages_usage_final ON messages USING GIN(usage);
CREATE INDEX IF NOT EXISTS idx_messages_usage_total_tokens ON messages(((usage->>'total_tokens')::INTEGER));

-- Add final constraint to ensure usage is never NULL
ALTER TABLE messages 
ALTER COLUMN usage SET DEFAULT '{}',
ALTER COLUMN usage SET NOT NULL;