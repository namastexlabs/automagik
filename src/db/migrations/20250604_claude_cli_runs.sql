-- Claude CLI Runs and Outputs Tables
-- Migration: 20250604_claude_cli_runs.sql

-- Table for tracking Claude CLI runs
CREATE TABLE IF NOT EXISTS claude_cli_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id VARCHAR(255),
    workflow_name VARCHAR(50) NOT NULL,
    branch VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    workspace_path TEXT,
    started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    metadata JSONB DEFAULT '{}',
    execution_time_seconds FLOAT,
    exit_code INTEGER,
    user_id UUID REFERENCES users(id),
    agent_id UUID REFERENCES agents(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for storing Claude CLI outputs
CREATE TABLE IF NOT EXISTS claude_cli_outputs (
    id SERIAL PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES claude_cli_runs(run_id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    output_type VARCHAR(50) NOT NULL,
    content JSONB NOT NULL,
    sequence_number INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table for session persistence
CREATE TABLE IF NOT EXISTS claude_cli_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    run_id UUID NOT NULL REFERENCES claude_cli_runs(run_id),
    workflow_name VARCHAR(50) NOT NULL,
    max_turns INTEGER DEFAULT 2,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- Indexes for performance
CREATE INDEX idx_claude_cli_runs_status ON claude_cli_runs(status);
CREATE INDEX idx_claude_cli_runs_session_id ON claude_cli_runs(session_id);
CREATE INDEX idx_claude_cli_runs_workflow_name ON claude_cli_runs(workflow_name);
CREATE INDEX idx_claude_cli_runs_branch ON claude_cli_runs(branch);
CREATE INDEX idx_claude_cli_runs_user_id ON claude_cli_runs(user_id);
CREATE INDEX idx_claude_cli_runs_agent_id ON claude_cli_runs(agent_id);
CREATE INDEX idx_claude_cli_runs_started_at ON claude_cli_runs(started_at DESC);

CREATE INDEX idx_claude_cli_outputs_run_id ON claude_cli_outputs(run_id);
CREATE INDEX idx_claude_cli_outputs_sequence ON claude_cli_outputs(run_id, sequence_number);
CREATE INDEX idx_claude_cli_outputs_type ON claude_cli_outputs(output_type);

CREATE INDEX idx_claude_cli_sessions_last_used ON claude_cli_sessions(last_used_at DESC);
CREATE INDEX idx_claude_cli_sessions_workflow ON claude_cli_sessions(workflow_name);

-- Add check constraints
ALTER TABLE claude_cli_runs 
ADD CONSTRAINT check_status 
CHECK (status IN ('queued', 'running', 'completed', 'failed', 'cancelled'));

ALTER TABLE claude_cli_outputs
ADD CONSTRAINT check_output_type
CHECK (output_type IN ('text', 'system', 'tool_use', 'result', 'error', 'metadata'));

-- Add trigger to update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_claude_cli_runs_updated_at
BEFORE UPDATE ON claude_cli_runs
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();

-- Comments
COMMENT ON TABLE claude_cli_runs IS 'Tracks Claude CLI workflow executions';
COMMENT ON TABLE claude_cli_outputs IS 'Stores streaming output from Claude CLI executions';
COMMENT ON TABLE claude_cli_sessions IS 'Persists Claude CLI session information for resumption';

COMMENT ON COLUMN claude_cli_runs.run_id IS 'Unique identifier for this run';
COMMENT ON COLUMN claude_cli_runs.session_id IS 'Claude CLI session ID for resumption';
COMMENT ON COLUMN claude_cli_runs.workflow_name IS 'Name of the workflow (architect, implement, test, etc.)';
COMMENT ON COLUMN claude_cli_runs.branch IS 'Git branch being worked on';
COMMENT ON COLUMN claude_cli_runs.status IS 'Current status of the run';
COMMENT ON COLUMN claude_cli_runs.workspace_path IS 'Path to temporary workspace';
COMMENT ON COLUMN claude_cli_runs.metadata IS 'Additional run metadata (request details, etc.)';

COMMENT ON COLUMN claude_cli_outputs.output_type IS 'Type of output (text, system, tool_use, etc.)';
COMMENT ON COLUMN claude_cli_outputs.content IS 'JSON content from Claude CLI streaming output';
COMMENT ON COLUMN claude_cli_outputs.sequence_number IS 'Order of output messages';