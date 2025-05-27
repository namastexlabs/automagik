# MCP Server Integration

This document describes the Model Context Protocol (MCP) server integration capabilities available in Automagik Agents, enabling agents to dynamically load and use external tools and resources.

## Overview

**Sofia** agent supports full MCP server integration, enabling it to:

- Dynamically load MCP servers and their tools
- Refresh server connections on each run
- Manage server lifecycle automatically
- Handle server failures gracefully
- Integrate MCP tools with PydanticAI agents

## Supported Agents

| Agent | MCP Support | Dynamic Loading | Server Management | Tool Integration |
|-------|-------------|-----------------|-------------------|------------------|
| **Simple** | ❌ No | ❌ No | ❌ No | ❌ No |
| **Sofia** | ✅ Full | ✅ Yes | ✅ Yes | ✅ Yes |

> **Note**: Simple agent intentionally excludes MCP integration to maintain minimalism per design requirements.

## MCP Server Management

### Server Configuration

MCP servers are configured in the database and assigned to specific agents:

```sql
-- Example MCP server configuration
INSERT INTO mcp_servers (name, command, args, agent_assignment, is_active) VALUES
('linear-server', 'npx', '["@modelcontextprotocol/server-linear"]', 'sofia', true),
('postgres-server', 'python', '["-m", "mcp_postgres"]', 'sofia', true),
('memory-server', 'python', '["-m", "mcp_agent_memory"]', 'sofia', true);
```

### Dynamic Server Loading

Sofia agent loads MCP servers dynamically on each run:

```python
async def _load_mcp_servers(self) -> List[Any]:
    """Load MCP servers assigned to Sofia agent."""
    try:
        # Refresh MCP client manager to get latest server configs
        refresh_mcp_client_manager()
        
        # Get MCP client manager instance
        from src.mcp.client_manager import get_mcp_client_manager
        mcp_manager = get_mcp_client_manager()
        
        # Get servers assigned to 'sofia' agent
        servers = mcp_manager.get_servers_for_agent('sofia')
        
        # Filter for running servers
        running_servers = [server for server in servers if server.is_running]
        
        logger.info(f"Loaded {len(running_servers)} MCP servers for Sofia agent")
        return running_servers
        
    except Exception as e:
        logger.error(f"Error loading MCP servers: {e}")
        return []
```

### Server Lifecycle Management

```python
async def _initialize_pydantic_agent(self) -> None:
    """Initialize PydanticAI agent with MCP servers."""
    
    # Always load fresh MCP servers
    mcp_servers = await self._load_mcp_servers()
    
    # Check if servers changed since last initialization
    if self._agent_instance is not None and self._last_mcp_servers == mcp_servers:
        return  # No need to recreate agent
    
    # Store current servers for comparison
    self._last_mcp_servers = mcp_servers
    
    # Create new agent instance with updated servers
    self._agent_instance = Agent(
        model=model_name,
        system_prompt=filled_system_prompt,
        tools=tools,
        model_settings=model_settings,
        deps_type=AutomagikAgentsDependencies,
        mcp_servers=mcp_servers  # Pass MCP servers to PydanticAI
    )
```

## Available MCP Servers

### Linear Server

Provides Linear project management integration:

```bash
# Install Linear MCP server
npm install -g @modelcontextprotocol/server-linear

# Configure in database
INSERT INTO mcp_servers (name, command, args, agent_assignment) VALUES
('linear-server', 'npx', '["@modelcontextprotocol/server-linear"]', 'sofia');
```

**Available Tools:**
- `mcp_linear_getIssues` - List Linear issues
- `mcp_linear_createIssue` - Create new issues
- `mcp_linear_updateIssue` - Update existing issues
- `mcp_linear_getProjects` - List projects
- `mcp_linear_createProject` - Create new projects

### PostgreSQL Server

Provides database query capabilities:

```bash
# Install PostgreSQL MCP server
pip install mcp-postgres

# Configure in database
INSERT INTO mcp_servers (name, command, args, agent_assignment) VALUES
('postgres-server', 'python', '["-m", "mcp_postgres"]', 'sofia');
```

**Available Tools:**
- `mcp_postgres_query` - Execute SQL queries
- `mcp_postgres_schema` - Get database schema
- `mcp_postgres_tables` - List database tables

### Agent Memory Server

Provides graph memory integration:

```bash
# Install Agent Memory MCP server
pip install mcp-agent-memory

# Configure in database
INSERT INTO mcp_servers (name, command, args, agent_assignment) VALUES
('memory-server', 'python', '["-m", "mcp_agent_memory"]', 'sofia');
```

**Available Tools:**
- `mcp_agent-memory_search_memory_nodes` - Search memory nodes
- `mcp_agent-memory_search_memory_facts` - Search memory facts
- `mcp_agent-memory_add_memory` - Add new memories
- `mcp_agent-memory_get_episodes` - Get recent episodes

## Usage

### Automatic Tool Discovery

Sofia agent automatically discovers and registers MCP tools:

```python
# Sofia agent automatically has access to MCP tools
response = await sofia_agent.run(
    "Create a Linear issue for implementing new feature"
)

# Agent can use mcp_linear_createIssue tool automatically
```

### Manual Tool Usage

```python
# Direct tool usage (if needed)
from src.mcp.client_manager import get_mcp_client_manager

mcp_manager = get_mcp_client_manager()
linear_server = mcp_manager.get_server('linear-server')

# Use Linear tools directly
result = await linear_server.call_tool('mcp_linear_createIssue', {
    'title': 'New Feature Request',
    'teamId': 'team-id',
    'description': 'Implement new functionality'
})
```

### CLI Usage

```bash
# Sofia agent automatically has MCP tools available
automagik agents run sofia \
  --input "Search for recent Linear issues and create a summary"

# Agent will use mcp_linear_getIssues automatically
```

## Configuration

### Environment Variables

Configure MCP servers with environment variables:

```bash
# Linear MCP server
export LINEAR_API_KEY="your-linear-api-key"

# PostgreSQL MCP server  
export DATABASE_URL="postgresql://user:pass@localhost/db"

# Agent Memory MCP server
export GRAPHITI_API_KEY="your-graphiti-key"
```

### Database Configuration

MCP servers are managed in the database:

```sql
-- MCP servers table structure
CREATE TABLE mcp_servers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    command VARCHAR(255) NOT NULL,
    args JSONB,
    env_vars JSONB,
    agent_assignment VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Agent Assignment

Assign servers to specific agents:

```python
# Sofia agent gets all servers assigned to 'sofia'
servers = mcp_manager.get_servers_for_agent('sofia')

# Simple agent intentionally gets no MCP servers
# (maintains minimalism)
```

## Error Handling

### Server Connection Failures

```python
async def _load_mcp_servers(self) -> List[Any]:
    """Load MCP servers with error handling."""
    try:
        servers = mcp_manager.get_servers_for_agent('sofia')
        running_servers = []
        
        for server in servers:
            try:
                if server.is_running:
                    running_servers.append(server)
                else:
                    logger.warning(f"MCP server {server.name} is not running")
            except Exception as e:
                logger.error(f"Error checking server {server.name}: {e}")
                
        return running_servers
        
    except Exception as e:
        logger.error(f"Failed to load MCP servers: {e}")
        return []  # Graceful fallback to no MCP servers
```

### Tool Execution Errors

```python
# MCP tool errors are handled by PydanticAI
try:
    result = await sofia_agent.run("Create a Linear issue")
except MCPToolError as e:
    logger.error(f"MCP tool error: {e}")
    return AgentResponse(
        text="Sorry, I couldn't complete that action. Please try again.",
        success=False,
        error_message=str(e)
    )
```

### Server Restart Handling

```python
# Servers are refreshed on each run
async def run(self, user_input: str, **kwargs) -> AgentResponse:
    """Run Sofia agent with fresh MCP servers."""
    
    # Always refresh MCP servers before running
    await self._initialize_pydantic_agent()
    
    # Continue with normal execution
    result = await self._agent_instance.run(user_input, ...)
```

## Monitoring and Debugging

### Server Status Checking

```python
# Check MCP server status
from src.mcp.client_manager import get_mcp_client_manager

mcp_manager = get_mcp_client_manager()

for server_name in ['linear-server', 'postgres-server', 'memory-server']:
    server = mcp_manager.get_server(server_name)
    if server:
        print(f"{server_name}: {'Running' if server.is_running else 'Stopped'}")
    else:
        print(f"{server_name}: Not found")
```

### Debug Logging

Enable debug logging for MCP integration:

```python
import logging

# Enable MCP debug logging
logging.getLogger('src.mcp').setLevel(logging.DEBUG)
logging.getLogger('mcp').setLevel(logging.DEBUG)

# Enable Sofia agent debug logging
logging.getLogger('src.agents.simple.sofia').setLevel(logging.DEBUG)
```

### Tool Usage Tracking

```python
# Track MCP tool usage in agent responses
response = await sofia_agent.run("Create a Linear issue")

# Check which MCP tools were used
mcp_tools_used = [
    call for call in response.tool_calls 
    if call.get('tool_name', '').startswith('mcp_')
]

logger.info(f"MCP tools used: {[tool['tool_name'] for tool in mcp_tools_used]}")
```

## Best Practices

### Server Management

1. **Monitor server health** regularly
2. **Restart failed servers** automatically
3. **Use environment variables** for sensitive configuration
4. **Assign servers appropriately** to agents

### Performance Optimization

1. **Cache server connections** when possible
2. **Limit concurrent tool calls** to prevent overload
3. **Use connection pooling** for database servers
4. **Monitor resource usage** of MCP servers

### Security

1. **Validate MCP tool inputs** before execution
2. **Use secure environment variables** for API keys
3. **Limit server permissions** appropriately
4. **Audit MCP tool usage** regularly

## Examples

### Linear Integration

```python
# Sofia agent with Linear MCP integration
response = await sofia_agent.run(
    "Create a Linear issue titled 'Fix authentication bug' "
    "in the Backend team with high priority"
)

# Agent automatically uses mcp_linear_createIssue
```

### Database Queries

```python
# Sofia agent with PostgreSQL MCP integration
response = await sofia_agent.run(
    "Show me the top 10 users by activity in the last month"
)

# Agent automatically uses mcp_postgres_query
```

### Memory Search

```python
# Sofia agent with Memory MCP integration
response = await sofia_agent.run(
    "Search my memory for information about the user's preferences"
)

# Agent automatically uses mcp_agent-memory_search_memory_nodes
```

## Troubleshooting

### Common Issues

1. **Server not starting**: Check command and arguments in database
2. **Tools not available**: Verify server is running and assigned to agent
3. **Authentication errors**: Check environment variables for API keys
4. **Connection timeouts**: Increase timeout settings or restart servers

### Diagnostic Commands

```bash
# Check MCP server status
automagik mcp status

# Restart MCP servers
automagik mcp restart

# Test MCP server connection
automagik mcp test linear-server
```

### Testing

Test MCP integration:

```bash
# Run MCP integration tests
python -m pytest tests/agents/sofia/test_mcp.py -v

# Test specific MCP server
python -m pytest tests/mcp/test_linear_integration.py -v
```

## Future Enhancements

- **MCP server auto-discovery** from package managers
- **Server health monitoring** dashboard
- **Dynamic server scaling** based on load
- **MCP server marketplace** integration
- **Cross-agent server sharing** capabilities
- **Server performance analytics** and optimization 