-- Add unique constraint to prevent race conditions on workspace paths
-- This migration enhances the workflow_runs table to prevent concurrent
-- workflow creation race conditions

-- Create a unique index on workspace_path for non-null values
-- This prevents multiple workflows from using the same workspace simultaneously
CREATE UNIQUE INDEX IF NOT EXISTS idx_workflow_runs_workspace_path_unique 
ON workflow_runs(workspace_path) 
WHERE workspace_path IS NOT NULL;

-- Add a composite index for session_id + status to efficiently check for active sessions
CREATE INDEX IF NOT EXISTS idx_workflow_runs_session_status 
ON workflow_runs(session_id, status) 
WHERE session_id IS NOT NULL;

-- Add an index for finding active (non-terminal) workflows quickly
CREATE INDEX IF NOT EXISTS idx_workflow_runs_active 
ON workflow_runs(status) 
WHERE status IN ('pending', 'running');

-- Add a timestamp trigger to automatically update the updated_at column
-- Note: SQLite doesn't support triggers in the same way as PostgreSQL,
-- so this is handled in application code instead