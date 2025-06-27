-- Ensure usage column exists in messages table
-- PostgreSQL Compatible Version

-- This migration ensures the usage column exists
-- If it already exists from previous migration, this is a no-op
DO $$
BEGIN
    -- Check if usage column exists, if not add it
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'messages' AND column_name = 'usage'
    ) THEN
        ALTER TABLE messages ADD COLUMN usage JSONB DEFAULT '{}';
    END IF;
END
$$;

-- Ensure index exists for usage queries  
CREATE INDEX IF NOT EXISTS idx_messages_usage_jsonb ON messages USING GIN(usage);

-- Create additional performance indexes for common queries
CREATE INDEX IF NOT EXISTS idx_messages_usage_framework ON messages((usage->>'framework'));
CREATE INDEX IF NOT EXISTS idx_messages_usage_request_tokens ON messages(CAST(usage->>'request_tokens' AS INTEGER));
CREATE INDEX IF NOT EXISTS idx_messages_usage_response_tokens ON messages(CAST(usage->>'response_tokens' AS INTEGER));