# .mcp.json Configuration Specification

## Overview

The `.mcp.json` file provides MCP (Model Context Protocol) server configuration for Automagik Agents, extending the PydanticAI standard format with agent assignment and tool filtering capabilities.

## File Location

The `.mcp.json` file must be placed at the project root:
```
am-agents-labs-mcp/
├── .mcp.json          ← Configuration file
├── src/
├── tests/
└── ...
```

## Basic Format

The configuration follows the PydanticAI `mcpServers` format with Automagik extensions:

```json
{
  "mcpServers": {
    "server_name": {
      "command": "command_to_run",
      "args": ["arg1", "arg2"],
      "env": {"KEY": "value"},
      "agent_names": ["agent1", "agent2"],
      "allowed_tools": ["tool1", "tool2"],
      "tool_prefix": "prefix"
    }
  }
}
```

## Standard PydanticAI Fields

### STDIO Server Configuration
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
      "env": {
        "DEBUG": "true"
      }
    }
  }
}
```

### HTTP Server Configuration  
```json
{
  "mcpServers": {
    "weather_api": {
      "http_url": "http://localhost:3001/sse",
      "env": {
        "API_KEY": "your_api_key"
      }
    }
  }
}
```

## Automagik Extensions

### Agent Assignment
Control which agents can access each MCP server:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
      "agent_names": ["simple", "genie"]
    },
    "global_tools": {
      "command": "uvx", 
      "args": ["global-mcp-tools"],
      "agent_names": ["*"]  // All agents
    }
  }
}
```

**Agent Assignment Rules**:
- `["*"]` - All agents can access this server
- `["agent1", "agent2"]` - Only specified agents can access
- `[]` or omitted - No agents can access (disabled)

### Tool Filtering
Control which tools each server exposes to agents:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
      "agent_names": ["simple"],
      "allowed_tools": ["read_file", "list_directory"]  // Only these tools
    },
    "unrestricted": {
      "command": "other-mcp-server",
      "agent_names": ["genie"],
      "allowed_tools": []  // All tools (no filtering)
    }
  }
}
```

**Tool Filtering Rules**:
- `[]` or omitted - All tools available (no filtering)
- `["tool1", "tool2"]` - Only specified tools available
- Tools not in the list are filtered out at agent runtime

### Tool Prefixes
Avoid naming conflicts between servers:

```json
{
  "mcpServers": {
    "python_runner": {
      "command": "deno",
      "args": ["run", "python-mcp-server.js"],
      "tool_prefix": "py",
      "agent_names": ["genie"]
    },
    "javascript_runner": {
      "command": "node", 
      "args": ["js-mcp-server.js"],
      "tool_prefix": "js",
      "agent_names": ["genie"]
    }
  }
}
```

**Result**: Agent sees tools as `py_run_code` and `js_run_code` instead of conflicting `run_code` tools.

## Complete Example

```json
{
  "mcpServers": {
    "genie": {
      "command": "uvx",
      "args": ["automagik-tools@latest", "tool", "genie"],
      "env": {
        "AUTOMAGIK_API_KEY": "namastex888", 
        "AUTOMAGIK_BASE_URL": "http://localhost:28881",
        "AUTOMAGIK_TIMEOUT": "1000",
        "AUTOMAGIK_ENABLE_MARKDOWN": "false",
        "OPENAI_API_KEY": "sk-proj-..."
      },
      "agent_names": ["simple", "genie"],
      "allowed_tools": ["search_web", "run_python", "create_linear_task"],
      "tool_prefix": "genie"
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
      "agent_names": ["*"],
      "allowed_tools": ["read_file", "write_file", "list_directory"],
      "tool_prefix": "fs"
    },
    "weather": {
      "http_url": "http://localhost:3001/sse",
      "env": {
        "WEATHER_API_KEY": "your_weather_key"
      },
      "agent_names": ["simple"],
      "allowed_tools": []  // All weather tools
    },
    "development": {
      "command": "python",
      "args": ["-m", "dev_tools.mcp_server"],
      "env": {
        "DEV_MODE": "true"
      },
      "agent_names": ["genie"],
      "allowed_tools": ["debug", "profile", "test_runner"]
    }
  }
}
```

## Validation Rules

### Required Fields
- Each server must have either `command` OR `http_url`
- `command` servers must have `command` field
- `http_url` servers must have `http_url` field

### Field Types
```typescript
interface MCPServerConfig {
  // Core configuration (pick one)
  command?: string;              // For STDIO servers
  args?: string[];               // Command arguments
  http_url?: string;             // For HTTP servers
  
  // Environment and behavior
  env?: Record<string, string>;  // Environment variables
  tool_prefix?: string;          // Tool name prefix
  
  // Automagik extensions
  agent_names?: string[];        // Agent assignment
  allowed_tools?: string[];      // Tool filtering
}
```

### Validation Examples
```json
// ✅ Valid STDIO server
{
  "my_server": {
    "command": "npx",
    "args": ["-y", "my-mcp-server"],
    "agent_names": ["simple"]
  }
}

// ✅ Valid HTTP server  
{
  "remote_server": {
    "http_url": "https://api.example.com/mcp",
    "agent_names": ["*"]
  }
}

// ❌ Invalid - missing required fields
{
  "broken_server": {
    "env": {"KEY": "value"}
    // Missing command OR http_url
  }
}

// ❌ Invalid - conflicting fields
{
  "conflicted_server": {
    "command": "npx",
    "http_url": "http://example.com"
    // Can't have both command and http_url
  }
}
```

## System Integration

### Startup Loading
1. System reads `.mcp.json` from project root
2. Validates configuration format and required fields
3. Syncs valid configurations to `mcp_configs` database table
4. Initializes PydanticAI MCP clients for each agent

### Runtime Behavior
```python
# Agent creation example
def create_agent_with_mcp(agent_name: str) -> Agent:
    configs = get_mcp_configs_for_agent(agent_name)
    mcp_servers = []
    
    for config in configs:
        # Filter tools for this agent
        if config.allowed_tools:
            # TODO: Apply tool filtering in PydanticAI
            pass
            
        # Create appropriate server type
        if config.command:
            server = MCPServerStdio(
                config.command,
                args=config.args or [],
                env=config.env or {},
                tool_prefix=config.tool_prefix
            )
        else:
            server = MCPServerHTTP(
                url=config.http_url,
                tool_prefix=config.tool_prefix
            )
        mcp_servers.append(server)
    
    return Agent(model="openai:gpt-4o", mcp_servers=mcp_servers)
```

### Hot Reload Support
When configurations change via API:
1. Update database immediately
2. Regenerate `.mcp.json` file to keep in sync  
3. Trigger reload for affected agents

## Best Practices

### Agent Assignment Strategy
```json
{
  "mcpServers": {
    // Global utility tools - all agents
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem"],
      "agent_names": ["*"],
      "allowed_tools": ["read_file", "list_directory"]  // Safe operations only
    },
    
    // Specialized tools - specific agents
    "code_execution": {
      "command": "python",
      "args": ["-m", "code_runner"],
      "agent_names": ["genie"],  // Only advanced agents
      "allowed_tools": ["run_python", "install_package"]
    },
    
    // Development tools - disabled in production
    "debug_tools": {
      "command": "debug-mcp-server",
      "agent_names": [],  // Disabled
      "allowed_tools": []
    }
  }
}
```

### Environment Variables
```json
{
  "mcpServers": {
    "secure_api": {
      "command": "api-mcp-server",
      "env": {
        "API_KEY": "${SECURE_API_KEY}",          // From environment
        "BASE_URL": "https://api.production.com", // Hardcoded
        "TIMEOUT": "30000"
      },
      "agent_names": ["simple"]
    }
  }
}
```

### Tool Organization
```json
{
  "mcpServers": {
    // Group related tools by prefix
    "web_tools": {
      "command": "web-mcp-server",
      "tool_prefix": "web",
      "agent_names": ["simple", "genie"],
      "allowed_tools": ["search", "scrape", "screenshot"]
    },
    
    "file_tools": {  
      "command": "file-mcp-server",
      "tool_prefix": "file",
      "agent_names": ["*"],
      "allowed_tools": ["read", "write", "list"]
    }
  }
}
```

## Migration from Current System

### Export Current Configuration
The migration script will export existing `mcp_servers` and `agent_mcp_servers` data into this format:

```python
def export_to_mcp_json():
    servers = get_all_mcp_servers()
    config = {"mcpServers": {}}
    
    for server in servers:
        agent_assignments = get_agent_assignments(server.id)
        
        config["mcpServers"][server.name] = {
            "command": server.command[0] if server.command else None,
            "args": server.command[1:] if server.command else [],
            "http_url": server.http_url,
            "env": server.env or {},
            "agent_names": [a.name for a in agent_assignments],
            "allowed_tools": [],  # Default to no filtering
            "tool_prefix": None
        }
    
    with open(".mcp.json", "w") as f:
        json.dump(config, f, indent=2)
```

This specification provides a clean, simple way to configure MCP servers while maintaining compatibility with PydanticAI and adding the agent assignment and tool filtering capabilities needed by Automagik Agents.