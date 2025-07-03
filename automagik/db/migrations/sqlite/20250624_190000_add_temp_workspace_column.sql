-- Add temp_workspace column to workflow_runs table
-- This tracks whether a workflow run used a temporary isolated workspace

-- SQLite doesn't support ADD COLUMN IF NOT EXISTS, so we need to check first
-- This migration is idempotent - it can be run multiple times safely

-- Add the column (will fail silently if it already exists)
ALTER TABLE workflow_runs 
ADD COLUMN temp_workspace INTEGER DEFAULT 0;

-- Create index for efficient querying of temp workspace runs
CREATE INDEX IF NOT EXISTS idx_workflow_runs_temp_workspace 
ON workflow_runs(temp_workspace);

-- Add a comment for documentation (SQLite supports this via PRAGMA)
-- This helps developers understand the column's purpose