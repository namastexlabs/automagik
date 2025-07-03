-- Create settings table for application configuration storage (PostgreSQL version)
-- Supports both encrypted (API keys) and plain text (URLs, flags) settings

CREATE TABLE IF NOT EXISTS settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key VARCHAR(255) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    encrypted BOOLEAN DEFAULT FALSE,
    description TEXT,
    category VARCHAR(100) DEFAULT 'general',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by UUID,
    CHECK (category IN ('api_keys', 'urls', 'features', 'ui_config', 'general'))
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);
CREATE INDEX IF NOT EXISTS idx_settings_category ON settings(category);
CREATE INDEX IF NOT EXISTS idx_settings_created_at ON settings(created_at);

-- Insert default settings for the platform
INSERT INTO settings (key, value, encrypted, category, description) VALUES
('automagik_url', 'http://localhost:28881', FALSE, 'urls', 'Backend API endpoint'),
('sync_interval_seconds', '30', FALSE, 'features', 'Background sync frequency'),
('enable_auto_sync', 'true', FALSE, 'features', 'Enable automatic background sync'),
('enable_notifications', 'true', FALSE, 'features', 'Push notifications enabled')
ON CONFLICT (key) DO NOTHING;