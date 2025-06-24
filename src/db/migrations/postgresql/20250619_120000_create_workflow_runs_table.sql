-- Create workflow_runs table for tracking Claude Code workflow executions
-- PostgreSQL Compatible Version

CREATE TABLE IF NOT EXISTS workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id VARCHAR(255) UNIQUE NOT NULL,
    workflow_name VARCHAR(255) NOT NULL,
    agent_type VARCHAR(255),
    ai_model VARCHAR(255),
    task_input TEXT NOT NULL,
    session_id VARCHAR(255),
    session_name VARCHAR(255),
    git_repo TEXT,
    git_branch VARCHAR(255),
    initial_commit_hash VARCHAR(255),
    final_commit_hash VARCHAR(255),
    git_diff_added_lines INTEGER DEFAULT 0,
    git_diff_removed_lines INTEGER DEFAULT 0,
    git_diff_files_changed INTEGER DEFAULT 0,
    git_diff_stats JSONB DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    result TEXT,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    duration_seconds INTEGER,
    workspace_id VARCHAR(255),
    workspace_persistent BOOLEAN DEFAULT true,
    workspace_cleaned_up BOOLEAN DEFAULT false,
    workspace_path TEXT,
    cost_estimate DECIMAL(10,6),
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    user_id VARCHAR(255),
    metadata JSONB DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT chk_workflow_runs_status 
        CHECK (status IN ('pending', 'running', 'completed', 'failed', 'killed')),
    CONSTRAINT chk_workflow_runs_duration_positive 
        CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    CONSTRAINT chk_workflow_runs_tokens_positive 
        CHECK (input_tokens >= 0 AND output_tokens >= 0 AND total_tokens >= 0)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_workflow_runs_run_id ON workflow_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_session_id ON workflow_runs(session_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_workflow_name ON workflow_runs(workflow_name);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_created_at ON workflow_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_user_id ON workflow_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_git_branch ON workflow_runs(git_branch);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_workspace_id ON workflow_runs(workspace_id);

-- JSONB indexes for metadata and git stats
CREATE INDEX IF NOT EXISTS idx_workflow_runs_metadata ON workflow_runs USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_git_stats ON workflow_runs USING GIN(git_diff_stats);

-- Create trigger for automatic timestamp updates
DROP TRIGGER IF EXISTS update_workflow_runs_updated_at ON workflow_runs;
CREATE TRIGGER update_workflow_runs_updated_at 
    BEFORE UPDATE ON workflow_runs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments
COMMENT ON TABLE workflow_runs IS 'Track Claude Code workflow executions with performance and git metadata';
COMMENT ON COLUMN workflow_runs.git_diff_stats IS 'JSONB statistics about git changes made during the workflow';
COMMENT ON COLUMN workflow_runs.metadata IS 'JSONB additional metadata about the workflow execution';