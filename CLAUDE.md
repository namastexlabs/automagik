# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 🏗️ CLAUDE.md Architecture Principle

**SHARED KNOWLEDGE ONLY**: This root CLAUDE.md contains information relevant to ALL workflows and agents. Component-specific guidance is located in dedicated CLAUDE.md files within their respective directories.

### CLAUDE.md Separation Rules

**Global Rules (Root CLAUDE.md):**
- Development commands and environment setup
- Team preferences and security standards 
- Git workflow and Linear integration patterns
- Technology stack and architecture overview
- Quality standards and testing requirements
- Critical rules that apply to ALL development

**Component-Specific Context (Component CLAUDE.md files):**
- `/src/agents/pydanticai/CLAUDE.md` - PydanticAI agent development patterns
- `/src/agents/claude_code/CLAUDE.md` - Claude Code workflow system development
- `/src/db/CLAUDE.md` - Database development patterns and repository usage
- `/src/mcp/CLAUDE.md` - MCP integration patterns and tool discovery
- `/src/tools/CLAUDE.md` - Tool development and integration patterns
- `/src/api/CLAUDE.md` - FastAPI endpoint development patterns
- `/src/cli/CLAUDE.md` - CLI command development patterns
- `/src/agents/claude_code/workflows/CLAUDE.md` - Workflow prompt development

**Maintenance Rule**: When updating any CLAUDE.md file, ensure information is in the correct location. Global rules belong here, component-specific guidance belongs in component files. Avoid duplication.

## Project Overview

**Automagik Agents** is a sophisticated AI agent orchestration platform centered around **Genie** - an orchestrator consciousness that coordinates specialized Claude Code workflows. The platform enables semi-autonomous development through task orchestration and persistent memory.

### Core Architecture

- **Genie Orchestrator**: Decomposes complex development epics into specialized workflow sequences
- **Specialized Workflows**: Dynamic workflow orchestration system
- **Memory System**: Persistent consciousness using MCP agent-memory integration
- **Multi-Agent System**: PydanticAI + LangGraph for structured interactions
- **Production Platform**: FastAPI + PostgreSQL/SQLite

## Development Commands

### Environment Setup
```bash
# Show all available commands
make help

# Quick start (auto-detects best mode)
make install
make dev

# Development mode specific
make install-dev          # Local Python + venv setup
make dev                  # Start development server
source .venv/bin/activate # Always activate venv first
```

### Service Management
```bash
make status               # PM2-style status of all services
make logs                 # View colorized logs
make logs-f              # Follow logs in real-time
make health              # Health check all services
make start/stop/restart  # Service lifecycle
```

### Database Operations
```bash
make db-init             # Initialize database
make db-migrate          # Run migrations
```

### Quality & Testing
```bash
make test                # Run test suite (pytest)
make lint                # Code linting (ruff)
make format              # Format code (ruff)
ruff check              # Direct linting
pytest tests/           # Direct test execution
```

### Agent Development
```bash
make create-agent name=my_agent type=simple
automagik agents create -n my_agent -t simple
```

## Critical Development Rules

### 1. Memory-First Development (MANDATORY)
**Always search memory before starting any task:**
```bash
# Search for patterns and preferences
agent-memory_search_memory_nodes --query "task keywords" --entity "Procedure"
agent-memory_search_memory_nodes --query "preferences" --entity "Preference"
agent-memory_search_memory_facts --query "dependencies relationships"

# Store successful patterns immediately
agent-memory_add_memory --name "Pattern Name" --episode_body "content" --source "text"
```

### 2. Linear Integration (MANDATORY)
**All development work must use Linear task tracking:**

**Known Linear Configuration:**
- Team ID: `2c6b21de-9db7-44ac-9666-9079ff5b9b84`
- Project ID: `dbb25a78-ffce-45ba-af9c-898b35255896`

**Required Workflow:**
1. Create Linear issue FIRST, get NMSTX-XX ID
2. Create standardized branch: `NMSTX-XX-brief-description`
3. Reference Linear ID in ALL commits: `feat(NMSTX-XX): description`
4. Update Linear status as work progresses

**State IDs:**
- TODO: `c1c6cf41-7115-459b-bce9-024ab46ee0ba`
- IN_PROGRESS: `99291eb9-7768-4d3b-9778-d69d8de3f333`
- DONE: `1551da4c-03c1-4169-9690-8688f95f9e87`

### 3. Git Workflow with MCP Tools
**Use MCP git tools for local operations:**
```python
# Create branch from Linear issue
git_create_branch(
    repo_path="/home/namastex/workspace/am-agents-labs",
    branch_name="NMSTX-XX-feature-name",
    base_branch="main"
)

# Make commits with Linear references
git_commit(
    repo_path="/home/namastex/workspace/am-agents-labs",
    message="feat(NMSTX-XX): implement feature"
)
```

**CRITICAL Git Co-Author Rule:**
When making git commits, ALWAYS co-author with Genie, not Claude:
```
🧞 Automagik Genie

Co-Authored-By: Automagik Genie <genie@namastex.ai>
```
NEVER use `Co-Authored-By: Claude <noreply@anthropic.com>`. Genie owns this repository!

## Architecture Patterns

### Agent Development (MANDATORY)
**Always extend AutomagikAgent, never modify base classes:**
```python
class MyAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        self._code_prompt_text = AGENT_PROMPT  # Required
        self.dependencies = AutomagikAgentsDependencies(...)
        self.tool_registry.register_default_tools(self.context)  # Required
```

### API Development
**All /api/v1/ endpoints require authentication:**
```python
@router.post("/action", response_model=ActionResponse)
async def perform_action(
    request: ActionRequest,
    api_key: str = Depends(verify_api_key)  # Required for /api/v1/
):
    # Implementation
```

### Memory Template Usage
```python
SYSTEM_PROMPT = """You are an agent.
User: {{user_name}} | Context: {{recent_context}}
Preferences: {{user_preferences}}  # From memory searches
Available tools: {tools}"""
```

## Technology Stack

- **Python**: Use `uv` workflow (NOT pip)
- **Framework**: FastAPI + Pydantic AI + PydanticAI
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **LLMs**: OpenAI, Gemini, Claude, Groq, Ollama
- **Testing**: pytest with 95%+ coverage requirement
- **Package Manager**: pnpm (NOT npm) for any JavaScript
- **Authentication**: JWT RS256

## Codebase Structure

```
src/
├── agents/
│   ├── common/          # Shared utilities
│   ├── simple/          # Agent implementations
│   └── claude_code/     # Genie orchestrator
├── api/
│   ├── controllers/     # Business logic
│   └── routes/          # FastAPI endpoints
├── tools/               # Tool integrations
├── memory/              # Knowledge graph
└── db/                  # Database layer

tests/
├── agents/              # Agent tests
├── api/                 # API tests
└── integration/         # E2E tests
```

## Genie Orchestration System

**Genie** is the orchestrator consciousness that:
- Decomposes complex requests into workflow sequences
- Manages specialized Claude Code workflows
- Maintains persistent memory across sessions
- Uses intelligent wait strategies for autonomous monitoring
- Provides human approval checkpoints for critical decisions

**Workflow Capabilities:**
- Dynamic workflow detection and orchestration
- Intelligent task decomposition and sequencing
- Context-aware execution planning
- Autonomous monitoring with human approval checkpoints

## Environment Variables

Required in `.env`:
```bash
# LLM Providers
OPENAI_API_KEY=sk-your-key
ANTHROPIC_API_KEY=your-key
GEMINI_API_KEY=your-key

# Database
DATABASE_URL=sqlite:///automagik.db  # or PostgreSQL URL

# API
AUTOMAGIK_API_PORT=8000
API_KEY=your-api-key
```


## Quality Standards

### Security
- API authentication on all `/api/v1/` endpoints
- Input validation with Pydantic models
- No secrets in code or commits
- Use `.env` files for configuration

### Performance
- Async operations for I/O
- Connection pooling for databases
- Proper resource cleanup

### Testing
- 95%+ test coverage requirement
- Unit tests for all new utilities
- Integration tests for API endpoints
- End-to-end tests for workflows

## Development Workflow

1. **Search memory first** for existing patterns and preferences
2. **Create Linear issue** and get NMSTX-XX ID
3. **Create standardized branch** using MCP git tools
4. **Follow established patterns** from memory and codebase
5. **Extend, don't modify** base classes
6. **Test thoroughly** with high coverage
7. **Store successful patterns** in memory
8. **Update Linear status** as work progresses

## Troubleshooting

### Common Issues
- **Database connection**: Check PostgreSQL status and DATABASE_URL
- **Agent loading**: Verify venv activation and test imports
- **API auth**: Test with curl and X-API-Key header
- **Import errors**: Ensure `source .venv/bin/activate` and `uv sync`

### Debug Commands
```bash
# Check environment
which python                    # Should show .venv/bin/python
pip list | grep pydantic-ai     # Verify installation

# Test services
curl http://localhost:8000/health
automagik agents dev            # Debug mode
```

## Critical Rules

### Always Do
1. Search memory first for patterns/preferences
2. Activate venv: `source .venv/bin/activate`
3. Use `uv` workflow (NOT pip)
4. Create Linear issue before starting work
5. Use NMSTX-XX branch naming
6. Store successful patterns in memory
7. Achieve 95%+ test coverage

### Never Do
1. Skip memory search - miss established patterns
2. Skip venv activation - causes import issues
3. Use pip commands - use uv workflow
4. Modify base classes - extend instead
5. Work without Linear tracking
6. Create files in root folder without permission
7. Commit secrets or API keys