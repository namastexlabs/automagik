-- MCP Refactor Migration: Create simplified mcp_configs table
-- Epic: NMSTX-253 - Replace complex 2-table MCP system with single-table architecture
-- Component: Core (NMSTX-254)
-- PostgreSQL Compatible Version

-- Step 1: Create backup tables for existing data (safety net)
-- Note: Only create backup if source tables exist
-- PostgreSQL supports conditional table creation

-- Step 2: Create the new simplified mcp_configs table (PostgreSQL compatible)
CREATE TABLE IF NOT EXISTS mcp_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) UNIQUE NOT NULL,
    config JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Step 3: Create indexes for performance (PostgreSQL compatible)
CREATE INDEX IF NOT EXISTS idx_mcp_configs_name ON mcp_configs(name);
CREATE INDEX IF NOT EXISTS idx_mcp_configs_config ON mcp_configs USING GIN(config);

-- Index for agent filtering using JSONB operations
CREATE INDEX IF NOT EXISTS idx_mcp_configs_agents ON mcp_configs USING GIN((config->'agents'));

-- Index for server type filtering
CREATE INDEX IF NOT EXISTS idx_mcp_configs_server_type ON mcp_configs((config->>'server_type'));

-- Index for enabled configs
CREATE INDEX IF NOT EXISTS idx_mcp_configs_enabled ON mcp_configs((config->>'enabled')) WHERE config->>'enabled' = 'true';

-- Step 4: Add basic validation (PostgreSQL has rich constraint support)
-- Add JSON validation constraints (use DO block for idempotency)
DO $$
BEGIN
    -- Add name length constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_mcp_configs_name_length'
    ) THEN
        ALTER TABLE mcp_configs 
        ADD CONSTRAINT chk_mcp_configs_name_length 
        CHECK (length(name) > 0 AND length(name) <= 255);
    END IF;
    
    -- Add config validation constraint if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint 
        WHERE conname = 'chk_mcp_configs_config_valid'
    ) THEN
        ALTER TABLE mcp_configs 
        ADD CONSTRAINT chk_mcp_configs_config_valid 
        CHECK (jsonb_typeof(config) = 'object');
    END IF;
END
$$;

-- Step 5: Create trigger for automatic timestamp updates (PostgreSQL compatible)
-- First create the function if it doesn't exist
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop trigger if exists, then create
DROP TRIGGER IF EXISTS update_mcp_configs_updated_at ON mcp_configs;
CREATE TRIGGER update_mcp_configs_updated_at 
    BEFORE UPDATE ON mcp_configs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Step 6: PostgreSQL supports COMMENT statements
COMMENT ON TABLE mcp_configs IS 'Simplified MCP configuration table storing JSONB configs (replaces mcp_servers + agent_mcp_servers)';
COMMENT ON COLUMN mcp_configs.name IS 'Unique server identifier';
COMMENT ON COLUMN mcp_configs.config IS 'Complete JSONB configuration including server settings, agent assignments, and tool filters';

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