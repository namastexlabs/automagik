-- MCP Refactor Migration: Create simplified mcp_configs table
-- Epic: NMSTX-253 - Replace complex 2-table MCP system with single-table architecture
-- Component: Core (NMSTX-254)

-- Step 1: Create backup tables for existing data (safety net)
CREATE TABLE IF NOT EXISTS mcp_servers_backup AS 
    SELECT *, NOW() as backup_created_at FROM mcp_servers;

CREATE TABLE IF NOT EXISTS agent_mcp_servers_backup AS 
    SELECT *, NOW() as backup_created_at FROM agent_mcp_servers;

-- Step 2: Create the new simplified mcp_configs table
CREATE TABLE IF NOT EXISTS mcp_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    config JSONB NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Step 3: Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_mcp_configs_name ON mcp_configs(name);
CREATE INDEX IF NOT EXISTS idx_mcp_configs_config ON mcp_configs USING GIN(config);

-- Index for agent filtering (config->'agents' contains agent names)
CREATE INDEX IF NOT EXISTS idx_mcp_configs_agents ON mcp_configs USING GIN((config->'agents'));

-- Index for server type filtering
CREATE INDEX IF NOT EXISTS idx_mcp_configs_server_type ON mcp_configs((config->>'server_type'));

-- Index for enabled configs
CREATE INDEX IF NOT EXISTS idx_mcp_configs_enabled ON mcp_configs((config->>'enabled')) WHERE (config->>'enabled')::boolean = true;

-- Step 4: Add constraints and validation
ALTER TABLE mcp_configs ADD CONSTRAINT chk_config_has_name 
    CHECK (config ? 'name' AND config->>'name' IS NOT NULL);

ALTER TABLE mcp_configs ADD CONSTRAINT chk_config_has_server_type 
    CHECK (config ? 'server_type' AND config->>'server_type' IN ('stdio', 'http'));

-- Ensure stdio servers have command
ALTER TABLE mcp_configs ADD CONSTRAINT chk_stdio_has_command 
    CHECK (config->>'server_type' != 'stdio' OR config ? 'command');

-- Ensure http servers have URL  
ALTER TABLE mcp_configs ADD CONSTRAINT chk_http_has_url 
    CHECK (config->>'server_type' != 'http' OR config ? 'url');

-- Ensure agents is an array
ALTER TABLE mcp_configs ADD CONSTRAINT chk_config_agents_is_array 
    CHECK (config->'agents' IS NULL OR jsonb_typeof(config->'agents') = 'array');

-- Step 5: Add function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_mcp_configs_updated_at_column()
    RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for automatic timestamp updates
DROP TRIGGER IF EXISTS update_mcp_configs_updated_at ON mcp_configs;
CREATE TRIGGER update_mcp_configs_updated_at BEFORE UPDATE ON mcp_configs 
    FOR EACH ROW EXECUTE FUNCTION update_mcp_configs_updated_at_column();

-- Step 6: Add comments explaining the new architecture
COMMENT ON TABLE mcp_configs IS 'Simplified MCP configuration table storing JSON configs (replaces mcp_servers + agent_mcp_servers)';
COMMENT ON COLUMN mcp_configs.name IS 'Unique server identifier';
COMMENT ON COLUMN mcp_configs.config IS 'Complete JSON configuration including server settings, agent assignments, and tool filters';

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