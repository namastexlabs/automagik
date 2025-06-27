-- Migration: Add workflow_processes table for process tracking and emergency kill functionality
-- Created: 2025-06-16 13:29:06
-- Purpose: Track active workflow processes to enable emergency termination
-- Compatible: SQLite and PostgreSQL

-- Create workflow_processes table for tracking active workflow executions
-- Note: Uses TEXT for process_info in SQLite, JSONB in PostgreSQL (handled by provider)
-- SQLite-compatible timestamps using datetime('now')
CREATE TABLE IF NOT EXISTS workflow_processes (
    run_id TEXT PRIMARY KEY,
    pid INTEGER,
    status TEXT NOT NULL DEFAULT 'running',
    workflow_name TEXT,
    session_id TEXT,
    user_id TEXT,
    started_at TEXT DEFAULT (datetime('now')),
    workspace_path TEXT,
    last_heartbeat TEXT DEFAULT (datetime('now')), 
    process_info TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Create indexes for efficient queries (compatible with both databases)
CREATE INDEX IF NOT EXISTS idx_workflow_processes_status 
ON workflow_processes(status);

CREATE INDEX IF NOT EXISTS idx_workflow_processes_started_at 
ON workflow_processes(started_at);

CREATE INDEX IF NOT EXISTS idx_workflow_processes_last_heartbeat 
ON workflow_processes(last_heartbeat);

CREATE INDEX IF NOT EXISTS idx_workflow_processes_session_id 
ON workflow_processes(session_id);