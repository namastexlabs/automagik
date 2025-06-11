# MCP Integration Documentation

This document provides comprehensive information about the Model Context Protocol (MCP) integration in the Automagik Agents framework.

## Overview

The MCP integration allows Automagik Agents to communicate with external tools and services through standardized MCP servers. This enables dynamic tool discovery, execution, and resource access while maintaining security and modularity.

## Architecture

### Core Components

- **MCPClientManager** (`src/mcp/client.py`): Manages MCP client connections and server lifecycle
- **MCPServerManager** (`src/mcp/server.py`): Handles MCP server configurations and status
- **MCP Models** (`src/mcp/models.py`): Pydantic data models for MCP entities
- **MCP Exceptions** (`src/mcp/exceptions.py`): Custom error handling for MCP operations
- **MCP Repository** (`src/db/repository/mcp.py`): Database operations for MCP configurations
- **MCP API Routes** (`src/api/routes/mcp_routes.py`): REST API endpoints for MCP management

### Database Schema

The MCP integration includes new database tables:

```sql
-- Migration: 20250524_085600_create_mcp_tables.sql
-- Tables: mcp_servers, mcp_tools, mcp_resources (and related indexes)
```

## Getting Started

### Import Pattern

```python
# ✅ CORRECT: Import from src.mcp package
from src.mcp.client import get_mcp_manager
from src.db.repository.mcp import get_mcp_config_by_name, list_mcp_configs
from src.db.models import MCPConfig

# ✅ CORRECT: Initialize client manager
manager = await get_mcp_manager()
# Configurations are auto-loaded from database
```

### Server Configuration

MCP servers are configured in the database and can be managed via API or directly through the repository layer.

```python
# Example server configuration
server_config = MCPServerConfig(
    name="filesystem",
    server_type=MCPServerType.STDIO,
    command=["secure-filesystem-server"],
    allowed_directories=["/home/namastex/workspace/am-agents-labs"],
    auto_start=True
)
```

## API Endpoints

**Base URL**: `http://localhost:8881/api/v1/mcp/`

### Authentication

All MCP API endpoints (except health) require authentication:

```bash
# Headers required for authenticated endpoints
X-API-Key: namastex888
```

### Available Endpoints

#### Health Check
```bash
# GET /api/v1/mcp/health (no authentication required)
curl http://localhost:8881/api/v1/mcp/health

# Response:
{
  "status": "healthy",
  "servers_total": 2,
  "servers_running": 2,
  "servers_error": 0,
  "tools_available": 22,
  "resources_available": 0
}
```

#### Server Management
```bash
# GET /api/v1/mcp/servers (list all servers)
curl -H "X-API-Key: namastex888" http://localhost:8881/api/v1/mcp/servers

# GET /api/v1/mcp/servers/{server_name} (get specific server)
curl -H "X-API-Key: namastex888" http://localhost:8881/api/v1/mcp/servers/filesystem

# Response includes server status, tools, and configuration
```

#### Tool Management
```bash
# GET /api/v1/mcp/tools (list all available tools)
curl -H "X-API-Key: namastex888" http://localhost:8881/api/v1/mcp/tools

# POST /api/v1/mcp/tools/{tool_name}/call (execute tool)
curl -X POST -H "X-API-Key: namastex888" \
     -H "Content-Type: application/json" \
     -d '{"arguments": {"path": "/home/namastex/workspace/am-agents-labs"}}' \
     http://localhost:8881/api/v1/mcp/tools/list_directory/call
```

## Testing Results

### Integration Status ✅

**Comprehensive testing completed across all components:**

- ✅ **Core Modules** (NAM-13): All imports, models, and error handling working
- ✅ **API Integration** (NAM-14): All endpoints authenticated and responding correctly  
- ✅ **Database Layer** (NAM-15): Migration applied, all CRUD operations functional
- ✅ **Breaking Changes** (NAM-15): No existing functionality impacted

### Current Deployment Status

```bash
# Server Information
Port: 8881
Servers Running: 2 (filesystem, test_filesystem)
Tools Available: 22 total
Authentication: X-API-Key header required
Health Status: Fully operational
```

### Verified Integrations

1. **Filesystem MCP Server**: Provides file system access with directory restrictions
2. **Test Filesystem Server**: Development/testing server
3. **Agent Integration**: All agents can access MCP tools via tool registry
4. **API Access**: Full REST API for external integrations

## Error Handling

### Common HTTP Status Codes

- `200 OK`: Successful operation
- `401 Unauthorized`: Missing or invalid API key
- `404 Not Found`: Server or tool not found
- `500 Internal Server Error`: MCP server communication error

### Error Response Format

```json
{
  "detail": "Error description",
  "error_code": "MCP_ERROR_CODE",
  "server_name": "affected_server"
}
```

## Troubleshooting

### Server Port Issues

**Problem**: Cannot connect to MCP API
```bash
# Solution: Verify server is running on correct port
curl http://localhost:8881/api/v1/mcp/health
# Expected: {"status": "healthy"}
```

**Problem**: Wrong port in documentation/configuration
```bash
# Check actual server port in logs
automagik agents dev
# Look for: "INFO: Uvicorn running on http://0.0.0.0:8881"
```

### Authentication Issues

**Problem**: 401 Unauthorized responses
```bash
# Solution: Include correct API key header
curl -H "X-API-Key: namastex888" http://localhost:8881/api/v1/mcp/servers
# Note: Key value should match AM_API_KEY in .env file
```

**Problem**: API key not working
```bash
# Check environment variable
echo $AM_API_KEY
# Verify it matches the key being sent in requests
```

### Server Connection Issues

**Problem**: MCP servers not starting
```bash
# Check server status via API
curl -H "X-API-Key: namastex888" http://localhost:8881/api/v1/mcp/servers
# Look for "status": "error" in response

# Check application logs
automagik agents dev
# Look for MCP server startup messages
```

**Problem**: Tools not available
```bash
# Verify tools are discovered
curl -H "X-API-Key: namastex888" http://localhost:8881/api/v1/mcp/tools
# Should return list of available tools

# Check individual server status
curl -H "X-API-Key: namastex888" http://localhost:8881/api/v1/mcp/servers/filesystem
```

### Import Issues

**Problem**: Cannot import MCP classes
```python
# ❌ WRONG: These imports will fail
from src.mcp.client import MCPClient  # MCPClient doesn't exist
from mcp import MCPClientManager  # Wrong package
from src.mcp import MCPClientManager  # Old import pattern

# ✅ CORRECT: Use these imports
from src.mcp.client import get_mcp_manager
from src.db.repository.mcp import get_mcp_config_by_name, list_mcp_configs
from src.db.models import MCPConfig
```

**Problem**: Module not found errors
```bash
# Ensure you're in the correct environment
source .venv/bin/activate
cd /home/namastex/workspace/am-agents-labs

# Verify MCP module exists
python -c "from src.mcp import MCPClientManager; print('Import successful')"
```

### Database Issues

**Problem**: MCP tables not found
```bash
# Check if migration was applied
automagik agents dev
# Look for migration messages in startup logs

# Verify tables exist manually
psql -h localhost -p 5432 -U automagik -d automagik
\dt mcp_*
```

### Async Context Issues

**Problem**: "Attempted to exit cancel scope in different task" errors
```python
# This indicates improper async context management
# MCP servers use async context managers and must be handled properly
# The framework handles this automatically, but custom implementations should be careful
```

## Development Patterns

### Adding New MCP Servers

1. Create server configuration in database via API or repository
2. Restart application to load new server
3. Verify server starts via health endpoint
4. Test tool discovery and execution

### Custom Tool Integration

1. Implement tools in MCP server following MCP specification
2. Register server with automagik agents
3. Tools become available automatically via tool registry
4. Test integration via API endpoints

## Best Practices

### Security

- Always validate server configurations before enabling
- Use restricted directory access for filesystem servers
- Implement proper authentication for sensitive tools
- Monitor server status and disable problematic servers

### Performance

- Limit concurrent tool executions per server
- Implement timeouts for long-running operations
- Monitor resource usage of MCP server processes
- Cache tool discovery results when appropriate

### Monitoring

- Use health endpoint for system monitoring
- Track server uptime and error rates
- Monitor tool execution success/failure rates
- Set up alerts for server failures

## Related Documentation

- [Architecture](../architecture/overview.md): Overall system architecture
- [API Documentation](../development/api.md): General API usage patterns
- [Agent Overview](../development/agents-overview.md): How agents integrate with MCP tools
- [Configuration](../getting-started/configuration.md): Environment and server configuration 