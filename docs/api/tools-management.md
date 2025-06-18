# Tool Management System

The Automagik Agents Platform includes a comprehensive tool management system that automatically discovers, catalogs, and manages both built-in code tools and external MCP (Model Context Protocol) tools.

## Overview

The tool management system provides:

- **Automatic Discovery**: Scans `src/tools/` directories for code tools and connects to MCP servers
- **Unified API**: Single set of endpoints to manage all tool types
- **Database Persistence**: Stores tool metadata, parameters, and execution statistics
- **Dynamic Execution**: Execute tools via API with proper parameter validation
- **MCP Integration**: Create and manage MCP server configurations
- **Comprehensive Filtering**: Search, filter, and categorize tools

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Code Tools    │    │   MCP Tools     │    │   Tool Database │
│  (src/tools/)   │    │ (External MCPs) │    │  (PostgreSQL)   │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
          ┌─────────────────────────────────────────────┐
          │         Tool Discovery Service              │
          │  • Scans src/tools/ directories            │
          │  • Connects to MCP servers                  │
          │  • Extracts parameter schemas               │
          │  • Categorizes and indexes tools            │
          └─────────────────┬───────────────────────────┘
                            │
          ┌─────────────────────────────────────────────┐
          │              Tool API                       │
          │  • GET /tools (list with filtering)        │
          │  • POST /tools/{name}/execute (execute)    │
          │  • POST /tools/mcp/servers (add MCP)       │
          │  • POST /tools/discover (refresh)          │
          └─────────────────────────────────────────────┘
```

## API Endpoints

### List Tools
```http
GET /tools?tool_type=code&category=messaging&search=email
```

**Parameters:**
- `tool_type`: Filter by type (`code`, `mcp`, `hybrid`)
- `enabled_only`: Show only enabled tools (default: `true`)
- `category`: Filter by category
- `agent_name`: Filter by agent restrictions
- `search`: Search in tool names and descriptions

**Response:**
```json
{
  "tools": [
    {
      "name": "gmail_send_email",
      "type": "code",
      "description": "Send email via Gmail API",
      "module": "src.tools.gmail.tool",
      "parameters": [
        {
          "name": "to",
          "type": "string",
          "description": "Recipient email",
          "required": true
        }
      ]
    }
  ],
  "total_count": 45,
  "filtered_count": 3,
  "categories": ["messaging", "file_operations", "database"]
}
```

### Get Tool Details
```http
GET /tools/gmail_send_email
```

**Response:**
```json
{
  "tool": {
    "name": "gmail_send_email",
    "type": "code",
    "description": "Send email via Gmail API",
    "parameters": [...]
  },
  "stats": {
    "total_executions": 150,
    "successful_executions": 145,
    "failed_executions": 5,
    "success_rate": 96.7,
    "avg_execution_time_ms": 285.5
  }
}
```

### Execute Tool
```http
POST /tools/gmail_send_email/execute
```

**Request:**
```json
{
  "context": {
    "agent_name": "email_assistant",
    "session_id": "session_123"
  },
  "parameters": {
    "to": "user@example.com",
    "subject": "Hello from AI",
    "body": "This email was sent by an AI agent."
  }
}
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "message_id": "msg_abc123",
    "sent_at": "2025-06-18T10:30:00Z"
  }
}
```

### Create Tool
```http
POST /tools
```

**Request:**
```json
{
  "name": "custom_tool",
  "type": "code",
  "description": "Custom tool for specific task",
  "module_path": "src.tools.custom.tool",
  "function_name": "execute_custom",
  "parameters_schema": {
    "type": "object",
    "properties": {
      "input": {"type": "string", "description": "Input data"}
    },
    "required": ["input"]
  },
  "categories": ["custom", "utility"],
  "enabled": true
}
```

### Discover Tools
```http
POST /tools/discover
```

Scans all available tools and syncs them to the database.

**Response:**
```json
{
  "status": "success",
  "discovered": {
    "code_tools": [...],
    "mcp_tools": [...]
  },
  "sync_stats": {
    "created": 12,
    "updated": 3,
    "errors": 0,
    "total": 15
  }
}
```

### Create MCP Server
```http
POST /tools/mcp/servers
```

**Request:**
```json
{
  "name": "github_mcp",
  "server_type": "stdio",
  "config": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"]
  },
  "auto_discover": true
}
```

## Tool Types

### Code Tools
Built-in tools located in `src/tools/` directories:

```
src/tools/
├── airtable/          # Airtable integration
├── gmail/             # Gmail API integration  
├── discord/           # Discord messaging
├── evolution/         # WhatsApp via Evolution API
├── google_drive/      # Google Drive operations
├── notion/            # Notion workspace integration
├── memory/            # Agent memory operations
└── datetime/          # Date/time utilities
```

Each tool directory contains:
- `tool.py` - Main tool functions
- `schema.py` - Parameter schemas
- `interface.py` - Tool interface definitions

### MCP Tools
External tools connected via Model Context Protocol:
- Git operations
- Database queries  
- Linear project management
- Memory/knowledge graphs
- File operations
- Web browsing

## Tool Discovery Process

1. **Startup Discovery**: Automatically runs when the application starts
2. **File System Scanning**: Scans `src/tools/` for Python modules
3. **Function Analysis**: Extracts tool functions and parameter schemas
4. **MCP Connection**: Connects to configured MCP servers
5. **Database Sync**: Stores/updates tool metadata in database
6. **Categorization**: Automatically categorizes tools based on functionality

## Tool Execution

Tools are executed with:
- **Parameter Validation**: Against JSON schemas
- **Context Injection**: RunContext with agent/session info
- **Error Handling**: Comprehensive error capture and logging
- **Metrics Collection**: Execution time and success tracking
- **Result Processing**: Standardized response formatting

## Categories

Tools are automatically categorized:
- `messaging` - Email, SMS, Discord, WhatsApp
- `file_operations` - Upload, download, file processing
- `database` - SQL queries, data operations
- `storage` - Cloud storage, memory operations
- `api` - External API integrations
- `productivity` - Calendar, notion, project management
- `utility` - Date/time, string processing
- `security` - Authentication, validation

## Configuration

### Environment Variables
```bash
# MCP server configurations are stored in database
# No additional environment variables needed for tool discovery
```

### Tool Restrictions
```json
{
  "agent_restrictions": ["email_agent", "assistant_agent"]
}
```

## Monitoring & Metrics

The system tracks:
- **Execution Count**: Number of times each tool is used
- **Success Rate**: Percentage of successful executions
- **Execution Time**: Average, min, max execution times
- **Error Patterns**: Common failure reasons
- **Usage Trends**: Tool popularity over time

## Extension Points

### Adding New Code Tools

1. Create directory in `src/tools/`
2. Implement tool functions with proper signatures
3. Add parameter schemas using Pydantic
4. Restart application (automatic discovery)

### Adding New MCP Tools

1. Use `/tools/mcp/servers` endpoint
2. Provide server configuration
3. Tools are automatically discovered and cataloged

## Best Practices

1. **Function Signatures**: Use `RunContext[Dict]` as first parameter
2. **Async Functions**: Prefer async/await for I/O operations
3. **Error Handling**: Use specific exception types
4. **Documentation**: Include docstrings with parameter descriptions
5. **Schemas**: Provide comprehensive JSON schemas for parameters
6. **Categories**: Use meaningful, searchable category names

## Security

- **API Key Required**: All endpoints require authentication
- **Parameter Validation**: Prevents injection attacks
- **Agent Restrictions**: Limit tool access by agent
- **Audit Logging**: All executions are logged
- **Error Sanitization**: Sensitive data removed from error messages