# Setup Guide

This guide provides step-by-step instructions for setting up your local development environment for the Automagik Agents project.

## Prerequisites

The Makefile system can automatically install most prerequisites, but you'll need:

- **Basic System**: Linux, macOS, or WSL on Windows
- **Git:** For cloning the repository
- **Internet Connection:** For downloading dependencies

The following will be installed automatically if missing:
- **Python:** Version 3.10+ (automatically detected/installed)
- **Docker & Docker Compose:** For containerized services
- **uv:** Python package manager (preferred over pip)
- **System tools:** make, curl, jq, ccze (for colored logs)

## Quick Start (Recommended)

The easiest way to get started is using the automated Makefile system:

```bash
git clone https://github.com/namastexlabs/automagik-agents.git
cd automagik-agents

# Show all available commands
make help

# Install prerequisites (all platforms)
make install-prerequisites

# Quick installation and startup
make install-dev    # Install development environment
make dev           # Start development mode
```

### Installation Modes

```bash
# Auto-detect best mode for your system
make install

# Specific installation modes:
make install-dev       # Development (local Python + venv)
make install-docker    # Docker development environment
make install-prod      # Production Docker environment  
make install-service   # Systemd service (Linux only)
```

### Platform Support

The Makefile automatically detects your platform and uses the appropriate package manager:

- **Ubuntu/Debian**: `apt-get`
- **RHEL/CentOS**: `yum`
- **Fedora**: `dnf`
- **Arch Linux**: `pacman`
- **macOS**: `brew` (installs Homebrew if needed)

## Manual Prerequisites (Advanced)

If you prefer to install prerequisites manually:

```bash
# Check what's needed
make check-system

# Verify after installation
make verify-prerequisites
```

## Configuration

### 1. Environment Variables

Copy and configure the environment file:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration:

```dotenv
# Essential Variables
AUTOMAGIK_API_KEY="am-your_secure_api_key_here"
OPENAI_API_KEY="sk-your_openai_api_key_here"

# Server Configuration
AUTOMAGIK_API_PORT=8881
AUTOMAGIK_API_HOST=0.0.0.0
ENVIRONMENT=development

# Database Configuration
# DATABASE_TYPE can be "sqlite" (default) or "postgresql"
DATABASE_TYPE=sqlite

# SQLite Configuration (default, no additional setup required)
SQLITE_DATABASE_PATH=./data/automagik_agents.db

# PostgreSQL Configuration (optional, for production use)
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
- The `AUTOMAGIK_API_KEY` is used for internal API authentication - generate a secure random string

### 2. Database Setup

The framework supports both SQLite (default) and PostgreSQL databases:

#### SQLite (Recommended for Development)

SQLite is the default database and requires no additional setup:

```bash
# Initialize SQLite database (automatic)
make db-init
```

The SQLite database file will be created automatically at `./data/automagik_agents.db`.

**Advantages:**
- ✅ Zero configuration required
- ✅ Single file database
- ✅ Perfect for development and testing
- ✅ Fast and lightweight

#### PostgreSQL (Recommended for Production)

For production deployments or when you need advanced database features:

```bash
# Set DATABASE_TYPE=postgresql in your .env file
echo "DATABASE_TYPE=postgresql" >> .env

# Install and start PostgreSQL
make install-postgres

# Initialize database
make db-init
```

**Advantages:**
- ✅ Robust production database
- ✅ Advanced features (full-text search, JSON operations)
- ✅ Better concurrent access
- ✅ Scalable for large deployments

#### Optional: Graph Database Services

```bash
# Optional: Install graph services
make install-neo4j      # Neo4j database
make install-graphiti   # Graphiti service
```

## Service Management

### Starting Services

```bash
# Development mode (local Python)
make dev

# Docker development stack
make docker

# Production Docker stack  
make prod

# Force start (stops conflicting services)
make dev FORCE=1
```

### Monitoring

```bash
# Beautiful PM2-style status display
make status

# Quick status summary
make status-quick

# Health check all services
make health

# View logs (colorized)
make logs

# Follow logs in real-time
make logs-f
```

### Service Control

```bash
# Stop all services
make stop

# Restart services
make restart

# Auto-detect mode and start appropriate service
make start
```

## Verification

### 1. Check Installation

```bash
# Comprehensive system check
make check-system

# Verify all prerequisites
make verify-prerequisites

# Check service status
make status
```

### 2. Test the API

```bash
# Health check
curl http://localhost:8881/health

# API documentation
open http://localhost:8881/docs

# Test agent endpoint
curl -X POST http://localhost:8881/api/v1/agent/simple/run \
  -H "X-API-Key: your_am_api_key" \
  -H "Content-Type: application/json" \
  -d '{"message_content": "Hello!", "session_name": "test"}'
```

## Development Workflow

### Essential Commands

```bash
# Start development
make dev                  # Start with auto-reload

# Monitor and debug
make status              # PM2-style status table
make logs-f              # Follow logs
make health              # Check all services

# Development tools
make test                # Run test suite
make lint                # Code linting
make format              # Code formatting
make requirements-update # Update dependencies
```

### Database Operations

```bash
# Database management
make db-init             # Initialize schema
make db-migrate          # Run migrations
make db-reset            # Reset database (⚠️ destructive)
```

### Docker Operations

```bash
# Docker development
make docker              # Start Docker stack
make docker-build        # Build images
make docker-clean        # Clean containers/images
```

## Production Deployment

### Docker Production Setup

```bash
# Install production environment
make install-prod

# Start production stack
make prod

# Monitor production
make status
make health
make logs-f
```

### Systemd Service Setup

```bash
# Install as systemd service (Linux only)
make install-service

# Control via systemd
sudo systemctl start automagik-agents
sudo systemctl status automagik-agents

# Or use make commands
make start    # Uses systemd if installed
make stop
make restart
```

## Troubleshooting

### Common Issues

**1. Prerequisites missing:**
```bash
# Install all prerequisites
make install-prerequisites

# Check what's missing
make check-system
```

**2. Virtual environment issues:**
```bash
# Clean and recreate
make venv-clean
make install-python-env
```

**3. Database connection errors:**
```bash
# Check service status
make status

# Check health
make health

# View logs
make logs

# Restart database
make install-postgres
```

**4. Port conflicts:**
```bash
# Stop conflicting services
make stop

# Force start new service
make dev FORCE=1

# Check what's using ports
make status
```

**5. Docker issues:**
```bash
# Clean Docker resources
make docker-clean

# Rebuild containers
make docker-build
make docker
```

### Log Analysis

```bash
# Smart log detection (auto-finds source)
make logs

# Follow logs from all sources
make logs-all

# Interactive container selection
make logs-docker

# Specific line counts
make logs-100    # Last 100 lines
make logs-500    # Last 500 lines
```

### Health Diagnostics

```bash
# Comprehensive health check
make health

# Individual service checks
make status           # All instances
make status-quick     # One-line summary

# Check specific components
curl http://localhost:8881/health      # API health
make db-init                          # Database connectivity
```

### Clean Installation

```bash
# Full reset (⚠️ destructive)
make reset

# Clean specific components
make clean              # Temporary files
make venv-clean         # Virtual environment
make docker-clean       # Docker resources

# Reinstall from scratch
make install-dev
```

## Advanced Configuration

### Environment Detection

The Makefile automatically detects:
- **Environment files**: `.env` for development, `.env.prod` for production
- **Running services**: Docker containers, systemd services, local processes
- **Platform**: Linux distribution or macOS for package management

### Force Mode

Use `FORCE=1` to override conflict detection:

```bash
make dev FORCE=1        # Stop existing and start dev
make docker FORCE=1     # Force Docker mode
make prod FORCE=1       # Force production mode
```

### Individual Services

```bash
# Install specific services
make install-postgres   # PostgreSQL only
make install-neo4j      # Neo4j only
make install-graphiti   # Graphiti only
make install-python-env # Python environment only
```

## Next Steps

After successful installation:

1. **Test basic functionality**: `make dev && make status && make logs-f`
2. **Configure agents**: Edit configurations in `src/agents/`
3. **Add integrations**: Configure Discord, Notion, etc. in `.env`
4. **Create custom agents**: Use the agent creation system
5. **Set up monitoring**: Configure health checks and logging
6. **Deploy to production**: Use `make install-prod && make prod`

For more information, see:
- [Makefile Reference](../operations/makefile-reference.md) - Complete command reference
- [Configuration Guide](./configuration.md) - Detailed configuration
- [Running Guide](./running.md) - Operational procedures
- [API Reference](http://localhost:8881/docs) - API documentation 