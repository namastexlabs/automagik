# CLAUDE.md

This file provides MCP (Model Context Protocol) development context for Claude Code working in this directory.

## MCP Development Context

This directory contains the MCP integration layer for Automagik Agents. When working here, you're developing MCP server management, tool discovery, security boundaries, and protocol implementations.

## 🔌 MCP Architecture Overview

### Core Components
- **MCPClientManager** (`client.py`) - Central orchestrator for all MCP servers
- **MCPServerManager** (`server.py`) - Individual server instance management
- **Security Module** (`security.py`) - Command allowlisting and input validation
- **Models** (`models.py`) - Type-safe configuration and data transfer

### Integration Strategy
- **Agent Integration** - Tools discovered via `ToolRegistry.register_mcp_tools()`
- **API Integration** - Management endpoints at `/api/routes/mcp_routes.py`
- **Database Persistence** - Server configs stored in PostgreSQL
- **Configuration Sources** - `.mcp.json` files + database storage

## 🛡️ MCP Security Patterns

### Command Allowlisting
```python
# Only these commands are permitted for MCP servers
ALLOWED_COMMANDS = {
    "npx", "uvx", "python3", "python", "node", "docker", "mcp"
}

# Security enforcement
def validate_server_command(command: str) -> bool:
    base_command = command.split()[0]
    return base_command in ALLOWED_COMMANDS
```

### Path Restrictions
```python
# Restricted execution paths
ALLOWED_PATHS = ["/tmp", "/var/tmp", "/opt/mcp"]

def validate_server_path(path: str) -> bool:
    return any(path.startswith(allowed) for allowed in ALLOWED_PATHS)
```

### Environment Filtering
```python
# Filtered environment variables for server processes
def get_filtered_environment():
    safe_vars = ["PATH", "HOME", "USER", "LANG"]
    return {k: v for k, v in os.environ.items() if k in safe_vars}
```

## 🚀 MCP Server Management Patterns

### Server Lifecycle Management
```python
# Server startup pattern
async def start_mcp_server(config: MCPServerConfig):
    """Start MCP server with proper lifecycle management."""
    
    # 1. Validate configuration
    if not validate_server_command(config.command):
        raise MCPSecurityError(f"Command not allowed: {config.command}")
    
    # 2. Start server process
    process = await asyncio.create_subprocess_exec(
        *config.command.split(),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=get_filtered_environment()
    )
    
    # 3. Initialize MCP client connection
    client = await MCPClient.create(
        read_stream=process.stdout,
        write_stream=process.stdin
    )
    
    # 4. Store in server registry
    self.servers[config.name] = MCPServerManager(
        config=config,
        process=process,
        client=client
    )
```

### Tool Discovery Pattern
```python
async def discover_server_tools(server_name: str) -> List[MCPTool]:
    """Discover tools from MCP server."""
    
    server = self.servers.get(server_name)
    if not server:
        raise MCPServerError(f"Server not found: {server_name}")
    
    try:
        # List available tools from server
        result = await server.client.list_tools()
        
        # Convert to internal tool format
        tools = []
        for tool_info in result.tools:
            tool = MCPTool(
                name=tool_info.name,
                description=tool_info.description,
                input_schema=tool_info.inputSchema,
                server_name=server_name
            )
            tools.append(tool)
            
        return tools
        
    except Exception as e:
        logger.error(f"Tool discovery failed for {server_name}: {e}")
        return []
```

### Tool Execution Pattern
```python
async def call_mcp_tool(
    server_name: str,
    tool_name: str,
    arguments: Dict[str, Any]
) -> MCPToolResult:
    """Execute tool on MCP server with error handling."""
    
    server = self.servers.get(server_name)
    if not server:
        raise MCPServerError(f"Server not found: {server_name}")
    
    try:
        # Validate arguments against tool schema
        tool = await self.get_tool_schema(server_name, tool_name)
        validate_tool_arguments(tool.input_schema, arguments)
        
        # Execute tool on server
        result = await server.client.call_tool(
            name=tool_name,
            arguments=arguments
        )
        
        return MCPToolResult(
            content=result.content,
            is_error=result.isError,
            server_name=server_name,
            tool_name=tool_name
        )
        
    except Exception as e:
        logger.error(f"Tool execution failed: {server_name}.{tool_name}: {e}")
        raise MCPToolError(f"Execution failed: {e}")
```

## 🔧 MCP Configuration Patterns

### Server Configuration Types
```python
# STDIO server (subprocess-based)
stdio_config = MCPServerConfig(
    name="filesystem",
    command="npx @modelcontextprotocol/server-filesystem /tmp",
    type="stdio",
    enabled=True,
    timeout=30
)

# HTTP/SSE server (remote)
http_config = MCPServerConfig(
    name="web-search",
    command="",  # Not used for HTTP
    type="http",
    url="https://api.example.com/mcp",
    enabled=True,
    timeout=30
)
```

### Configuration Loading Pattern
```python
async def load_mcp_configurations():
    """Load MCP configurations from multiple sources."""
    
    configs = []
    
    # 1. Load from .mcp.json files
    for config_file in glob.glob("**/.mcp.json", recursive=True):
        with open(config_file) as f:
            file_configs = json.load(f)
            configs.extend([MCPServerConfig(**cfg) for cfg in file_configs])
    
    # 2. Load from database
    db_configs = await get_mcp_server_configs()
    configs.extend(db_configs)
    
    # 3. Filter enabled configurations
    enabled_configs = [cfg for cfg in configs if cfg.enabled]
    
    return enabled_configs
```

## 🔄 Agent Integration Patterns

### MCP Tool Registration
```python
# In agent tool registry
def register_mcp_tools(self, context: Dict[str, Any]):
    """Register MCP tools for agent use."""
    
    mcp_manager = context.get("mcp_manager")
    if not mcp_manager:
        return
    
    # Get tools for this agent
    agent_tools = await mcp_manager.get_tools_for_agent(
        agent_id=context["agent_id"]
    )
    
    # Register each tool with agent
    for tool in agent_tools:
        self.register_tool(
            name=f"mcp_{tool.server_name}_{tool.name}",
            func=self._create_mcp_tool_wrapper(tool),
            description=tool.description,
            schema=tool.input_schema
        )
```

### MCP Tool Wrapper Pattern
```python
def _create_mcp_tool_wrapper(self, mcp_tool: MCPTool):
    """Create wrapper function for MCP tool."""
    
    async def mcp_tool_wrapper(**kwargs):
        try:
            result = await self.mcp_manager.call_tool(
                server_name=mcp_tool.server_name,
                tool_name=mcp_tool.name,
                arguments=kwargs
            )
            
            if result.is_error:
                return f"Error: {result.content}"
            
            return result.content
            
        except Exception as e:
            return f"MCP tool error: {e}"
    
    return mcp_tool_wrapper
```

## 📊 MCP Monitoring Patterns

### Health Checking
```python
async def check_server_health(server_name: str) -> MCPServerStatus:
    """Check health status of MCP server."""
    
    server = self.servers.get(server_name)
    if not server:
        return MCPServerStatus.NOT_FOUND
    
    try:
        # Ping server with tools list request
        await asyncio.wait_for(
            server.client.list_tools(),
            timeout=5.0
        )
        return MCPServerStatus.HEALTHY
        
    except asyncio.TimeoutError:
        return MCPServerStatus.TIMEOUT
    except Exception:
        return MCPServerStatus.ERROR
```

### Error Recovery Pattern
```python
async def recover_failed_server(server_name: str):
    """Attempt to recover a failed MCP server."""
    
    server = self.servers.get(server_name)
    if not server:
        return False
    
    try:
        # Stop existing server
        await self.stop_server(server_name)
        
        # Wait before restart
        await asyncio.sleep(2)
        
        # Restart with original configuration
        await self.start_server(server.config)
        
        logger.info(f"Successfully recovered MCP server: {server_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to recover server {server_name}: {e}")
        return False
```

## 🧪 MCP Testing Patterns

### Server Testing
```python
@pytest.mark.asyncio
async def test_mcp_server_lifecycle():
    """Test MCP server startup and shutdown."""
    
    config = MCPServerConfig(
        name="test-server",
        command="npx @modelcontextprotocol/server-filesystem /tmp",
        type="stdio"
    )
    
    manager = MCPClientManager()
    
    # Test startup
    await manager.start_server(config)
    assert "test-server" in manager.servers
    
    # Test tool discovery
    tools = await manager.discover_server_tools("test-server")
    assert len(tools) > 0
    
    # Test cleanup
    await manager.stop_server("test-server")
    assert "test-server" not in manager.servers
```

### Security Testing
```python
def test_command_validation():
    """Test MCP security command validation."""
    
    # Valid commands
    assert validate_server_command("npx @mcp/server-filesystem")
    assert validate_server_command("python3 -m mcp.server")
    
    # Invalid commands
    assert not validate_server_command("rm -rf /")
    assert not validate_server_command("curl http://evil.com")
    assert not validate_server_command("bash -c 'malicious code'")
```

### Tool Integration Testing
```python
@pytest.mark.asyncio
async def test_tool_execution():
    """Test MCP tool execution with mocked server."""
    
    # Mock MCP server responses
    mock_server = MockMCPServer()
    mock_server.add_tool("read_file", {"path": "string"})
    
    manager = MCPClientManager()
    manager.servers["mock"] = mock_server
    
    # Test tool execution
    result = await manager.call_tool(
        server_name="mock",
        tool_name="read_file",
        arguments={"path": "/tmp/test.txt"}
    )
    
    assert not result.is_error
    assert result.content is not None
```

## 🔍 MCP Debugging Techniques

```bash
# Enable MCP debug logging
export AUTOMAGIK_LOG_LEVEL=DEBUG
export MCP_DEBUG=true

# Test MCP server standalone
npx @modelcontextprotocol/server-filesystem /tmp

# Check MCP server status via API
curl http://localhost:8000/api/v1/mcp/servers

# Test specific MCP tool
curl -X POST http://localhost:8000/api/v1/mcp/servers/filesystem/tools/read_file \
  -H "Content-Type: application/json" \
  -d '{"path": "/tmp/test.txt"}'
```

## ⚠️ MCP Development Guidelines

### Security First
- Always validate server commands against allowlist
- Restrict server execution paths
- Filter environment variables for server processes
- Validate tool arguments against schemas
- Never trust MCP server responses without validation

### Error Handling
- Implement graceful degradation when servers fail
- Provide meaningful error messages to users
- Log detailed errors for debugging
- Implement automatic recovery for transient failures

### Performance Considerations
- Use connection pooling for HTTP servers
- Implement timeouts for all MCP operations
- Cache tool schemas to avoid repeated discovery
- Monitor server resource usage

### Async Patterns
- All MCP operations must be async
- Use proper context managers for server lifecycle
- Handle concurrent tool executions safely
- Implement proper cleanup in error scenarios

This context focuses specifically on MCP integration development patterns and should be used alongside the global development rules in the root CLAUDE.md.