-- Add error handling configuration to agents table
ALTER TABLE agents 
ADD COLUMN IF NOT EXISTS error_message TEXT DEFAULT NULL,
ADD COLUMN IF NOT EXISTS error_webhook_url TEXT DEFAULT NULL;

-- Add comment for documentation
COMMENT ON COLUMN agents.error_message IS 'Custom error message to display when agent encounters an error';
COMMENT ON COLUMN agents.error_webhook_url IS 'Webhook URL to call when agent encounters an error';