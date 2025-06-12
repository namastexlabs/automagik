# MCP Refactor Architecture - Simplified Single-Table Design

## Overview

This document outlines the simplified MCP (Model Context Protocol) architecture that replaces the over-engineered multi-table system with a clean, single-table approach.

**📋 IMPLEMENTATION STATUS**: The MCP refactor is **COMPLETED** with configuration management operational. The single-table design has been implemented and the API is functional with 6 configuration endpoints.

## Current Problems (To Be Removed)

### Over-Complex Database Schema
- **Two tables**: `mcp_servers` + `agent_mcp_servers` junction table
- **Hardcoded schema duplication** between PostgreSQL migrations and SQLite provider
- **Complex repository code** for basic CRUD operations
- **Complex server lifecycle management** (multiple management endpoints)

### Over-Engineered API
- **Current system complexity**: Multiple management endpoints with complex validation
- **Agent-server assignment complexity** requiring N+1 queries
- **Missing .mcp.json integration** - everything is API-driven

## Simplified Architecture

### Single Table Design

Replace the complex multi-table approach with a single `mcp_configs` table:

```sql
CREATE TABLE IF NOT EXISTS mcp_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    config JSONB NOT NULL,           -- Complete MCP server config
    agent_names JSONB DEFAULT '[]',  -- Array of agent names
    allowed_tools JSONB DEFAULT '[]', -- Array of tool names to filter
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### .mcp.json Integration

The system loads MCP configuration from `.mcp.json` at project root on startup, following the PydanticAI standard with extensions:

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
      "allowed_tools": ["search_web", "run_python"],
      "tool_prefix": "genie"
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"],
      "agent_names": ["*"],
      "allowed_tools": ["read_file", "write_file", "list_directory"]
    }
  }
}
```

## Key Design Principles

### 1. KISS (Keep It Simple, Stupid)
- **Single table** instead of complex relationships
- **JSON config storage** instead of normalized fields
- **File-first configuration** with database sync

### 2. PydanticAI Integration
Leverage PydanticAI's built-in MCP client capabilities:

```python
from pydantic_ai.mcp import MCPServerStdio, MCPServerHTTP

# Create servers from simplified config
servers = []
for name, config in mcp_configs.items():
    if config.get("command"):
        server = MCPServerStdio(
            config["command"],
            args=config.get("args", []),
            env=config.get("env", {}),
            tool_prefix=config.get("tool_prefix")
        )
    else:
        server = MCPServerHTTP(
            url=config["http_url"],
            tool_prefix=config.get("tool_prefix")
        )
    servers.append(server)

# Agent with MCP servers
agent = Agent('openai:gpt-4.1', mcp_servers=servers)
```

### 3. Agent Tool Filtering
Simple array-based filtering at the agent level:

```python
def get_agent_tools(agent_name: str, mcp_config: dict) -> List[str]:
    # Check if agent is allowed
    agent_names = mcp_config.get("agent_names", [])
    if "*" not in agent_names and agent_name not in agent_names:
        return []
    
    # Apply tool filtering
    allowed_tools = mcp_config.get("allowed_tools", [])
    if not allowed_tools:  # No filtering, allow all
        return discover_all_tools(mcp_config)
    
    return allowed_tools
```

## Simplified API Design

### Current Implementation Status
**⚠️ IMPLEMENTATION NOTE**: The new simplified API has been implemented with 6 configuration endpoints:

```
GET    /api/v1/mcp/configs                      # List all configs
POST   /api/v1/mcp/configs                      # Create new config
GET    /api/v1/mcp/configs/{name}               # Get specific config
PUT    /api/v1/mcp/configs/{name}               # Update config
GET    /api/v1/mcp/agents/{agent_name}/configs  # Get agent configs
DELETE /api/v1/mcp/configs/{name}               # Delete config
```

**Status**: Configuration management API is **IMPLEMENTED** and operational.

### Request/Response Format
```python
# POST /api/v1/mcp/configs
{
    "name": "genie",
    "config": {
        "command": "uvx",
        "args": ["automagik-tools@latest", "tool", "genie"],
        "env": {...}
    },
    "agent_names": ["simple", "genie"],
    "allowed_tools": ["search_web", "run_python"]
}

# Response
{
    "id": 1,
    "name": "genie", 
    "config": {...},
    "agent_names": ["simple", "genie"],
    "allowed_tools": ["search_web", "run_python"],
    "enabled": true,
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
}
```

## System Integration

### Startup Flow
1. **Load .mcp.json** from project root
2. **Sync to database** - upsert all configs to `mcp_configs` table
3. **Initialize PydanticAI clients** for each agent
4. **Ready for requests**

### Agent Creation Flow
```python
def create_agent_with_mcp(agent_name: str, model: str) -> Agent:
    # Get MCP configs for this agent
    configs = get_mcp_configs_for_agent(agent_name)
    
    # Create PydanticAI MCP servers
    mcp_servers = []
    for config in configs:
        if config["command"]:
            server = MCPServerStdio(
                config["command"],
                args=config["args"],
                env=config["env"],
                tool_prefix=config.get("tool_prefix")
            )
        else:
            server = MCPServerHTTP(
                url=config["http_url"],
                tool_prefix=config.get("tool_prefix")
            )
        mcp_servers.append(server)
    
    # Create agent with MCP servers
    return Agent(model, mcp_servers=mcp_servers)
```

### Hot Reload
When configs change via API:
1. **Update database** immediately
2. **Write .mcp.json** to keep file in sync
3. **Trigger agent reload** for affected agents

## Migration Strategy

### Phase 1: Create New System
- Create `mcp_configs` table
- Implement simplified repository functions
- Create basic CRUD API endpoints
- Add .mcp.json loading on startup

### Phase 2: Data Migration
- Export existing `mcp_servers` + `agent_mcp_servers` to new format
- Populate `mcp_configs` table with consolidated data
- Generate initial `.mcp.json` file

### Phase 3: Update Agents
- Modify agent creation to use new PydanticAI integration
- Update tool registry to work with filtered tools
- Test all existing functionality

### Phase 4: Cleanup
- Drop old tables: `mcp_servers`, `agent_mcp_servers`
- Remove old repository files: `src/db/repository/mcp.py`
- Clean up API routes: reduce from 15+ to 4 endpoints
- Remove hardcoded schema from SQLite provider

## Breaking Changes

### Database Schema
- **BREAKING**: `mcp_servers` and `agent_mcp_servers` tables will be dropped
- **MIGRATION REQUIRED**: Existing data must be exported and reimported

### API Endpoints
- **BREAKING**: All current MCP API endpoints will be removed/changed
- **NEW**: Only 4 simple CRUD endpoints will remain

### Agent Integration
- **BREAKING**: Agent MCP integration changes from custom client to PydanticAI
- **BENEFIT**: Simpler, more standard integration

## Implementation Progress

### Current Status
- **Database**: ✅ Single `mcp_configs` table implemented
- **Repository**: ✅ Simplified CRUD operations implemented  
- **API**: ✅ 6 configuration endpoints implemented and operational
- **Schema**: ✅ Unified schema design completed

### Current Integration
- **Configuration**: Database-driven with API management
- **Integration**: PydanticAI MCPServerStdio/HTTP integration
- **Maintenance**: Single table design with JSON configuration storage

### Performance Benefits Achieved
- **Queries**: ✅ Eliminated N+1 queries with single-table design
- **Startup**: ✅ Simplified configuration loading
- **Updates**: ✅ Direct JSON field updates

## Implementation Files

### New Files
- `src/db/repository/mcp_config.py` - Simple CRUD operations
- `src/api/routes/mcp_config_routes.py` - 4 endpoint API
- `src/mcp/config_loader.py` - .mcp.json loading and syncing

### Modified Files  
- `src/agents/models/automagik_agent.py` - PydanticAI MCP integration
- `src/mcp/client.py` - Simplified to use PydanticAI clients
- Migration: `YYYYMMDD_HHMMSS_simplify_mcp_tables.sql`

### Files to Remove
- `src/db/repository/mcp.py` (500+ lines)
- `src/api/routes/mcp_routes.py` (500+ lines) 
- Hardcoded MCP schema from `src/db/providers/sqlite.py`
- `src/db/migrations/20250524_085600_create_mcp_tables.sql`