-- Drop legacy MCP tables after migration to single-table architecture
-- Epic: NMSTX-253 - Complete migration to simplified mcp_configs table
-- 
-- The legacy two-table system (mcp_servers + agent_mcp_servers) has been
-- replaced with the unified mcp_configs table that stores JSON configurations.

-- Drop legacy tables if they exist
DROP TABLE IF EXISTS agent_mcp_servers CASCADE;
DROP TABLE IF EXISTS mcp_servers CASCADE;

-- Drop related triggers and functions if they exist
DROP TRIGGER IF EXISTS update_mcp_servers_updated_at ON mcp_servers;
DROP TRIGGER IF EXISTS update_agent_mcp_servers_updated_at ON agent_mcp_servers;
DROP FUNCTION IF EXISTS update_mcp_updated_at_column();

-- Note: The mcp_configs table created by 20250610_230000_create_mcp_configs_table.sql
-- is the current single-table architecture that replaces this legacy system.