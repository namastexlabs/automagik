# Tool Management API Endpoints

## 🔧 Tool Management Endpoints (`/tools`)

**Purpose**: View and execute tools that are automatically discovered from code and manually created for MCP.

### Available Endpoints:
```
GET    /tools                     # List all available tools with filtering
GET    /tools/{name}              # Get specific tool details + execution stats  
POST   /tools/{name}/execute      # Execute a tool with parameters
POST   /tools/create/mcp          # Create a new MCP tool manually
PUT    /tools/{name}              # Update tool configuration (enable/disable, etc.)
DELETE /tools/{name}              # Delete a tool 
GET    /tools/categories/list     # List all tool categories
GET    /tools/mcp/servers         # List available MCP servers from .mcp.json
```

### Key Features:
- **Code Tools**: Automatically discovered from `src/tools/` directory (104 tools)
- **MCP Tools**: Manually created via `/tools/create/mcp` endpoint
- **Execution Tracking**: All tool executions are logged with metrics
- **Filtering**: Filter by type (code/mcp), category, agent restrictions

### Creating MCP Tools:
```json
POST /tools/create/mcp
{
  "name": "my_custom_tool",
  "description": "Custom MCP tool",
  "mcp_server_name": "git",
  "mcp_tool_name": "git_log",
  "parameters_schema": {
    "type": "object",
    "properties": {
      "path": {"type": "string", "description": "Repository path"}
    },
    "required": ["path"]
  },
  "categories": ["git", "version-control"],
  "enabled": true
}
```

---

## 🌐 MCP Server Configuration (`.mcp.json`)

**Purpose**: MCP servers are configured via `.mcp.json` file in the project root.

### Current Configuration:
- **6 MCP Servers** configured in `.mcp.json`:
  - `mcp-sqlite`: Database operations
  - `git`: Git operations  
  - `linear`: Linear project management
  - `agent-memory`: Agent memory management
  - `deepwiki`: Documentation access
  - `automagik-workflows`: Workflow automation

### .mcp.json Structure:
```json
{
  "mcpServers": {
    "server-name": {
      "command": "npx",
      "args": ["-y", "package-name"],
      "agent_names": ["*"],
      "tools": {"include": ["*"]},
      "env": {"API_KEY": "value"}
    }
  }
}
```

---

## 🔄 How It Works Together

1. **MCP Servers**: Configure in `.mcp.json` file (6 servers already configured)
2. **Code Tools**: Automatically discovered from `src/tools/` (104 tools)
3. **MCP Tools**: Manually create via `POST /tools/create/mcp` endpoint
4. **Execute Tools**: Use `/tools/{name}/execute` to run both code and MCP tools uniformly
5. **Monitor Usage**: Check `/tools/{name}` for execution statistics and performance metrics

---

## 📊 Current Status

- ✅ **104 Code Tools** automatically discovered and available
- ✅ **6 MCP Servers** configured in `.mcp.json` file
- ✅ **0 MCP Tools** manually created (use `/tools/create/mcp` to add them)
- ✅ **Tool Database** properly synced with automatic discovery
- ✅ **API Fully Functional** with proper tool/server separation
- ✅ **Database Issues Fixed** - SQLite compatibility resolved
- ✅ **Clean API Docs** - No more confusing x-api-key requirements

---

## 🚀 Next Steps

1. **Create MCP Tools**: Use `POST /tools/create/mcp` to manually create tools for MCP servers
2. **Check Available Servers**: Use `GET /tools/mcp/servers` to see configured MCP servers
3. **Execute Tools**: Use `/tools/{name}/execute` for both code and MCP tools
4. **Monitor Performance**: Check tool execution stats via `/tools/{name}` endpoint

The system now provides the correct architecture:
- **Code Tools**: Auto-discovered from filesystem
- **MCP Servers**: Configured via `.mcp.json` file  
- **MCP Tools**: Manually created via API endpoints