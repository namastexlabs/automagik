-- Migration: Add usage tracking to messages table
-- Compatible with both SQLite and PostgreSQL

-- SQLite doesn't support IF NOT EXISTS with ADD COLUMN, so we handle this in migration manager
ALTER TABLE messages ADD COLUMN usage TEXT;

-- Create basic index for performance on usage queries (SQLite compatible)
CREATE INDEX IF NOT EXISTS idx_messages_usage_not_null
ON messages (usage) WHERE usage IS NOT NULL;

-- PostgreSQL-specific indexes with JSON operators (commented out for SQLite)
-- For PostgreSQL: Create index for performance on JSON usage queries
-- CREATE INDEX IF NOT EXISTS idx_messages_usage_model 
-- ON messages ((usage->>'model')) WHERE usage IS NOT NULL;

-- CREATE INDEX IF NOT EXISTS idx_messages_usage_tokens
-- ON messages ((usage->>'total_tokens')) WHERE usage IS NOT NULL;

-- CREATE INDEX IF NOT EXISTS idx_messages_usage_framework
-- ON messages ((usage->>'framework')) WHERE usage IS NOT NULL;
-- CREATE INDEX IF NOT EXISTS idx_messages_usage_gin 
-- ON messages USING GIN (usage) WHERE usage IS NOT NULL;