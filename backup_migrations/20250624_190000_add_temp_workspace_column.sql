-- Add temp_workspace column to workflow_runs table
-- This tracks whether a workflow run used a temporary isolated workspace

-- Database-agnostic migration that works with both PostgreSQL and SQLite
-- This migration is idempotent - it can be run multiple times safely

-- Add the column (PostgreSQL syntax with IF NOT EXISTS)
-- SQLite will ignore IF NOT EXISTS but handle duplicate column gracefully
ALTER TABLE workflow_runs 
ADD COLUMN IF NOT EXISTS temp_workspace INTEGER DEFAULT 0;

-- Create index for efficient querying of temp workspace runs
CREATE INDEX IF NOT EXISTS idx_workflow_runs_temp_workspace 
ON workflow_runs(temp_workspace);

-- This column tracks:
-- 0 = Persistent workspace (normal operation)
-- 1 = Temporary workspace (isolated execution)