# Tool Management & MCP Server API Endpoints

## 🔧 Tool Management Endpoints (`/tools`)

**Purpose**: View and execute tools that are automatically discovered from code and MCP servers.

### Available Endpoints:
```
GET    /tools                     # List all available tools with filtering
GET    /tools/{name}              # Get specific tool details + execution stats  
POST   /tools/{name}/execute      # Execute a tool with parameters
PUT    /tools/{name}              # Update tool configuration (enable/disable, etc.)
DELETE /tools/{name}              # Delete a tool (not recommended for discovered tools)
GET    /tools/categories/list     # List all tool categories
```

### Key Features:
- **Automatic Discovery**: Tools are automatically discovered from `src/tools/` directory
- **104 Code Tools**: Currently discovering all built-in code tools
- **MCP Tools**: Will automatically appear when MCP servers are configured
- **Execution Tracking**: All tool executions are logged with metrics
- **Filtering**: Filter by type (code/mcp), category, agent restrictions

---

## 🌐 MCP Server Management Endpoints (`/mcp`)

**Purpose**: Configure and manage MCP servers that provide external tools.

### Available Endpoints:
```
GET    /mcp/configs                        # List all MCP server configurations
POST   /mcp/configs                        # Create new MCP server configuration
GET    /mcp/configs/{name}                 # Get specific MCP server details
PUT    /mcp/configs/{name}                 # Update MCP server configuration  
DELETE /mcp/configs/{name}                 # Delete MCP server configuration
GET    /mcp/agents/{agent_name}/configs    # Get MCP servers for specific agent
```

### Creating MCP Servers:
```json
POST /mcp/configs
{
  "name": "my-mcp-server",
  "server_type": "stdio",
  "command": ["npx", "my-mcp-package"],
  "agents": ["*"],
  "tools": {"include": ["*"]},
  "environment": {"API_KEY": "your-key"},
  "timeout": 30000,
  "enabled": true,
  "auto_start": true
}
```

---

## 🔄 How It Works Together

1. **Configure MCP Server**: Use `/mcp/configs` endpoints to add external MCP servers
2. **Automatic Tool Discovery**: Once MCP server is configured, its tools automatically appear in `/tools` endpoints
3. **Execute Tools**: Use `/tools/{name}/execute` to run both code and MCP tools uniformly
4. **Monitor Usage**: Check `/tools/{name}` for execution statistics and performance metrics

---

## 📊 Current Status

- ✅ **104 Code Tools** automatically discovered and available
- ✅ **0 MCP Servers** currently configured (use `/mcp/configs` to add them)
- ✅ **Tool Database** properly synced with automatic discovery
- ✅ **API Fully Functional** with comprehensive tool management

---

## 🚀 Next Steps

1. **Add MCP Servers**: Use `POST /mcp/configs` to configure external MCP servers
2. **Watch Tool Count Grow**: Once MCP servers are added, tools will automatically appear in `/tools`
3. **Execute Tools**: Use the unified `/tools/{name}/execute` endpoint for all tools
4. **Monitor Performance**: Check tool execution stats via `/tools/{name}` endpoint

The system now provides a clean separation between:
- **Tools** (automatically discovered, read-only listing, executable)
- **MCP Servers** (manually configured, full CRUD operations)