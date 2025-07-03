-- Create settings table for application configuration storage
-- Supports both encrypted (API keys) and plain text (URLs, flags) settings

CREATE TABLE IF NOT EXISTS settings (
    id TEXT PRIMARY KEY,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    encrypted INTEGER DEFAULT 0,
    description TEXT,
    category TEXT DEFAULT 'general',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    created_by TEXT,
    CHECK (category IN ('api_keys', 'urls', 'features', 'ui_config', 'general'))
);

-- Create indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key);
CREATE INDEX IF NOT EXISTS idx_settings_category ON settings(category);
CREATE INDEX IF NOT EXISTS idx_settings_created_at ON settings(created_at);

-- Insert default settings for the platform
INSERT OR IGNORE INTO settings (id, key, value, encrypted, category, description) VALUES
('1', 'automagik_url', 'http://localhost:28881', 0, 'urls', 'Backend API endpoint'),
('2', 'sync_interval_seconds', '30', 0, 'features', 'Background sync frequency'),
('3', 'enable_auto_sync', 'true', 0, 'features', 'Enable automatic background sync'),
('4', 'enable_notifications', 'true', 0, 'features', 'Push notifications enabled');