-- Migration: Add workflow_processes table for process tracking and emergency kill functionality
-- Created: 2025-06-16 13:29:06
-- Purpose: Track active workflow processes to enable emergency termination

-- Create workflow_processes table for tracking active workflow executions
CREATE TABLE IF NOT EXISTS workflow_processes (
    run_id TEXT PRIMARY KEY,
    pid INTEGER,
    status TEXT NOT NULL DEFAULT 'running',
    workflow_name TEXT,
    session_id TEXT,
    user_id TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    workspace_path TEXT,
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    process_info JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_workflow_processes_status 
ON workflow_processes(status);

CREATE INDEX IF NOT EXISTS idx_workflow_processes_started_at 
ON workflow_processes(started_at);

CREATE INDEX IF NOT EXISTS idx_workflow_processes_last_heartbeat 
ON workflow_processes(last_heartbeat);

CREATE INDEX IF NOT EXISTS idx_workflow_processes_session_id 
ON workflow_processes(session_id);

-- Create GIN index for JSONB process_info queries
CREATE INDEX IF NOT EXISTS idx_workflow_processes_process_info 
ON workflow_processes USING gin(process_info);

-- Add constraint to ensure valid status values
ALTER TABLE workflow_processes 
ADD CONSTRAINT IF NOT EXISTS chk_workflow_processes_status_valid 
CHECK (status IN ('running', 'completed', 'failed', 'killed', 'terminated'));

-- Add constraint to ensure process_info is valid JSONB
ALTER TABLE workflow_processes 
ADD CONSTRAINT IF NOT EXISTS chk_workflow_processes_process_info_valid 
CHECK (jsonb_typeof(process_info) = 'object');

-- Add comments for documentation
COMMENT ON TABLE workflow_processes IS 'Tracks active workflow processes for monitoring and emergency termination';
COMMENT ON COLUMN workflow_processes.run_id IS 'Unique identifier for the workflow run';
COMMENT ON COLUMN workflow_processes.pid IS 'System process ID for the workflow execution';
COMMENT ON COLUMN workflow_processes.status IS 'Current status: running, completed, failed, killed, terminated';
COMMENT ON COLUMN workflow_processes.workflow_name IS 'Name of the workflow being executed';
COMMENT ON COLUMN workflow_processes.session_id IS 'Associated session ID from sessions table';
COMMENT ON COLUMN workflow_processes.user_id IS 'User who initiated the workflow';
COMMENT ON COLUMN workflow_processes.workspace_path IS 'File system path to the workflow workspace';
COMMENT ON COLUMN workflow_processes.last_heartbeat IS 'Last time the process was confirmed alive';
COMMENT ON COLUMN workflow_processes.process_info IS 'Additional process metadata (command, environment, etc.)';