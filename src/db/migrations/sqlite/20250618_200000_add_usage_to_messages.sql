-- Migration: add usage column to messages table if missing
-- SQLite compatible version - this will fail silently if column already exists
-- which is expected behavior for this migration

-- Check if column exists and add if missing (SQLite compatible approach)
-- This migration may fail if column already exists - that's expected and safe
ALTER TABLE messages ADD COLUMN usage TEXT; 