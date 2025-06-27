-- Fix workflow timestamps that have 'CURRENT_TEXT' instead of actual timestamps (PostgreSQL version)
-- This migration corrects a data issue where timestamp defaults were stored as literal strings

-- Update any workflows with invalid timestamp values
UPDATE workflows 
SET created_at = CURRENT_TIMESTAMP 
WHERE created_at::text = 'CURRENT_TEXT' 
   OR created_at::text = 'CURRENT_TIMESTAMP'
   OR created_at IS NULL;

UPDATE workflows 
SET updated_at = CURRENT_TIMESTAMP 
WHERE updated_at::text = 'CURRENT_TEXT' 
   OR updated_at::text = 'CURRENT_TIMESTAMP'
   OR updated_at IS NULL;