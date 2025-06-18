-- SQLite table creation fix for mcp_configs and tools tables
-- This script ensures the required tables exist with proper SQLite syntax

-- Create mcp_configs table if it doesn't exist
CREATE TABLE IF NOT EXISTS mcp_configs (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    name TEXT UNIQUE NOT NULL,
    config TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_mcp_configs_name ON mcp_configs(name);

-- Create tools table if it doesn't exist  
CREATE TABLE IF NOT EXISTS tools (
    id TEXT PRIMARY KEY DEFAULT (hex(randomblob(16))),
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL CHECK (type IN ('code', 'mcp', 'hybrid')),
    description TEXT,
    
    -- For code tools
    module_path TEXT,
    function_name TEXT,
    
    -- For MCP tools  
    mcp_server_name TEXT,
    mcp_tool_name TEXT,
    
    -- Tool metadata
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

CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name);
CREATE INDEX IF NOT EXISTS idx_tools_type ON tools(type);
CREATE INDEX IF NOT EXISTS idx_tools_enabled ON tools(enabled);
CREATE INDEX IF NOT EXISTS idx_tools_mcp_server ON tools(mcp_server_name) WHERE mcp_server_name IS NOT NULL;