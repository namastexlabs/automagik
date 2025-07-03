-- Create tool_executions table for tracking tool usage and performance
-- PostgreSQL Compatible Version

CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID,
    agent_name VARCHAR(255),
    session_id VARCHAR(255),
    parameters JSONB,
    context JSONB,
    status VARCHAR(50),
    result TEXT,
    error_message TEXT,
    execution_time_ms INTEGER,
    executed_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_tool_executions_tool_id ON tool_executions(tool_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_agent_name ON tool_executions(agent_name);
CREATE INDEX IF NOT EXISTS idx_tool_executions_session_id ON tool_executions(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_status ON tool_executions(status);
CREATE INDEX IF NOT EXISTS idx_tool_executions_executed_at ON tool_executions(executed_at);

-- JSONB indexes for parameters and context
CREATE INDEX IF NOT EXISTS idx_tool_executions_parameters ON tool_executions USING GIN(parameters);
CREATE INDEX IF NOT EXISTS idx_tool_executions_context ON tool_executions USING GIN(context);

-- Add constraints (use DO block for idempotency)
DO $$
BEGIN
    -- Add status constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_tool_executions_status'
    ) THEN
        ALTER TABLE tool_executions 
        ADD CONSTRAINT chk_tool_executions_status 
        CHECK (status IN ('success', 'error', 'timeout', 'cancelled'));
    END IF;
    
    -- Add execution time constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_tool_executions_execution_time_positive'
    ) THEN
        ALTER TABLE tool_executions 
        ADD CONSTRAINT chk_tool_executions_execution_time_positive 
        CHECK (execution_time_ms >= 0);
    END IF;
END
$$;

-- Add comments
COMMENT ON TABLE tool_executions IS 'Track tool execution history for performance monitoring and debugging';
COMMENT ON COLUMN tool_executions.parameters IS 'JSONB parameters passed to the tool';
COMMENT ON COLUMN tool_executions.context IS 'JSONB execution context and metadata';