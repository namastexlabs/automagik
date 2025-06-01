, # Claude Code Allowed Tools Configuration

## Overview

This directory contains the allowed tools configuration for Claude Code agents used in the LangGraph orchestration system. Each agent has specific tool permissions based on their role and responsibilities in the parallel development architecture.

## Configuration Structure

### Main Settings File
- **`.claude/settings.json`** - Main configuration file with:
  - Base permissions that apply to all agents
  - MCP server configurations
  - Agent profiles referencing individual permission files

### Agent-Specific Permissions
- **`.claude/agents-prompts/alpha-permissions.json`** - Alpha (Orchestrator) permissions
- **`.claude/agents-prompts/beta-permissions.json`** - Beta (Core Builder) permissions
- **`.claude/agents-prompts/delta-permissions.json`** - Delta (API Builder) permissions
- **`.claude/agents-prompts/epsilon-permissions.json`** - Epsilon (Tool Builder) permissions
- **`.claude/agents-prompts/gamma-permissions.json`** - Gamma (Quality Engineer) permissions
- **`.claude/agents-prompts/genie-permissions.json`** - Genie (General Purpose) permissions

## Agent Roles and Permissions

### Alpha Agent - Orchestrator
- **Role**: Epic coordination, task distribution, integration oversight
- **Key Permissions**:
  - Full Linear and Slack MCP access
  - Agent memory operations
  - Git status and log operations
  - Project status monitoring
- **Restrictions**: No direct code modifications, limited bash commands

### Beta Agent - Core Builder
- **Role**: Core framework, agents, memory system development
- **Key Permissions**:
  - Full source code access in `src/agents/` and `src/memory/`
  - Python/uv package management
  - Database query access
  - Unit testing for agent components
- **Restrictions**: Cannot modify API or tools directories

### Delta Agent - API Builder
- **Role**: FastAPI endpoints, authentication, middleware
- **Key Permissions**:
  - Full source code access in `src/api/`
  - HTTP testing tools (curl, http)
  - API testing capabilities
  - Database query access
- **Restrictions**: Cannot modify agent models or tools

### Epsilon Agent - Tool Builder
- **Role**: External integrations, tool development
- **Key Permissions**:
  - Full source code access in `src/tools/`
  - External API testing (WebFetch, curl)
  - DeepWiki MCP access for documentation
  - Tool schema and interface development
- **Restrictions**: Cannot modify core agent or API code

### Gamma Agent - Quality Engineer
- **Role**: Testing, quality assurance, documentation
- **Key Permissions**:
  - Full pytest execution
  - Code quality tools (ruff, coverage)
  - Documentation updates
  - Test suite development
- **Restrictions**: Cannot modify source code outside tests/docs

### Genie Agent - General Purpose
- **Role**: General development, initial epic creation
- **Key Permissions**:
  - Full access to all tools
  - All MCP servers
  - Unrestricted bash commands (with safety denials)
- **Restrictions**: Basic safety restrictions only

## Security Principles

1. **Least Privilege**: Each agent only has permissions needed for their role
2. **Workspace Isolation**: Agents work in separate git worktrees
3. **Safe Denials**: Dangerous commands are explicitly denied for all agents
4. **MCP Scoping**: Agents only get MCP tools relevant to their function

## How Permissions Work

### Allow Rules
- Specific tools/commands the agent can use
- Can use wildcards: `Bash(pytest*)` allows all pytest commands
- MCP tools: `mcp__linear__*` allows all Linear operations

### Deny Rules
- Override allow rules for safety
- Prevent destructive operations
- Applied after allow rules

### Examples
```json
// Allow specific git commands
"Bash(git status*)",
"Bash(git log*)",

// Allow all Linear MCP operations
"mcp__linear__*",

// Deny dangerous operations
"Bash(rm -rf /)",
"Write(/etc/*)"
```

## Integration with Orchestration

The orchestration system uses these permissions when launching Claude Code agents:
1. Alpha coordinates the team using Linear/Slack
2. Beta/Delta/Epsilon work in isolated worktrees
3. Gamma validates quality across all components
4. Genie handles general tasks and epic creation

## Updating Permissions

To modify agent permissions:
1. Edit the specific agent's JSON file in `.claude/agents-prompts/`
2. Test the permissions with a sample task
3. Ensure the agent can still fulfill their role
4. Document any significant changes

## Best Practices

1. **Regular Review**: Audit permissions quarterly
2. **Test Changes**: Verify agents can complete their tasks
3. **Document Additions**: Explain why new permissions are needed
4. **Minimize Scope**: Only grant what's absolutely necessary
5. **Safety First**: Always include safety denials