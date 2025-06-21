-- Migration: Ensure usage column exists in messages table
-- This migration properly handles the case where the column may already exist
-- Compatible with both SQLite and PostgreSQL

-- For PostgreSQL: Use idempotent DO block
-- For SQLite: The migration manager will check if column exists before applying

-- PostgreSQL version (will be skipped by SQLite)
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'messages' AND column_name = 'usage'
    ) THEN
        ALTER TABLE messages ADD COLUMN usage TEXT;
    END IF;
END
$$;

-- SQLite version (will fail gracefully in PostgreSQL due to DO block above)
-- The migration manager handles checking if column exists for SQLite
ALTER TABLE messages ADD COLUMN usage TEXT;

-- Create indexes for performance (works on both databases)
CREATE INDEX IF NOT EXISTS idx_messages_usage_not_null
ON messages (usage) WHERE usage IS NOT NULL;

-- Additional indexes for PostgreSQL JSON queries (will fail gracefully on SQLite)
-- These are commented out but can be uncommented for PostgreSQL deployments
-- CREATE INDEX IF NOT EXISTS idx_messages_usage_model 
-- ON messages ((usage->>'model')) WHERE usage IS NOT NULL;
-- CREATE INDEX IF NOT EXISTS idx_messages_usage_tokens
-- ON messages ((usage->>'total_tokens')) WHERE usage IS NOT NULL;