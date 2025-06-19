-- Migration: Add usage tracking to messages table
-- Compatible with both SQLite and PostgreSQL

-- Add usage column to messages table for token tracking
-- SQLite doesn't support IF NOT EXISTS with ALTER TABLE
ALTER TABLE messages ADD COLUMN usage TEXT;

-- Create basic index for usage column (SQLite compatible)
-- SQLite doesn't support JSON operators in indexes
CREATE INDEX IF NOT EXISTS idx_messages_usage 
ON messages (usage) WHERE usage IS NOT NULL;

-- For PostgreSQL optimization (will be ignored by SQLite)
-- CREATE INDEX IF NOT EXISTS idx_messages_usage_model 
-- ON messages ((usage->>'model')) WHERE usage IS NOT NULL;

-- CREATE INDEX IF NOT EXISTS idx_messages_usage_tokens
-- ON messages ((usage->>'total_tokens')) WHERE usage IS NOT NULL;

-- CREATE INDEX IF NOT EXISTS idx_messages_usage_framework
-- ON messages ((usage->>'framework')) WHERE usage IS NOT NULL;

-- CREATE INDEX IF NOT EXISTS idx_messages_usage_gin 
-- ON messages USING GIN (usage) WHERE usage IS NOT NULL;