-- Migration: Add channel_payload column to messages table
-- Description: Adds a new column to store channel-specific payload data for messages
-- Created at: 2025-03-26 04:59:44

-- Add channel_payload column
ALTER TABLE messages
ADD COLUMN channel_payload JSONB DEFAULT NULL;

-- Add comment to explain the column's purpose
COMMENT ON COLUMN messages.channel_payload IS 'Stores channel-specific payload data for messages, such as platform-specific metadata or formatting';

-- Update the updated_at timestamp for existing rows
UPDATE messages
SET updated_at = CURRENT_TIMESTAMP
WHERE channel_payload IS NULL; 