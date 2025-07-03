-- Drop legacy MCP tables after migration to single-table architecture
-- Epic: NMSTX-253 - Complete migration to simplified mcp_configs table
-- 
-- The legacy two-table system (mcp_servers + agent_mcp_servers) has been
-- replaced with the unified mcp_configs table that stores JSON configurations.

-- Drop legacy tables if they exist
DROP TABLE IF EXISTS agent_mcp_servers;
DROP TABLE IF EXISTS mcp_servers;

-- Drop related triggers if they exist
DROP TRIGGER IF EXISTS update_mcp_servers_updated_at;
DROP TRIGGER IF EXISTS update_agent_mcp_servers_updated_at;

-- Note: The mcp_configs table created by 20250610_230000_create_mcp_configs_table.sql
-- is the current single-table architecture that replaces this legacy system.