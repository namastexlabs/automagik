-- Migration: Create preferences tables (SQLite compatible)
-- [EPIC-SIMULATION-TEST]
-- Description: Creates preferences and preference_history tables for user preference system

-- Create preferences table
CREATE TABLE IF NOT EXISTS preferences (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    category TEXT NOT NULL,
    preferences TEXT NOT NULL DEFAULT '{}',
    version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    CONSTRAINT unique_user_category UNIQUE(user_id, category)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_preferences_user_id ON preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_preferences_category ON preferences(category);

-- Create preference history table for audit logging
CREATE TABLE IF NOT EXISTS preference_history (
    id TEXT PRIMARY KEY,
    preference_id TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT NOT NULL,
    changed_by TEXT,
    changed_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Create index for history lookups
CREATE INDEX IF NOT EXISTS idx_preference_history_preference_id ON preference_history(preference_id);
CREATE INDEX IF NOT EXISTS idx_preference_history_changed_at ON preference_history(changed_at);

-- Create trigger to automatically update updated_at timestamp
CREATE TRIGGER IF NOT EXISTS preferences_updated_at_trigger
    AFTER UPDATE ON preferences
    FOR EACH ROW
    BEGIN
        UPDATE preferences SET updated_at = datetime('now') WHERE id = NEW.id;
    END;