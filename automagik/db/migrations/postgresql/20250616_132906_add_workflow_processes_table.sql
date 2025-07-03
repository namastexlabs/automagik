-- Migration: Add workflow_processes table for process tracking and emergency kill functionality
-- Created: 2025-06-16 13:29:06
-- Purpose: Track active workflow processes to enable emergency termination
-- PostgreSQL Compatible Version

-- Create workflow_processes table for tracking active workflow executions
-- Note: Uses JSONB for process_info in PostgreSQL for better performance and querying
CREATE TABLE IF NOT EXISTS workflow_processes (
    run_id VARCHAR(255) PRIMARY KEY,
    pid INTEGER,
    status VARCHAR(50) NOT NULL DEFAULT 'running',
    workflow_name VARCHAR(255),
    session_id VARCHAR(255),
    user_id VARCHAR(255),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    workspace_path TEXT,
    last_heartbeat TIMESTAMPTZ DEFAULT NOW(), 
    process_info JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient queries (PostgreSQL optimized)
CREATE INDEX IF NOT EXISTS idx_workflow_processes_status 
ON workflow_processes(status);

CREATE INDEX IF NOT EXISTS idx_workflow_processes_started_at 
ON workflow_processes(started_at);

CREATE INDEX IF NOT EXISTS idx_workflow_processes_last_heartbeat 
ON workflow_processes(last_heartbeat);

CREATE INDEX IF NOT EXISTS idx_workflow_processes_session_id 
ON workflow_processes(session_id);

-- PostgreSQL-specific JSONB index for process_info
CREATE INDEX IF NOT EXISTS idx_workflow_processes_process_info 
ON workflow_processes USING GIN(process_info);

-- Add constraints for PostgreSQL (use DO block for idempotency)
DO $$
BEGIN
    -- Add status constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_workflow_processes_status'
    ) THEN
        ALTER TABLE workflow_processes 
        ADD CONSTRAINT chk_workflow_processes_status 
        CHECK (status IN ('running', 'completed', 'failed', 'killed', 'timeout'));
    END IF;
END
$$;

-- Create trigger for automatic timestamp updates
DROP TRIGGER IF EXISTS update_workflow_processes_updated_at ON workflow_processes;
CREATE TRIGGER update_workflow_processes_updated_at 
    BEFORE UPDATE ON workflow_processes
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE workflow_processes IS 'Track active workflow processes to enable emergency termination';
COMMENT ON COLUMN workflow_processes.run_id IS 'Unique identifier for the workflow run';
COMMENT ON COLUMN workflow_processes.pid IS 'Process ID of the running workflow';
COMMENT ON COLUMN workflow_processes.process_info IS 'JSONB metadata about the running process';