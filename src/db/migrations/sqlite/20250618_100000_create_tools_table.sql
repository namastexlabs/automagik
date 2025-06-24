-- Create comprehensive tools management table
-- This migration creates the tools table for unified tool management
-- SQLite Compatible Version

CREATE TABLE IF NOT EXISTS tools (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('code', 'mcp', 'hybrid')),
    description TEXT,
    
    -- For code tools
    module_path TEXT,
    function_name TEXT,
    
    -- For MCP tools  
    mcp_server_name TEXT,
    mcp_tool_name TEXT,
    
    -- Tool metadata (JSON stored as TEXT in SQLite)
    parameters_schema TEXT,
    capabilities TEXT DEFAULT '[]',
    categories TEXT DEFAULT '[]',
    
    -- Tool configuration
    enabled INTEGER DEFAULT 1,
    agent_restrictions TEXT DEFAULT '[]',
    
    -- Execution metadata
    execution_count INTEGER DEFAULT 0,
    last_executed_at TEXT,
    average_execution_time_ms INTEGER DEFAULT 0,
    
    -- Audit fields
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name);
CREATE INDEX IF NOT EXISTS idx_tools_type ON tools(type);
CREATE INDEX IF NOT EXISTS idx_tools_enabled ON tools(enabled);
CREATE INDEX IF NOT EXISTS idx_tools_mcp_server ON tools(mcp_server_name);

-- Create indexes for JSON fields using json_extract
CREATE INDEX IF NOT EXISTS idx_tools_parameters_schema ON tools(parameters_schema);
CREATE INDEX IF NOT EXISTS idx_tools_capabilities ON tools(capabilities);
CREATE INDEX IF NOT EXISTS idx_tools_categories ON tools(categories);
CREATE INDEX IF NOT EXISTS idx_tools_agent_restrictions ON tools(agent_restrictions);

-- Create trigger for updated_at (SQLite compatible)
CREATE TRIGGER IF NOT EXISTS update_tools_updated_at 
    AFTER UPDATE ON tools
BEGIN
    UPDATE tools SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- Tools will be automatically discovered and inserted at startup
-- See src/services/tool_discovery.py for automatic discovery logic

-- SQLite doesn't support COMMENT statements
-- Table: tools - Unified tool management table for code and MCP tools
-- Column: type - Tool type: code (built-in), mcp (external), hybrid (both)
-- Column: parameters_schema - JSON schema for tool parameters validation
-- Column: capabilities - Array of tool capabilities/features
-- Column: categories - Array of tool categories for organization
-- Column: agent_restrictions - Array of agent names that can use this tool (empty = all agents)