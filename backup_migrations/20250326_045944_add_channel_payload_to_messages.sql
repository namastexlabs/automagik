-- Migration: Add channel_payload column to messages table
-- Description: Adds a new column to store channel-specific payload data for messages
-- Created at: 2025-03-26 04:59:44

-- Add channel_payload column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'messages' AND column_name = 'channel_payload'
    ) THEN
        ALTER TABLE messages
        ADD COLUMN channel_payload JSONB DEFAULT NULL;
        RAISE NOTICE 'Added channel_payload column to messages table';
    ELSE
        RAISE NOTICE 'channel_payload column already exists in messages table, skipping';
    END IF;
END $$;

-- Add comment to explain the column's purpose (only if column exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'messages' AND column_name = 'channel_payload'
    ) THEN
        COMMENT ON COLUMN messages.channel_payload IS 'Stores channel-specific payload data for messages, such as platform-specific metadata or formatting';
    END IF;
END $$;

-- Update the updated_at timestamp for existing rows (only if column exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT FROM information_schema.columns 
        WHERE table_name = 'messages' AND column_name = 'channel_payload'
    ) THEN
        UPDATE messages
        SET updated_at = CURRENT_TIMESTAMP
        WHERE channel_payload IS NULL;
    END IF;
END $$; 