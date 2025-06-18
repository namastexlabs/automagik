-- Create comprehensive tools management table
-- This migration creates the tools table for unified tool management

CREATE TABLE IF NOT EXISTS tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL CHECK (type IN ('code', 'mcp', 'hybrid')),
    description TEXT,
    
    -- For code tools
    module_path TEXT,
    function_name TEXT,
    
    -- For MCP tools  
    mcp_server_name TEXT,
    mcp_tool_name TEXT,
    
    -- Tool metadata
    parameters_schema JSONB,
    capabilities JSONB DEFAULT '[]'::jsonb,
    categories JSONB DEFAULT '[]'::jsonb,
    
    -- Tool configuration
    enabled BOOLEAN DEFAULT TRUE,
    agent_restrictions JSONB DEFAULT '[]'::jsonb,
    
    -- Execution metadata
    execution_count INTEGER DEFAULT 0,
    last_executed_at TIMESTAMP,
    average_execution_time_ms INTEGER DEFAULT 0,
    
    -- Audit fields
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name);
CREATE INDEX IF NOT EXISTS idx_tools_type ON tools(type);
CREATE INDEX IF NOT EXISTS idx_tools_enabled ON tools(enabled);
CREATE INDEX IF NOT EXISTS idx_tools_mcp_server ON tools(mcp_server_name) WHERE mcp_server_name IS NOT NULL;

-- Create GIN indexes for JSONB fields
CREATE INDEX IF NOT EXISTS idx_tools_parameters_schema ON tools USING GIN (parameters_schema);
CREATE INDEX IF NOT EXISTS idx_tools_capabilities ON tools USING GIN (capabilities);
CREATE INDEX IF NOT EXISTS idx_tools_categories ON tools USING GIN (categories);
CREATE INDEX IF NOT EXISTS idx_tools_agent_restrictions ON tools USING GIN (agent_restrictions);

-- Create trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tools_updated_at BEFORE UPDATE ON tools 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Create tool execution log table for metrics
CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tool_id UUID NOT NULL REFERENCES tools(id) ON DELETE CASCADE,
    agent_name VARCHAR(255),
    session_id VARCHAR(255),
    
    -- Execution details
    parameters JSONB,
    context JSONB,
    
    -- Results
    status VARCHAR(50) CHECK (status IN ('success', 'error', 'timeout')),
    result JSONB,
    error_message TEXT,
    execution_time_ms INTEGER,
    
    -- Audit
    executed_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Create indexes for tool executions
CREATE INDEX IF NOT EXISTS idx_tool_executions_tool_id ON tool_executions(tool_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_agent_name ON tool_executions(agent_name);
CREATE INDEX IF NOT EXISTS idx_tool_executions_session_id ON tool_executions(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_executions_status ON tool_executions(status);
CREATE INDEX IF NOT EXISTS idx_tool_executions_executed_at ON tool_executions(executed_at);

-- Tools will be automatically discovered and inserted at startup
-- See src/services/tool_discovery.py for automatic discovery logic

-- Add comment to table
COMMENT ON TABLE tools IS 'Unified tool management table for code and MCP tools';
COMMENT ON COLUMN tools.type IS 'Tool type: code (built-in), mcp (external), hybrid (both)';
COMMENT ON COLUMN tools.parameters_schema IS 'JSON schema for tool parameters validation';
COMMENT ON COLUMN tools.capabilities IS 'Array of tool capabilities/features';
COMMENT ON COLUMN tools.categories IS 'Array of tool categories for organization';
COMMENT ON COLUMN tools.agent_restrictions IS 'Array of agent names that can use this tool (empty = all agents)';