-- Migration: Create preferences tables
-- [EPIC-SIMULATION-TEST]
-- Description: Creates preferences and preference_history tables for user preference system

-- Create preferences table
CREATE TABLE IF NOT EXISTS preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,
    preferences JSONB NOT NULL DEFAULT '{}',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT unique_user_category UNIQUE(user_id, category)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_preferences_user_id ON preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_preferences_category ON preferences(category);

-- Create preference history table for audit logging
CREATE TABLE IF NOT EXISTS preference_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    preference_id UUID NOT NULL REFERENCES preferences(id) ON DELETE CASCADE,
    old_value JSONB,
    new_value JSONB NOT NULL,
    changed_by UUID REFERENCES users(id) ON DELETE SET NULL,
    changed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create index for history lookups
CREATE INDEX IF NOT EXISTS idx_preference_history_preference_id ON preference_history(preference_id);
CREATE INDEX IF NOT EXISTS idx_preference_history_changed_at ON preference_history(changed_at);

-- Add trigger to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_preferences_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS preferences_updated_at_trigger ON preferences;
CREATE TRIGGER preferences_updated_at_trigger
    BEFORE UPDATE ON preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_preferences_updated_at();

-- Add comment to tables
COMMENT ON TABLE preferences IS 'Stores user preferences by category with flexible JSONB storage';
COMMENT ON TABLE preference_history IS 'Audit log tracking all changes to user preferences';

-- Add comments to columns
COMMENT ON COLUMN preferences.category IS 'Preference category: ui, behavior, notifications, language, privacy, accessibility';
COMMENT ON COLUMN preferences.preferences IS 'JSONB field containing preference key-value pairs';
COMMENT ON COLUMN preferences.version IS 'Schema version for preference migration support';