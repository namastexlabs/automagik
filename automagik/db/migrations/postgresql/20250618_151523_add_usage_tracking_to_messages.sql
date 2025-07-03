-- Add usage tracking to messages table for token and cost analytics
-- PostgreSQL Compatible Version

-- Add usage column to messages table (PostgreSQL) - check if it exists first
DO $$
BEGIN
    -- Add usage column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'messages' AND column_name = 'usage'
    ) THEN
        ALTER TABLE messages ADD COLUMN usage JSONB DEFAULT '{}';
    END IF;
END
$$;

-- Create index for usage queries (PostgreSQL JSONB)
CREATE INDEX IF NOT EXISTS idx_messages_usage ON messages USING GIN(usage);

-- Create index for model queries
CREATE INDEX IF NOT EXISTS idx_messages_usage_model ON messages((usage->>'model'));

-- Create index for token queries  
CREATE INDEX IF NOT EXISTS idx_messages_usage_tokens ON messages(CAST(usage->>'total_tokens' AS INTEGER));

-- Add constraint to ensure valid JSON structure (use DO block for idempotency)
DO $$
BEGIN
    -- Add usage validation constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_messages_usage_valid'
    ) THEN
        ALTER TABLE messages 
        ADD CONSTRAINT chk_messages_usage_valid 
        CHECK (jsonb_typeof(usage) = 'object' OR usage IS NULL);
    END IF;
END
$$;

-- Add comments
COMMENT ON COLUMN messages.usage IS 'JSONB tracking token usage, costs, and model information for analytics';