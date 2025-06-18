-- Migration: Add usage tracking to messages table
-- Compatible with both SQLite and PostgreSQL

-- Add usage column to messages table for token tracking
ALTER TABLE messages ADD COLUMN IF NOT EXISTS usage TEXT;

-- Create index for performance on usage queries
-- This works for both SQLite (TEXT) and PostgreSQL (can be converted to JSONB later)
CREATE INDEX IF NOT EXISTS idx_messages_usage_model 
ON messages ((usage->>'model')) WHERE usage IS NOT NULL;

-- Create index for usage data queries
CREATE INDEX IF NOT EXISTS idx_messages_usage_tokens
ON messages ((usage->>'total_tokens')) WHERE usage IS NOT NULL;

-- Create index for framework type
CREATE INDEX IF NOT EXISTS idx_messages_usage_framework
ON messages ((usage->>'framework')) WHERE usage IS NOT NULL;

-- For PostgreSQL optimization (will be ignored by SQLite)
-- CREATE INDEX IF NOT EXISTS idx_messages_usage_gin 
-- ON messages USING GIN (usage) WHERE usage IS NOT NULL;