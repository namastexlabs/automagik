-- Create MCP servers table to store server configurations and state
CREATE TABLE IF NOT EXISTS mcp_servers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    server_type VARCHAR(20) NOT NULL CHECK (server_type IN ('stdio', 'http')),
    description TEXT,
    
    -- Server connection configuration
    command JSONB, -- Array of command parts for stdio servers
    env JSONB DEFAULT '{}', -- Environment variables as key-value pairs
    http_url VARCHAR(500), -- URL for HTTP servers
    
    -- Server behavior configuration
    auto_start BOOLEAN NOT NULL DEFAULT TRUE,
    max_retries INTEGER NOT NULL DEFAULT 3,
    timeout_seconds INTEGER NOT NULL DEFAULT 30,
    tags JSONB DEFAULT '[]', -- Array of tags for categorization
    priority INTEGER NOT NULL DEFAULT 0,
    
    -- Server state tracking
    status VARCHAR(20) NOT NULL DEFAULT 'stopped' CHECK (status IN ('stopped', 'starting', 'running', 'error', 'stopping')),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    started_at TIMESTAMP,
    last_error TEXT,
    error_count INTEGER NOT NULL DEFAULT 0,
    connection_attempts INTEGER NOT NULL DEFAULT 0,
    last_ping TIMESTAMP,
    
    -- Discovery results
    tools_discovered JSONB DEFAULT '[]', -- Array of discovered tool names
    resources_discovered JSONB DEFAULT '[]', -- Array of discovered resource URIs
    
    -- Audit trail
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_started TIMESTAMP,
    last_stopped TIMESTAMP
);

-- Create junction table for agent-to-server assignments (many-to-many)
CREATE TABLE IF NOT EXISTS agent_mcp_servers (
    id SERIAL PRIMARY KEY,
    agent_id INTEGER NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    mcp_server_id INTEGER NOT NULL REFERENCES mcp_servers(id) ON DELETE CASCADE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    -- Ensure unique agent-server combinations
    UNIQUE(agent_id, mcp_server_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_mcp_servers_name ON mcp_servers(name);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_status ON mcp_servers(status);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_enabled ON mcp_servers(enabled);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_type ON mcp_servers(server_type);
CREATE INDEX IF NOT EXISTS idx_mcp_servers_auto_start ON mcp_servers(auto_start) WHERE enabled = TRUE;

-- Indexes for agent assignments
CREATE INDEX IF NOT EXISTS idx_agent_mcp_servers_agent_id ON agent_mcp_servers(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_mcp_servers_server_id ON agent_mcp_servers(mcp_server_id);

-- Composite index for finding servers by agent and status
CREATE INDEX IF NOT EXISTS idx_mcp_servers_agent_status ON agent_mcp_servers(agent_id, mcp_server_id);

-- Add constraints to ensure configuration consistency
ALTER TABLE mcp_servers ADD CONSTRAINT chk_stdio_has_command 
    CHECK (server_type != 'stdio' OR command IS NOT NULL);
    
ALTER TABLE mcp_servers ADD CONSTRAINT chk_http_has_url 
    CHECK (server_type != 'http' OR http_url IS NOT NULL);

-- Add function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_mcp_updated_at_column()
    RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for automatic timestamp updates
CREATE TRIGGER update_mcp_servers_updated_at BEFORE UPDATE ON mcp_servers 
    FOR EACH ROW EXECUTE FUNCTION update_mcp_updated_at_column();

CREATE TRIGGER update_agent_mcp_servers_updated_at BEFORE UPDATE ON agent_mcp_servers 
    FOR EACH ROW EXECUTE FUNCTION update_mcp_updated_at_column();

-- Add comments explaining the tables' purposes
COMMENT ON TABLE mcp_servers IS 'Stores MCP server configurations, state, and discovery results';
COMMENT ON TABLE agent_mcp_servers IS 'Junction table mapping agents to MCP servers they can access';

COMMENT ON COLUMN mcp_servers.command IS 'Command array for stdio servers (e.g., ["npm", "start"])';
COMMENT ON COLUMN mcp_servers.env IS 'Environment variables as JSON object for stdio servers';
COMMENT ON COLUMN mcp_servers.http_url IS 'Base URL for HTTP-based MCP servers';
COMMENT ON COLUMN mcp_servers.tools_discovered IS 'Array of tool names discovered from the server';
COMMENT ON COLUMN mcp_servers.resources_discovered IS 'Array of resource URIs discovered from the server';
COMMENT ON COLUMN mcp_servers.status IS 'Current operational status of the server';
COMMENT ON COLUMN mcp_servers.enabled IS 'Whether the server is enabled for use';