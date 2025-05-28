# Running the Project

This guide explains how to run the Automagik Agents application using the new Makefile-based system.

**Prerequisite:** Ensure you have completed the steps in the [Setup Guide](./setup.md). The Makefile system automatically handles environment management and service detection.

## Quick Start Commands

The Makefile provides a unified interface for running and managing the application:

```bash
# Start development mode
make dev                    # Start with auto-reload (stops conflicting services)

# Start production mode  
make prod                   # Start production Docker stack

# Service management
make start                  # Auto-detect mode and start
make stop                   # Stop all services
make restart                # Restart services

# Monitoring
make status                 # PM2-style status table
make logs                   # View colorized logs
make logs-f                 # Follow logs in real-time
make health                 # Health check all services
```

## Installation and Service Modes

### Development Mode (Recommended for Development)

```bash
# Install and start development environment
make install-dev            # Install local Python environment
make dev                    # Start with auto-reload

# Monitor development
make status                 # Check status
make logs-f                 # Follow logs
```

### Docker Development Mode

```bash
# Install and start Docker environment
make install-docker         # Install Docker development
make docker                 # Start Docker stack

# Monitor Docker
make status                 # All containers status
make logs-docker            # Interactive container log selection
```

### Production Mode

```bash
# Install and start production environment  
make install-prod           # Install production environment
make prod                   # Start production stack

# Monitor production
make status                 # Production status
make health                 # Health checks
make logs                   # Production logs
```

### Systemd Service Mode (Linux)

```bash
# Install as systemd service
make install-service        # Install systemd service

# Control via make (uses systemd automatically)
make start                  # Start service
make stop                   # Stop service
make restart                # Restart service
make status                 # Service status
```

## Status Monitoring

### PM2-Style Status Display

The `make status` command provides a beautiful status table:

```bash
make status
```

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

### Quick Status Check

```bash
make status-quick           # One-line summary
# Output: 💜 Mode: docker-prod | Docker: 6 | Local: 2 | Service: inactive
```

### Health Monitoring

```bash
make health                 # Comprehensive health check
# Checks: API endpoints, database connectivity, service health
```

## Log Viewing

### Smart Log Detection

The Makefile automatically detects and displays logs from the appropriate source:

```bash
make logs                   # Auto-detect log source and show
make logs-f                 # Follow logs in real-time  
make logs-100               # Show last 100 lines
make logs-500               # Show last 500 lines
```

### Log Sources

Logs are automatically sourced from:
1. **Systemd service**: `journalctl -u automagik-agents`
2. **Docker containers**: `docker logs <container>`
3. **Local files**: `logs/automagik.log`

### Advanced Log Viewing

```bash
make logs-docker            # Interactive Docker container selection
make logs-all               # View logs from all sources
```

**Log Colorization:** Logs are automatically colorized using `ccze` when available, with graceful fallback to plain text.

## Force Mode

Use `FORCE=1` to override conflict detection and force start services:

```bash
# These check for conflicts first
make dev                    # Will warn if services are running
make docker                 # Will check for port conflicts

# These force start (stop existing services)
make dev FORCE=1            # Stop existing services and start dev
make docker FORCE=1         # Force start Docker stack
make prod FORCE=1           # Force start production mode
```

## Multi-Instance Management

The Makefile system can manage multiple instances simultaneously:

### Running Multiple Modes

```bash
# Start development on default port
make dev

# Start production on different port (via .env.prod)
make prod

# Check all running instances
make status                 # Shows all instances in one table
```

### Instance Types Detected

- **Docker containers**: All automagik-related containers
- **Local processes**: uvicorn processes running automagik
- **Systemd services**: automagik-agents systemd service

## Manual Server Startup (Advanced)

For advanced debugging or custom configurations:

```bash
# Activate virtual environment (done automatically by make)
source .venv/bin/activate

# Start manually with custom options
uvicorn src.main:app --host 0.0.0.0 --port 8881 --reload

# Or use make with custom environment
AM_PORT=8882 make dev
```

## Environment Detection

The Makefile automatically detects your environment:

- **Development**: Uses `.env` file, local Python
- **Production**: Uses `.env.prod` file, Docker containers
- **Mixed**: Can run multiple modes simultaneously

## Accessing the API

Once services are running, access:

*   **API Endpoints:** `http://localhost:${AM_PORT}/api/v1/`
*   **Interactive Documentation (Swagger UI):** `http://localhost:${AM_PORT}/docs`
*   **Alternative Documentation (ReDoc):** `http://localhost:${AM_PORT}/redoc`
*   **Health Check:** `http://localhost:${AM_PORT}/health`

**Port Detection:** Use `make status` to see which ports services are running on.

## Development Workflow

### Typical Development Session

```bash
# Start development environment
make install-dev            # One-time setup
make dev                    # Start development mode

# Monitor during development
make logs-f                 # Follow logs in separate terminal
make status                 # Check status periodically

# Development tools
make test                   # Run tests
make lint                   # Check code quality
make format                 # Format code

# Stop when done
make stop                   # Stop all services
```

### Production Deployment

```bash
# Deploy to production
make install-prod           # One-time setup
make prod                   # Start production stack

# Monitor production
make health                 # Regular health checks
make status                 # Monitor all services
make logs                   # Check for issues
```

## Troubleshooting

### Service Won't Start

```bash
# Check what's running
make status

# Stop conflicting services
make stop

# Force start
make dev FORCE=1
```

### Port Conflicts

```bash
# Check port usage
make status                 # Shows all ports in use

# Change port in environment file
nano .env                   # Edit AM_PORT
```

### Database Issues

```bash
# Check database status
make status                 # Look for database containers/services
make health                 # Database connectivity check

# Restart database
make install-postgres       # Restart PostgreSQL
make db-init               # Initialize if needed
```

### Log Analysis

```bash
# View all logs for debugging
make logs-all

# Follow specific container logs
make logs-docker            # Interactive selection

# Check specific services
journalctl -u automagik-agents -f  # Systemd service logs
docker logs -f automagik_agents    # Docker container logs
```

## Environment Differences

### Development vs Production

| Feature | Development (`make dev`) | Production (`make prod`) |
|---------|-------------------------|-------------------------|
| **Reload** | Auto-reload enabled | No auto-reload |
| **Environment** | Uses `.env` | Uses `.env.prod` |
| **Mode** | Local Python process | Docker containers |
| **Logging** | Verbose logging | Production logging |
| **Port** | Default AM_PORT | Production ports |

### Force Mode Effects

| Command | Normal Behavior | Force Mode (`FORCE=1`) |
|---------|----------------|------------------------|
| `make dev` | Checks for conflicts | Stops existing services |
| `make docker` | Warns about ports | Forces container restart |
| `make prod` | Checks prerequisites | Forces production start |

For more information, see:
- [Makefile Reference](./makefile-reference.md) - Complete command reference
- [Setup Guide](./setup.md) - Installation procedures
- [Configuration Guide](./configuration.md) - Environment configuration 