# Makefile Reference

The automagik-agents project uses a comprehensive Makefile system for installation, deployment, and management. This replaces the previous shell-based scripts with a more robust, AI-friendly approach.

## 🚀 Quick Start

```bash
# Show all available commands
make help

# Quick installation and startup
make install-dev    # Install development environment
make dev           # Start development mode

# Status and logs
make status        # Show PM2-style status of all instances
make logs          # View colorized logs
make health        # Check health of all services
```

## 💜 Design Philosophy

- **Purple Theme**: All visual elements use automagik's signature purple/magenta colors
- **PM2-Style**: Status displays inspired by pm2's clean output format
- **Agent-Friendly**: Declarative syntax that AI agents can easily parse and generate
- **Token-Efficient**: Maximize information density while minimizing output
- **Environment-Aware**: Automatically detects .env vs .env.prod configurations

## 📋 Command Categories

### 🔧 Prerequisites

| Command | Description |
|---------|-------------|
| `make install-prerequisites` | Install system dependencies (all platforms) |
| `make install-uv` | Install uv Python package manager |
| `make verify-prerequisites` | Verify all prerequisites are installed |
| `make check-system` | Check system prerequisites and show status |

**Platform-specific installation:**
- `make install-prerequisites-linux` - Auto-detects distribution
- `make install-prerequisites-mac` - Uses Homebrew
- `make install-prerequisites-debian` - Ubuntu/Debian packages
- `make install-prerequisites-rhel` - RHEL/CentOS packages
- `make install-prerequisites-fedora` - Fedora packages
- `make install-prerequisites-arch` - Arch Linux packages

### 📋 Installation

| Command | Description |
|---------|-------------|
| `make install` | **Auto-detect and install appropriate environment** |
| `make install-dev` | Development environment (local Python + venv) |
| `make install-docker` | Docker development environment |
| `make install-prod` | Production Docker environment |
| `make install-service` | Systemd service installation |

**Individual service installation:**
- `make install-postgres` - PostgreSQL database container
- `make install-neo4j` - Neo4j graph database (for Graphiti)
- `make install-graphiti` - Graphiti knowledge graph service
- `make install-python-env` - Python virtual environment only

### 🎛️ Service Management

| Command | Description |
|---------|-------------|
| `make start` | Start services (auto-detect mode) |
| `make stop` | Stop all services |
| `make restart` | Restart services |
| `make dev` | Start development mode |
| `make docker` | Start Docker development stack |
| `make prod` | Start production Docker stack |

### 📊 Monitoring & Status

| Command | Description |
|---------|-------------|
| `make status` | **Show PM2-style status table of all instances** |
| `make status-quick` | Quick one-line status summary |
| `make health` | Check health of all services |
| `make logs` | View colorized logs (auto-detect source) |
| `make logs-f` | Follow logs in real-time |
| `make logs-100` | View last 100 log lines |
| `make logs-500` | View last 500 log lines |
| `make logs-docker` | Interactive Docker container log selection |
| `make logs-all` | View logs from all sources |

### 🗄️ Database

| Command | Description |
|---------|-------------|
| `make db-init` | Initialize database |
| `make db-migrate` | Run database migrations |
| `make db-reset` | Reset database (⚠️ destructive) |

### 🛠️ Development

| Command | Description |
|---------|-------------|
| `make test` | Run test suite |
| `make lint` | Run code linting |
| `make format` | Format code with ruff |
| `make requirements-update` | Update Python dependencies |

### 🐳 Docker

| Command | Description |
|---------|-------------|
| `make docker-build` | Build Docker images |
| `make docker-clean` | Clean Docker images and containers |

### 🧹 Maintenance

| Command | Description |
|---------|-------------|
| `make clean` | Clean temporary files |
| `make reset` | Full reset (⚠️ destructive) |
| `make venv-clean` | Remove virtual environment |

## 🔥 Force Mode

Add `FORCE=1` to force operations that might conflict with running services:

```bash
# These will check for conflicts and ask for confirmation
make dev
make docker

# These will stop existing services and proceed
make dev FORCE=1
make docker FORCE=1
```

## 🎯 Environment Detection

The Makefile automatically detects your environment:

- **Development**: Uses `.env` file
- **Production**: Uses `.env.prod` file (takes precedence)
- **Docker Detection**: Automatically detects running containers
- **Service Detection**: Checks systemd service status

## 📊 Status Display

The `make status` command shows a beautiful PM2-style table:

```
💜 Automagik Agents Status
┌────┬─────────────────────────┬──────────┬───────┬────────┬──────────┬──────────┐
│ id │ name                    │ mode     │ port  │ pid    │ uptime   │ status   │
├────┼─────────────────────────┼──────────┼───────┼────────┼──────────┼──────────┤
│ 0  │ automagik_agents        │ docker   │ 8881  │ 32ef3b │ 1h       │ online   │
│ 1  │ automagik_agents_db     │ docker   │ 5432  │ 0bd1e7 │ 1h       │ online   │
│ 2  │ automagik-agents-prod   │ docker   │ 18881 │ 7d0d1c │ 2h       │ online   │
│ 3  │ automagik_graphiti      │ docker   │ 8000  │ 44de0a │ 2h       │ online   │
│ 4  │ automagik-local         │ process  │ -     │ 485345 │ 00:00    │ error    │
│ 5  │ automagik-svc           │ service  │ -     │ -      │ -        │ stopped  │
└────┴─────────────────────────┴──────────┴───────┴────────┴──────────┴──────────┘
```

**Status Indicators:**
- 🟢 **online** - Service running and healthy
- 🔴 **error** - Service running but unhealthy
- 🟡 **stopped** - Service not running

## 🔍 Log Viewing

Logs are automatically colorized using `ccze` when available:

```bash
make logs           # Smart auto-detection of log source
make logs-f         # Follow logs (like tail -f)
make logs-docker    # Choose specific Docker container
```

**Log Sources (auto-detected):**
1. **Systemd service**: `journalctl -u automagik-agents`
2. **Docker containers**: `docker logs <container>`
3. **Local files**: `logs/automagik.log`

## 🩺 Health Checks

The health system provides comprehensive service monitoring:

```bash
make health
```

**Checks:**
- 💜 Automagik Agents API endpoint
- 🐘 PostgreSQL connectivity  
- 🔷 Neo4j status (if enabled)
- 📊 Graphiti service health

## 🚀 Common Workflows

### First-Time Setup

```bash
# Install everything needed for development
make install-prerequisites
make install-dev

# Start development
make dev

# Check status
make status
```

### Docker Development

```bash
# Set up Docker environment
make install-docker

# Start full stack
make docker

# Monitor logs
make logs-f
```

### Production Deployment

```bash
# Install production environment
make install-prod

# Start production stack
make prod

# Monitor health
make health
make status
```

### Troubleshooting

```bash
# Check system requirements
make check-system

# Verify prerequisites
make verify-prerequisites

# View logs for debugging
make logs-all

# Check health of all services
make health
```

## 🔧 Environment Variables

Key variables read from `.env` or `.env.prod`:

- `AM_PORT` - Main application port
- `DATABASE_URL` - PostgreSQL connection string
- `AM_API_KEY` - API authentication key
- `LOG_LEVEL` - Logging verbosity

## 💡 Tips & Best Practices

1. **Always check status first**: `make status` shows what's running
2. **Use force flag for conflicts**: Add `FORCE=1` when needed
3. **Follow logs during startup**: `make logs-f` helps debug issues
4. **Health check regularly**: `make health` catches problems early
5. **Keep environment files updated**: Copy from `.env.example`

## 🚨 Troubleshooting

### Common Issues

**"Virtual environment not found"**
```bash
make install-python-env
```

**"Docker not found"**
```bash
make install-prerequisites
```

**"Port already in use"**
```bash
make stop
# or
make dev FORCE=1
```

**"Environment file not found"**
```bash
cp .env.example .env
# Edit .env with your configuration
```

## 🔄 Migration from Shell Scripts

If migrating from the old shell-based installation:

| Old Command | New Command |
|-------------|-------------|
| `./scripts/install/setup.sh` | `make install-dev` |
| `./scripts/start.sh` | `make dev` |
| `./scripts/status.sh` | `make status` |
| Manual Docker commands | `make docker` |
| Manual systemd setup | `make install-service` |

The Makefile system provides all the functionality of the previous shell scripts with better error handling, status reporting, and multi-instance management. 