# Setup Guide

This guide provides step-by-step instructions for setting up your local development environment for the Automagik Agents project.

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Python:** Version 3.10, 3.11, or 3.12 (check with `python --version`). You can use tools like `pyenv` to manage multiple Python versions.
*   **Docker & Docker Compose:** Required for running the PostgreSQL database and optional services (Neo4j, Graphiti). Visit the [Docker website](https://docs.docker.com/get-docker/) for installation instructions.
*   **Git:** For cloning the repository.
*   **`uv`:** The Python package installer and virtual environment manager used by this project. The setup script will install it automatically if not present.

## Quick Start (Recommended)

The easiest way to get started is using the automated setup script:

```bash
git clone https://github.com/namastexlabs/automagik-agents.git
cd automagik-agents
bash scripts/install/setup.sh
```

The installer will guide you through:
- **Local Installation**: Python virtual environment (recommended for development)
- **Docker Installation**: Containerized deployment (recommended for production)

### Non-Interactive Installation

For automated deployments or CI/CD, you can use non-interactive mode:

```bash
# Local installation with API keys
bash scripts/install/setup.sh --component agents --mode local \
  --openai-key sk-your-openai-key \
  --discord-token your-discord-token \
  --non-interactive

# Docker installation (production)
bash scripts/install/setup.sh --component agents --mode docker \
  --openai-key sk-your-openai-key \
  --non-interactive

# Install as systemd service (Linux only)
bash scripts/install/setup.sh --component agents --mode local \
  --install-service --non-interactive
```

### Setup Script Options

```bash
# Available options:
--component NAME        # Component to install (agents, omni, langflow, bundle)
--mode MODE            # Installation mode (local, docker, quick-update)
--openai-key KEY       # OpenAI API key for non-interactive installs
--discord-token TOKEN  # Discord bot token for non-interactive installs
--am-api-key KEY       # Automagik API key (auto-generated if not provided)
--no-python           # Skip Python installation
--no-docker           # Skip Docker installation
--no-dev              # Skip development tools installation
--verbose             # Enable verbose output
--non-interactive     # Skip interactive prompts and use defaults
--install-service     # Install as systemd service (Linux only)
--no-helpers          # Skip helper functions installation
```

## Manual Installation (Advanced)

If you prefer to set up manually or need to customize the installation:

### 1. Clone the Repository

```bash
git clone https://github.com/namastexlabs/automagik-agents.git
cd automagik-agents
```

### 2. Install UV Package Manager

If `uv` is not installed, install it:

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh
# or
pip install uv
```

### 3. Create Virtual Environment

```bash
# Create virtual environment with UV
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Linux/macOS
# or
.venv\Scripts\activate     # On Windows
```

### 4. Install Dependencies

```bash
# Sync dependencies using UV
uv sync

# Install project in editable mode
uv pip install -e .
```

### 5. Set Up Environment Variables

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration:

```dotenv
# Essential Variables
AM_API_KEY="am-your_secure_api_key_here"
OPENAI_API_KEY="sk-your_openai_api_key_here"

# Server Configuration
AM_PORT=8881
AM_HOST=0.0.0.0
AM_ENV=development

# Database Configuration (for local development)
DATABASE_URL="postgresql://postgres:postgres@localhost:5432/automagik_agents"
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=automagik_agents

# Optional: Discord Integration
DISCORD_BOT_TOKEN="your_discord_bot_token_here"

# Optional: Graph Database (Neo4j + Graphiti)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=automagik123
GRAPHITI_NAMESPACE_ID=automagik

# Optional: Other Integrations
NOTION_TOKEN=
GEMINI_API_KEY=
ANTHROPIC_API_KEY=
```

**Important Notes:**
- Replace placeholder values with your actual API keys
- Get API keys from: [OpenAI](https://platform.openai.com/api-keys), [Google AI Studio](https://makersuite.google.com/app/apikey), [Anthropic](https://console.anthropic.com/)
- The `AM_API_KEY` is used for internal API authentication - generate a secure random string

### 6. Start Database Services

#### Option A: Using Setup Script (Recommended)

The setup script handles Docker service management automatically:

```bash
# Use the setup script - it will handle Docker services
bash scripts/install/setup.sh --component agents --mode docker

# Or for local mode with Docker database
bash scripts/install/setup.sh --component agents --mode local
```

#### Option B: Manual Docker Commands (Advanced)

If you need to manage Docker services manually:

```bash
# Start PostgreSQL only
cd docker
docker compose up -d postgres

# Start all services (PostgreSQL + Neo4j + Graphiti)
docker compose --profile graphiti up -d
```

#### Option C: Local PostgreSQL

If you have PostgreSQL installed locally, ensure it's running and create the database:

```bash
createdb automagik_agents
```

## Verification

### 1. Check Installation

```bash
# Check if virtual environment is activated
which python  # Should point to .venv/bin/python

# Check if automagik CLI is available
automagik --help

# Check database connection
automagik agents db init  # Initialize database schema
```

### 2. Start the Server

```bash
# Using the new CLI commands
automagik agents start              # Start the server

# Or in development mode with auto-reload
automagik agents dev                # Start with auto-reload (stops any existing server)

# Or using uvicorn directly (if needed)
uvicorn src.main:app --host 0.0.0.0 --port 8881 --reload
```

### 3. Test the API

```bash
# Health check
curl http://localhost:8881/health

# API documentation
open http://localhost:8881/docs

# Test agent endpoint
curl -X POST http://localhost:8881/api/v1/agent/simple_agent/run \
  -H "X-API-Key: your_am_api_key" \
  -H "Content-Type: application/json" \
  -d '{"message_content": "Hello!", "session_name": "test"}'
```

## Post-Installation Commands

If you used the setup script with `--install-service`, you'll have convenient management commands:

```bash
agent start      # Start the service
agent stop       # Stop the service
agent restart    # Restart the service
agent status     # Show service status
agent logs       # View logs with colors
agent health     # Check API health
agent update     # Quick update deployment
agent rebuild    # Full rebuild
agent dev        # Start in development mode
agent help       # Show all commands
```

## Docker Installation Details

The Docker setup includes:

- **PostgreSQL**: Main database (port 5432)
- **Neo4j**: Graph database for advanced memory (port 7474 web, 7687 bolt)
- **Graphiti**: Graph intelligence service (port 8000)
- **Automagik Agents**: Main application (port 8881)

### Recommended: Use Setup Script

The setup script automatically manages Docker services:

```bash
# Install with Docker mode (handles everything automatically)
bash scripts/install/setup.sh --component agents --mode docker

# Quick update (rebuilds and restarts containers)
bash scripts/install/setup.sh --component agents --mode quick-update
```

### Manual Docker Commands (Advanced)

If you need direct Docker control:

```bash
# Start all services
cd docker
docker compose up -d

# Start with graph services
docker compose --profile graphiti up -d

# View logs
docker compose logs -f automagik-agents

# Stop services
docker compose down

# Rebuild and restart
docker compose up -d --build
```

## Development Setup

For development work, additional setup is recommended:

### 1. Install Development Dependencies

```bash
# Development tools are included in uv sync
# Additional tools can be installed as needed
uv pip install pytest pytest-asyncio ruff black isort mypy
```

### 2. Pre-commit Hooks (Optional)

```bash
# Install pre-commit
uv pip install pre-commit

# Set up hooks
pre-commit install
```

### 3. IDE Configuration

For VS Code, recommended extensions:
- Python
- Pylance
- Ruff
- Docker

## Troubleshooting

### Common Issues

**1. `uv` command not found:**
```bash
# Install UV manually
curl -LsSf https://astral.sh/uv/install.sh | sh
# Add to PATH
export PATH="$HOME/.local/bin:$PATH"
```

**2. Virtual environment activation fails:**
```bash
# Recreate virtual environment
rm -rf .venv
uv venv
source .venv/bin/activate
uv sync
```

**3. Database connection errors:**
```bash
# If using setup script, check service status
agent status  # If agent commands are available

# Manual Docker checks
cd docker
docker compose ps postgres

# Check database logs
docker compose logs postgres

# Verify connection string in .env
echo $DATABASE_URL
```

**4. Permission denied on setup script:**
```bash
chmod +x scripts/install/setup.sh
```

**5. Docker port conflicts:**
```bash
# Check what's using the port
lsof -i :8881
lsof -i :5432

# Change ports in .env file
AM_PORT=8882
POSTGRES_PORT=5433
```

**6. API key errors:**
- Ensure API keys are properly set in `.env`
- Check that `.env` file is in the project root
- Verify API key format (OpenAI keys start with `sk-`)

### Getting Help

1. Check the [API documentation](http://localhost:8881/docs) when the server is running
2. View logs: `agent logs` (if available) or `docker compose logs -f`
3. Check service status: `agent status` (if available) or `docker compose ps`
4. Verify environment: `automagik agents db check` (if available)

### Clean Installation

If you need to start fresh:

```bash
# Stop services using agent commands (if available)
agent stop

# Or manually stop Docker services
cd docker && docker compose down -v  # -v removes volumes

# Remove virtual environment
rm -rf .venv

# Remove environment file (optional)
rm .env

# Run setup again
bash scripts/install/setup.sh
```

## Next Steps

After successful installation:

1. **Configure your agents**: Edit agent configurations in `src/agents/`
2. **Add integrations**: Configure Discord, Notion, or other tools in `.env`
3. **Create custom agents**: Use `automagik agents create` command
4. **Set up monitoring**: Configure Logfire or other monitoring tools
5. **Deploy to production**: Use Docker mode for production deployments

For more information, see:
- [Configuration Guide](./configuration.md)
- [Agent Development Guide](./agents.md)
- [API Reference](http://localhost:8881/docs) 