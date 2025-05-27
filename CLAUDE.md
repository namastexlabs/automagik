# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
# Using the CLI
automagik agents start      # Start the FastAPI server
automagik agents dev        # Development mode with auto-reload
automagik agents --debug    # Show detailed configuration

# Direct Python execution
python -m src.main --reload --host 0.0.0.0 --port 8881

# Using install scripts (if available)
agent start                 # Start service/container
agent stop                  # Stop service/container
agent restart              # Restart service/container
agent status               # Show detailed status
agent logs                 # Show live logs
agent health               # Check API health
```

## Architecture Overview

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
automagik agents create -n my_agent -t simple
```
This creates the full agent structure in `src/agents/simple/my_agent/`.

### Tool Integration
Tools in `src/tools/` are automatically discovered and registered. Each tool module should have:
- `tool.py` - Main tool implementation
- `schema.py` - Pydantic schemas for requests/responses
- `interface.py` - External API interface (if applicable)

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