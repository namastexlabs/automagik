-- MCP Refactor Migration: Create simplified mcp_configs table
-- Epic: NMSTX-253 - Replace complex 2-table MCP system with single-table architecture
-- Component: Core (NMSTX-254)
-- SQLite Compatible Version

-- Step 1: Create backup tables for existing data (safety net)
-- Note: Only create backup if source tables exist
-- SQLite doesn't support conditional table creation, so we'll skip backups for now

-- Step 2: Create the new simplified mcp_configs table (SQLite compatible)
CREATE TABLE IF NOT EXISTS mcp_configs (
    id TEXT PRIMARY KEY DEFAULT (lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' || substr(lower(hex(randomblob(2))),2) || '-' || substr('89ab',abs(random()) % 4 + 1, 1) || substr(lower(hex(randomblob(2))),2) || '-' || lower(hex(randomblob(6)))),
    name TEXT UNIQUE NOT NULL,
    config TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Step 3: Create indexes for performance (SQLite compatible)
CREATE INDEX IF NOT EXISTS idx_mcp_configs_name ON mcp_configs(name);
CREATE INDEX IF NOT EXISTS idx_mcp_configs_config ON mcp_configs(config);

-- Index for agent filtering using JSON extraction
CREATE INDEX IF NOT EXISTS idx_mcp_configs_agents ON mcp_configs(json_extract(config, '$.agents'));

-- Index for server type filtering
CREATE INDEX IF NOT EXISTS idx_mcp_configs_server_type ON mcp_configs(json_extract(config, '$.server_type'));

-- Index for enabled configs
CREATE INDEX IF NOT EXISTS idx_mcp_configs_enabled ON mcp_configs(json_extract(config, '$.enabled')) WHERE json_extract(config, '$.enabled') = 'true';

-- Step 4: Add basic validation (SQLite has limited constraint support)
-- Note: Advanced JSON validation constraints are not supported in SQLite
-- Validation should be handled at the application level

-- Step 5: Create trigger for automatic timestamp updates (SQLite compatible)
CREATE TRIGGER IF NOT EXISTS update_mcp_configs_updated_at 
    AFTER UPDATE ON mcp_configs
BEGIN
    UPDATE mcp_configs SET updated_at = datetime('now') WHERE id = NEW.id;
END;

-- Step 6: SQLite doesn't support COMMENT statements
-- Table: mcp_configs - Simplified MCP configuration table storing JSON configs (replaces mcp_servers + agent_mcp_servers)
-- Column: name - Unique server identifier
-- Column: config - Complete JSON configuration including server settings, agent assignments, and tool filters

-- Example config structure (for reference):
/*
{
  "name": "example-server",
  "server_type": "stdio",
  "command": ["python", "/path/to/server.py"],
  "agents": ["simple", "discord", "stan"],
  "tools": {
    "include": ["tool1", "tool2"],
    "exclude": ["dangerous_tool"]
  },
  "environment": {
    "API_KEY": "value",
    "DEBUG": "true"
  },
  "timeout": 30000,
  "retry_count": 3,
  "enabled": true,
  "auto_start": true
}
*/