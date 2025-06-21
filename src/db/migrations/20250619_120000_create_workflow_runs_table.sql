CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    workflow_name TEXT NOT NULL,
    agent_type TEXT,
    ai_model TEXT,
    task_input TEXT NOT NULL,
    session_id TEXT,
    session_name TEXT,
    git_repo TEXT,
    git_branch TEXT,
    initial_commit_hash TEXT,
    final_commit_hash TEXT,
    git_diff_added_lines INTEGER DEFAULT 0,
    git_diff_removed_lines INTEGER DEFAULT 0,
    git_diff_files_changed INTEGER DEFAULT 0,
    git_diff_stats TEXT DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'pending',
    result TEXT,
    error_message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    completed_at TEXT,
    duration_seconds INTEGER,
    workspace_id TEXT,
    workspace_persistent INTEGER DEFAULT 1,
    workspace_cleaned_up INTEGER DEFAULT 0,
    workspace_path TEXT,
    cost_estimate REAL,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    user_id TEXT,
    metadata TEXT DEFAULT '{}',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    CHECK (status IN ('pending', 'running', 'completed', 'failed', 'killed')),
    CHECK (duration_seconds IS NULL OR duration_seconds >= 0),
    CHECK (input_tokens >= 0 AND output_tokens >= 0 AND total_tokens >= 0)
);

CREATE INDEX IF NOT EXISTS idx_workflow_runs_run_id ON workflow_runs(run_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_session_id ON workflow_runs(session_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_status ON workflow_runs(status);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_workflow_name ON workflow_runs(workflow_name);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_created_at ON workflow_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_user_id ON workflow_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_git_branch ON workflow_runs(git_branch);
CREATE INDEX IF NOT EXISTS idx_workflow_runs_workspace_id ON workflow_runs(workspace_id);