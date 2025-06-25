-- Add temp_workspace column to workflow_runs table
-- This tracks whether a workflow run used a temporary isolated workspace

-- PostgreSQL supports IF NOT EXISTS for idempotent migrations
ALTER TABLE workflow_runs 
ADD COLUMN IF NOT EXISTS temp_workspace BOOLEAN DEFAULT FALSE;

-- Create index for efficient querying of temp workspace runs
CREATE INDEX IF NOT EXISTS idx_workflow_runs_temp_workspace 
ON workflow_runs(temp_workspace);

-- Add column comment for documentation
COMMENT ON COLUMN workflow_runs.temp_workspace IS 
'Indicates if this workflow run used a temporary isolated workspace instead of git worktree';