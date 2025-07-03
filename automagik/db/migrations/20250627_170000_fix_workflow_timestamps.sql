-- Fix workflow timestamps that have 'CURRENT_TEXT' instead of actual timestamps
-- This migration corrects a data issue where timestamp defaults were stored as literal strings

-- Update any workflows with invalid timestamp values
UPDATE workflows 
SET created_at = CURRENT_TIMESTAMP 
WHERE created_at = 'CURRENT_TEXT' 
   OR created_at = 'CURRENT_TIMESTAMP'
   OR created_at IS NULL;

UPDATE workflows 
SET updated_at = CURRENT_TIMESTAMP 
WHERE updated_at = 'CURRENT_TEXT' 
   OR updated_at = 'CURRENT_TIMESTAMP'
   OR updated_at IS NULL;

-- Ensure all workflows have valid timestamps
UPDATE workflows 
SET created_at = CURRENT_TIMESTAMP 
WHERE typeof(created_at) != 'text' 
   OR datetime(created_at) IS NULL;

UPDATE workflows 
SET updated_at = CURRENT_TIMESTAMP 
WHERE typeof(updated_at) != 'text' 
   OR datetime(updated_at) IS NULL;