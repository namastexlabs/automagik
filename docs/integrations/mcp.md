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

**⚠️ IMPORTANT**: These are the **actual implemented endpoints** (verified against source code).

#### Configuration Management

##### List All MCP Configurations
```bash
# GET /api/v1/mcp/configs (list all configurations)
curl -H "X-API-Key: namastex888" http://localhost:8881/api/v1/mcp/configs

# Optional query parameters:
# ?agent_name=simple (filter by agent)
# ?enabled_only=true (only enabled configs)

# Response:
{
  "configs": [
    {
      "id": "1",
      "name": "filesystem",
      "config": {
        "server_type": "stdio",
        "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem"],
        "agents": ["*"],
        "enabled": true
      },
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 1,
  "filtered_by_agent": null
}
```

##### Create MCP Configuration
```bash
# POST /api/v1/mcp/configs (create new configuration)
curl -X POST -H "X-API-Key: namastex888" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "my-server",
       "server_type": "stdio",
       "command": ["python", "-m", "my_mcp_server"],
       "agents": ["simple", "sofia"],
       "tools": {"include": ["*"]},
       "environment": {"API_KEY": "secret"},
       "enabled": true,
       "auto_start": true
     }' \
     http://localhost:8881/api/v1/mcp/configs

# Response: Created configuration object
```

##### Get Specific Configuration
```bash
# GET /api/v1/mcp/configs/{name} (get specific configuration)
curl -H "X-API-Key: namastex888" http://localhost:8881/api/v1/mcp/configs/filesystem

# Response: Single configuration object
```

##### Update Configuration
```bash
# PUT /api/v1/mcp/configs/{name} (update configuration)
curl -X PUT -H "X-API-Key: namastex888" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "filesystem",
       "server_type": "stdio",
       "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
       "agents": ["simple"],
       "enabled": true
     }' \
     http://localhost:8881/api/v1/mcp/configs/filesystem

# Response: Updated configuration object
```

##### Get Agent-Specific Configurations
```bash
# GET /api/v1/mcp/agents/{agent_name}/configs (get configs for specific agent)
curl -H "X-API-Key: namastex888" http://localhost:8881/api/v1/mcp/agents/simple/configs

# Optional query parameters:
# ?enabled_only=true (only enabled configs)

# Response: List of configurations assigned to the agent
```

##### Delete Configuration
```bash
# DELETE /api/v1/mcp/configs/{name} (delete configuration)
curl -X DELETE -H "X-API-Key: namastex888" http://localhost:8881/api/v1/mcp/configs/my-server

# Response: 204 No Content (successful deletion)
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

### Configuration Types

#### STDIO Server Configuration
```json
{
  "name": "filesystem",
  "server_type": "stdio",
  "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
  "agents": ["simple", "sofia"],
  "tools": {
    "include": ["read_file", "write_file", "list_directory"]
  },
  "environment": {
    "NODE_ENV": "production"
  },
  "timeout": 30000,
  "retry_count": 3,
  "enabled": true,
  "auto_start": true
}
```

#### HTTP Server Configuration
```json
{
  "name": "remote-server",
  "server_type": "http",
  "url": "https://api.example.com/mcp",
  "agents": ["*"],
  "tools": {
    "exclude": ["dangerous_operation"]
  },
  "timeout": 60000,
  "enabled": true
}
```

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
# Note: Key value should match AUTOMAGIK_API_KEY in .env file
```

**Problem**: API key not working
```bash
# Check environment variable
echo $AUTOMAGIK_API_KEY
# Verify it matches the key being sent in requests
```

### Configuration Issues

**Problem**: Configuration not loading
```bash
# Check configuration exists
curl -H "X-API-Key: namastex888" http://localhost:8881/api/v1/mcp/configs/my-server
# Should return configuration object

# Check agent-specific configs
curl -H "X-API-Key: namastex888" http://localhost:8881/api/v1/mcp/agents/simple/configs
# Should show configs assigned to 'simple' agent
```

**Problem**: Server not working after configuration
```bash
# Verify configuration is enabled
curl -H "X-API-Key: namastex888" http://localhost:8881/api/v1/mcp/configs/my-server
# Check "enabled": true in response

# Check application logs for MCP startup messages
automagik agents dev
# Look for "MCP configuration loaded" messages
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