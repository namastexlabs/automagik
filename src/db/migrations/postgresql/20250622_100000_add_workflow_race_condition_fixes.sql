-- Add unique constraint to prevent race conditions on workspace paths
-- This migration enhances the workflow_runs table to prevent concurrent
-- workflow creation race conditions
-- PostgreSQL Compatible Version

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

-- Add partial indexes for performance optimization
-- Note: Cannot use NOW() in index predicate as it's not IMMUTABLE
CREATE INDEX IF NOT EXISTS idx_workflow_runs_completed_recent 
ON workflow_runs(completed_at) 
WHERE status = 'completed';

-- Add index for cleanup operations
CREATE INDEX IF NOT EXISTS idx_workflow_runs_cleanup_candidates 
ON workflow_runs(workspace_cleaned_up, completed_at) 
WHERE workspace_cleaned_up = false AND completed_at IS NOT NULL;

-- Add comments for maintenance
COMMENT ON INDEX idx_workflow_runs_workspace_path_unique IS 'Prevents race conditions by ensuring unique workspace paths';
COMMENT ON INDEX idx_workflow_runs_session_status IS 'Optimizes queries for active workflows by session';
COMMENT ON INDEX idx_workflow_runs_active IS 'Efficiently finds non-terminal workflow states';