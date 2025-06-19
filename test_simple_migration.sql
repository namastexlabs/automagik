CREATE TABLE IF NOT EXISTS workflow_runs_test (
    id TEXT PRIMARY KEY,
    run_id TEXT UNIQUE NOT NULL,
    workflow_name TEXT NOT NULL,
    task_input TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);