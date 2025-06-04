# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## MCP (Model Context Protocol) Module

The MCP module enables Automagik Agents to dynamically discover and use external tools through the Model Context Protocol standard.

## High-Level Architecture

### Core Components
- **MCPClientManager** (`client.py`): Central manager for all MCP servers, handles lifecycle, configuration persistence, and agent-tool mapping
- **MCPServerManager** (`server.py`): Manages individual server instances, tool discovery, and execution
- **Security Module** (`security.py`): Enforces strict security boundaries with command allowlisting and input validation
- **Models** (`models.py`): Pydantic models for type-safe configuration and data transfer

### Integration Points
- **Agents**: Access MCP tools via `ToolRegistry.register_mcp_tools()`
- **API**: REST endpoints at `/api/routes/mcp_routes.py` for server management
- **Database**: Server configs and agent assignments persisted in PostgreSQL
- **Configuration**: Supports `.mcp.json` files and database-stored configs

## Development Commands

```bash
# Run MCP-specific tests
uv run pytest tests/mcp/ -v

# Test security specifically
uv run pytest tests/mcp/test_mcp_security.py -v

# Run with debug logging to see MCP operations
AM_LOG_LEVEL=DEBUG uv run python -m src

# Check MCP server status
uv run python scripts/check_mcp_status.py
```

## Key Development Patterns

### Adding New MCP Server Support
1. Server commands must be allowlisted in `security.py`
2. Use STDIO type for subprocess-based servers
3. Use HTTP/SSE type for remote servers
4. Always validate server config with Pydantic models

### Security Considerations
- Only these commands are allowed: `npx`, `uvx`, `python3`, `python`, `node`, `docker`, `mcp`
- Server processes run with filtered environment variables
- Input validation prevents command injection
- Paths restricted to `/tmp`, `/var/tmp`, `/opt/mcp`

### Async Patterns
All MCP operations are async:
```python
async with mcp_client_manager:
    tools = await mcp_client_manager.get_tools_for_agent(agent_id)
    result = await mcp_client_manager.call_tool(server_name, tool_name, args)
```

### Error Handling
- Use custom exceptions from `exceptions.py`
- MCPServerError for server operations
- MCPToolError for tool execution
- Always provide context in error messages

## Testing Requirements
- Mock subprocess calls for STDIO servers
- Use httpx.AsyncClient mocks for HTTP servers
- Test security boundaries extensively
- Verify graceful degradation when servers fail