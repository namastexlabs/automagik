-- Create comprehensive tools management table
-- This migration creates the tools table for unified tool management
-- PostgreSQL Compatible Version

CREATE TABLE IF NOT EXISTS tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    type VARCHAR(50) NOT NULL CHECK (type IN ('code', 'mcp', 'hybrid')),
    description TEXT,
    
    -- For code tools
    module_path TEXT,
    function_name VARCHAR(255),
    
    -- For MCP tools  
    mcp_server_name VARCHAR(255),
    mcp_tool_name VARCHAR(255),
    
    -- Tool metadata (JSON stored as JSONB in PostgreSQL)
    parameters_schema JSONB,
    capabilities JSONB DEFAULT '[]',
    categories JSONB DEFAULT '[]',
    
    -- Tool configuration
    enabled BOOLEAN DEFAULT true,
    agent_restrictions JSONB DEFAULT '[]',
    
    -- Execution metadata
    execution_count INTEGER DEFAULT 0,
    last_executed_at TIMESTAMPTZ,
    average_execution_time_ms INTEGER DEFAULT 0,
    
    -- Audit fields
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Create indexes for performance (PostgreSQL optimized)
CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name);
CREATE INDEX IF NOT EXISTS idx_tools_type ON tools(type);
CREATE INDEX IF NOT EXISTS idx_tools_enabled ON tools(enabled);
CREATE INDEX IF NOT EXISTS idx_tools_mcp_server ON tools(mcp_server_name);

-- Create JSONB indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_tools_parameters_schema ON tools USING GIN(parameters_schema);
CREATE INDEX IF NOT EXISTS idx_tools_capabilities ON tools USING GIN(capabilities);
CREATE INDEX IF NOT EXISTS idx_tools_categories ON tools USING GIN(categories);
CREATE INDEX IF NOT EXISTS idx_tools_agent_restrictions ON tools USING GIN(agent_restrictions);

-- Create indexes for specific JSONB queries
CREATE INDEX IF NOT EXISTS idx_tools_capabilities_array ON tools USING GIN((capabilities));
CREATE INDEX IF NOT EXISTS idx_tools_categories_array ON tools USING GIN((categories));

-- Add constraints for data validation (use DO block for idempotency)
DO $$
BEGIN
    -- Add name length constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_tools_name_length'
    ) THEN
        ALTER TABLE tools 
        ADD CONSTRAINT chk_tools_name_length 
        CHECK (length(name) > 0 AND length(name) <= 255);
    END IF;
    
    -- Add execution count constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_tools_execution_count_positive'
    ) THEN
        ALTER TABLE tools 
        ADD CONSTRAINT chk_tools_execution_count_positive 
        CHECK (execution_count >= 0);
    END IF;
    
    -- Add execution time constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_tools_avg_execution_time_positive'
    ) THEN
        ALTER TABLE tools 
        ADD CONSTRAINT chk_tools_avg_execution_time_positive 
        CHECK (average_execution_time_ms >= 0);
    END IF;
END
$$;

-- Create trigger for updated_at (PostgreSQL compatible)
DROP TRIGGER IF EXISTS update_tools_updated_at ON tools;
CREATE TRIGGER update_tools_updated_at 
    BEFORE UPDATE ON tools
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comments for documentation
COMMENT ON TABLE tools IS 'Comprehensive tools management table for unified tool discovery and execution';
COMMENT ON COLUMN tools.type IS 'Tool type: code (Python function), mcp (MCP server tool), hybrid (both)';
COMMENT ON COLUMN tools.parameters_schema IS 'JSONB schema definition for tool parameters';
COMMENT ON COLUMN tools.capabilities IS 'JSONB array of tool capabilities and features';
COMMENT ON COLUMN tools.categories IS 'JSONB array of tool categories for organization';
COMMENT ON COLUMN tools.agent_restrictions IS 'JSONB array of agents allowed to use this tool';

-- Tools will be automatically discovered and inserted at startup
-- See src/services/tool_discovery.py for automatic discovery logic