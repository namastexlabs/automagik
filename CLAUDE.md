# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automagik Agents is a production-ready AI agent framework built on Pydantic AI that provides:
- 🤖 Extensible agent system with template-based creation
- 💾 Persistent memory with PostgreSQL and optional Neo4j/Graphiti knowledge graphs
- 🔧 Production-ready FastAPI with authentication and health monitoring
- 🔗 Multi-LLM support (OpenAI, Gemini, Claude, Groq)
- 📦 Zero-config deployment via Docker or systemd
- 🛠️ Comprehensive CLI for agent management and interaction

## 🎯 Core Development Principles

### Primary Objectives
- Develop, maintain, and extend automagik-agents framework following established patterns
- Always **EXTEND** `AutomagikAgent`, never modify base classes
- Follow patterns from existing agents in `src/agents/simple/`
- Use provided tools/infrastructure vs reinventing

### Critical Procedures

#### 1. **ALWAYS Search Memory First**
Before starting any task, search for established patterns and preferences:
```bash
# Search for task-specific patterns and preferences
agent-memory_search_memory_nodes --query "task keywords" --entity "Procedure"
agent-memory_search_memory_nodes --query "preferences" --entity "Preference"
agent-memory_search_memory_facts --query "dependencies relationships"
```

#### 2. **Use Linear for Task Management** 
Create Linear tasks for all development work and use Linear IDs in branch names and commits.

#### 3. **Store Successful Patterns**
After implementing solutions, store them in memory for future reuse:
```bash
agent-memory_add_memory --name "Pattern: [Name]" --episode_body "pattern details" --source "text"
```

## Quick Start

### Installation
```bash
# Clone repository
git clone https://github.com/namastexlabs/automagik-agents.git
cd automagik-agents

# Install with uv (recommended)
make install          # Auto-detects best mode
make install-dev      # Development environment
make install-docker   # Docker development
make install-service  # Systemd service

# Configure API keys in .env
cp .env.example .env
nano .env  # Add OPENAI_API_KEY, etc.
```

### Running the Server
```bash
# Development mode with auto-reload
make dev              # Or: automagik agents dev
make run              # Manual restart mode

# Production modes
make start            # Start server (auto-detects mode)
make docker           # Docker development stack
make prod             # Production Docker stack

# Service management
make status           # PM2-style status table
make logs             # View logs (N=lines, FOLLOW=1)
make health           # Check service health
```

## Development Commands

### Testing
```bash
# Activate virtual environment first
source .venv/bin/activate

# Run all tests
pytest

# Run specific test categories
pytest -m unit              # Unit tests only
pytest -m integration       # Integration tests (may require external services)
pytest -m slow             # Slow running tests

# Run tests with verbose output
pytest -v

# Run specific test file
pytest tests/path/to/test_file.py

# Run tests in parallel
pytest -n auto             # Uses pytest-xdist for parallel execution
```

### Code Quality
```bash
# Format and lint code
ruff check --exit-zero --fix src/
ruff format src/

# Check specific file
ruff check --exit-zero --fix $file
ruff format $file
```

### Server Management
```bash
# CLI Commands (auto-detects deployment mode)
automagik agents start      # Start server
automagik agents stop       # Stop server
automagik agents restart    # Restart server
automagik agents status     # Show detailed status
automagik agents logs [-f]  # View logs (with follow)
automagik agents health     # Check API health
automagik agents dev        # Development mode with auto-reload

# Direct execution
python -m src               # Start server
python -m src --reload      # Development mode

# Agent interaction
automagik agents create -n my_agent -t simple
automagik agents run -a simple -m "Hello!"
automagik agents chat -a simple
```

## Architecture Overview

### Project Structure
```
automagik-agents/
├── src/
│   ├── agents/          # Agent implementations
│   │   ├── models/      # Factory, base classes
│   │   ├── common/      # Shared utilities
│   │   └── simple/      # Agent templates
│   ├── api/             # FastAPI routes & controllers
│   ├── db/              # Database layer
│   ├── mcp/             # Model Context Protocol
│   ├── memory/          # Memory management
│   ├── tools/           # Tool implementations
│   ├── cli/             # CLI commands
│   ├── config.py        # Settings management
│   └── main.py          # FastAPI app entry
├── tests/               # Test suite
├── docker/              # Docker configurations
├── docs/                # Documentation
└── Makefile             # Development commands
```

### Core Components

**Agent Factory System** (`src/agents/models/agent_factory.py`)
- Centralized agent discovery and instantiation
- Template-based agent creation with automatic tool registration
- Thread-safe agent management with both sync and async locks

**Memory System** (`src/memory/`, `src/agents/common/memory_handler.py`)
- Persistent conversation storage in PostgreSQL
- Dynamic `{{variable}}` templating that auto-injects context
- Knowledge graph integration via Graphiti/Neo4j for semantic understanding

**MCP Integration** (`src/mcp/`)
- Model Context Protocol client and server management
- Automatic health checking and server lifecycle management
- Tool discovery and registration from MCP servers

**API Layer** (`src/api/`, `src/main.py`)
- FastAPI-based REST API with authentication middleware
- Async request handling with concurrency limits
- Comprehensive health monitoring and error handling

### Agent Structure

Agents follow a template pattern in `src/agents/simple/`:
- `agent.py` - Main agent implementation extending `AutomagikAgent`
- `prompts/` - Pydantic AI prompt definitions with role-based variations
- `specialized/` - Domain-specific tools and integrations
- `models.py` - Agent-specific data models (when needed)

### Database Architecture

**PostgreSQL Backend**
- Connection pooling via psycopg2 (10-25 connections)
- Migration system in `src/db/migrations/`
- Repository pattern in `src/db/repository/`

**Key Tables:**
- `agents` - Agent configurations and metadata
- `sessions` - Conversation sessions with agent associations
- `messages` - Message history with channel payload support
- `prompts` - Templated prompts with variable substitution
- `mcp_servers` - MCP server configurations and status

## CLI Usage

### Agent Commands
```bash
# Create new agent
automagik agents create -n weather_bot -t simple

# Run single message
automagik agents run -a simple -m "What's 2+2?"
automagik agents run -a weather_bot -m "Weather in NYC?" --model gpt-4

# Interactive chat
automagik agents chat -a simple
automagik agents chat -a weather_bot --session weather-convo

# With specific user
automagik agents chat -a simple --user "550e8400-e29b-41d4-a716-446655440000"
```

### Database Commands
```bash
# Initialize database
automagik agents db init

# Run migrations
automagik agents db migrate

# Database shell
automagik agents db shell
```

## Configuration

### Environment Variables
All configuration is managed through `src/config.py` using Pydantic Settings:

**Required:**
- `AM_API_KEY` - API authentication key
- `OPENAI_API_KEY` - OpenAI API access
- `DISCORD_BOT_TOKEN` - Discord bot authentication

**Database:**
- `DATABASE_URL` - Full PostgreSQL connection string
- Or individual: `POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

**Optional Integrations:**
- `GEMINI_API_KEY`, `ANTHROPIC_API_KEY` - Additional LLM providers
- `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` - Knowledge graph backend
- `NOTION_TOKEN`, `AIRTABLE_TOKEN` - External service integrations

### Agent Configuration
- Use `AM_AGENTS_NAMES` to specify which agents to initialize at startup
- Agents auto-discover and register tools from `src/tools/`
- Memory templates support `{{variable}}` substitution for dynamic context

## Development Patterns

### Creating New Agents
```bash
# Create from template
automagik agents create -n my_agent -t simple
# Or using make
make create-agent name=my_agent type=simple
```

This creates the full agent structure in `src/agents/simple/my_agent/`:
- `agent.py` - Main agent class extending AutomagikAgent
- `prompts/prompt.py` - Pydantic AI prompt definitions
- `specialized/` - Domain-specific implementations (optional)
- `models.py` - Agent-specific data models (optional)

#### Agent Extension Pattern (MANDATORY)
```python
from src.agents.models import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from typing import Dict

class MyAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        self._code_prompt_text = AGENT_PROMPT  # Required
        self.dependencies = AutomagikAgentsDependencies(...)
        self.tool_registry.register_default_tools(self.context)  # Required
```

### Tool Integration
Tools in `src/tools/` are automatically discovered and registered. Each tool module should have:
- `tool.py` - Main tool implementation
- `schema.py` - Pydantic schemas for requests/responses
- `interface.py` - External API interface (if applicable)

#### PydanticAI Tool Structure
```python
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from typing import Dict, Optional

class ToolInput(BaseModel):
    """Input schema for the tool"""
    query: str = Field(..., description="Search query")
    filters: Optional[Dict] = Field(None, description="Optional filters")

class ToolOutput(BaseModel):
    """Output schema for the tool"""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    message: str

@agent.tool
async def my_tool(ctx: RunContext[Dict], input_data: ToolInput) -> ToolOutput:
    """Tool description for the agent."""
    try:
        result = await perform_operation(input_data.query)
        return ToolOutput(
            success=True,
            data=result,
            message="Operation completed successfully"
        )
    except Exception as e:
        return ToolOutput(
            success=False,
            error=str(e),
            message="Operation failed"
        )
```

### Testing Patterns
- Unit tests for individual components
- Integration tests requiring external services (marked with `@pytest.mark.integration`)
- Agent-specific tests in `tests/agents/`
- Performance benchmarks in `tests/perf/`

### MCP Development
MCP servers are managed through the database with automatic lifecycle management. Server configurations support:
- Process-based servers (started via command)
- Network servers (connect to existing endpoints)
- Auto-start capabilities and health monitoring

## Database Operations

### Migrations
```bash
# Database initialization creates tables automatically
automagik agents start  # Runs db_init() during startup
```

### Connection Management
The system uses connection pooling with automatic retry logic. Database operations should use the repository pattern from `src/db/repository/`.

## Performance Considerations

- **Concurrency:** Limited to 100 concurrent requests (configurable via `UVICORN_LIMIT_CONCURRENCY`)
- **LLM Requests:** Max 15 concurrent per provider (configurable via `LLM_MAX_CONCURRENT_REQUESTS`)
- **Graphiti Queue:** Async processing with 10 workers, 1000 queue size
- **Connection Pooling:** 10-25 PostgreSQL connections based on load

## API Endpoints

### Core Endpoints
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation
- `GET /api/v1/agents` - List all agents
- `POST /api/v1/agent/{agent_name}/run` - Run agent with message

### Session Management
- `GET /api/v1/sessions` - List sessions
- `POST /api/v1/sessions` - Create session
- `GET /api/v1/sessions/{id}/messages` - Get session messages

### Memory Management
- `GET /api/v1/memories` - List memories
- `POST /api/v1/memories` - Create memory with {{variable}} support
- `GET /api/v1/agent/{agent_id}/memories` - Get agent memories

### Authentication
All API endpoints require `X-API-Key` header with value from `AM_API_KEY` environment variable.

## Debugging

### Enable Debug Mode
```bash
# Via environment
export AM_LOG_LEVEL=DEBUG

# Via CLI
automagik agents --debug
automagik agents dev --debug

# View configuration
automagik --debug agents status
```

### Common Issues

**Port already in use:**
```bash
make stop-all     # Stop all services
lsof -ti :8881    # Find process on port
kill -9 <PID>     # Force kill if needed
```

**Database connection issues:**
```bash
make db-init      # Reinitialize database
make logs N=100   # Check recent logs
```

**Missing dependencies:**
```bash
make install-deps # Install PostgreSQL, Neo4j, Graphiti
```

## 🚨 Development Workflow & Best Practices

### Git Workflow with MCP Tools

#### Starting New Work
```python
# 1. Check current status
git_status(repo_path="/root/workspace/am-agents-labs")

# 2. Create Linear task first to get NMSTX-XX ID
linear_create_issue(...)  # Returns issue with ID

# 3. Create branch with Linear ID (MANDATORY)
git_create_branch(
    repo_path="/root/workspace/am-agents-labs",
    branch_name="NMSTX-XX-feature-description",
    base_branch="main"
)

# 4. Switch to new branch
git_checkout(
    repo_path="/root/workspace/am-agents-labs",
    branch_name="NMSTX-XX-feature-description"
)
```

#### Commit Standards
- **Format:** `type(scope): description`
- **Types:** feat, fix, docs, test, refactor, style, chore
- **Always include Linear ID:** `feat(NMSTX-XX): implement feature`

```python
# Stage files
git_add(
    repo_path="/root/workspace/am-agents-labs",
    files=["src/file.py"]
)

# Commit with semantic message
git_commit(
    repo_path="/root/workspace/am-agents-labs",
    message="feat(NMSTX-XX): implement new functionality"
)

# Push using terminal (MCP doesn't support push)
run_terminal_cmd("git push origin NMSTX-XX-feature-description")
```

### Development Script Organization

- **Development scripts:** Always put in `dev/` folder
- **Temporary scripts:** Use `dev/temp/` (auto-deleted after 30 days)
- **Production utilities:** Only reviewed scripts go in `scripts/`

```bash
# ✅ DO: Put debugging/test scripts in dev/
dev/debug_mcp_connection_issue.py
dev/test_agent_memory_integration.py

# ❌ DON'T: Put temporary scripts in src/ or scripts/
```

### API Development Pattern

All `/api/v1/` endpoints require authentication:
```python
@router.post("/action", response_model=ActionResponse)
async def perform_action(
    request: ActionRequest,
    api_key: str = Depends(verify_api_key)  # Required for /api/v1/
):
    # Implementation
```

### Memory Template Usage

Prompts support dynamic variable substitution:
```python
SYSTEM_PROMPT = """You are an agent.
User: {{user_name}} | Context: {{recent_context}}
Preferences: {{user_preferences}}  # From memory searches
Available tools: {tools}"""
```

## 🚫 Critical Rules - What NOT to Do

### ❌ NEVER DO
1. **Skip memory search** - Always check for established patterns first
2. **Skip venv activation** - Always use `source .venv/bin/activate`
3. **Use pip commands** - Use `uv` workflow instead
4. **Modify base classes** - Always extend, never modify
5. **Bypass authentication** - All `/api/v1/` endpoints need API keys
6. **Work without Linear** - Always create tasks and use IDs
7. **Use shell git commands for local operations** - Use MCP git tools

### ✅ ALWAYS DO
1. **Search memory first** - Check preferences/procedures before starting
2. **Activate venv** - `source .venv/bin/activate` before Python commands
3. **Use uv workflow** - `uv sync|add|remove` (NOT pip)
4. **Extend AutomagikAgent** - Never modify base classes
5. **Use Linear** - For all development work
6. **Record patterns in memory** - Store successful implementations
7. **Use MCP git tools** - For version control operations

## Essential Commands Reference

```bash
# Environment
source .venv/bin/activate && uv sync

# Development
automagik agents start      # Start server
automagik agents dev        # Dev mode with auto-reload
make dev                    # Alternative dev mode

# Testing
pytest                      # Run all tests
pytest -m unit             # Unit tests only
ruff check --fix src/      # Lint and fix
ruff format src/           # Format code

# Memory Operations
agent-memory_search_memory_nodes --query "preferences" --entity "Preference"
agent-memory_add_memory --name "Pattern" --episode_body "content" --source "text"

# Linear
linear_create_issue --title "Issue Title" --teamId "<team-id>"
linear_update_issue --issueId "<issue-id>" --status "In Progress"
```