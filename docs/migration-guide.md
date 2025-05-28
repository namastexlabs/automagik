# Migration Guide: Shell Scripts to Makefile

This guide helps you transition from the old shell-based installation scripts to the new Makefile-based system.

## 🚀 Why Migrate?

The new Makefile system provides:
- **🎯 AI-Friendly**: Declarative commands that AI agents can easily parse
- **📊 Better Monitoring**: PM2-style status displays with real-time health
- **🔧 Multi-Platform**: Automatic OS detection and package management
- **🎨 Beautiful Output**: Colorized logs and status with automagik purple theme
- **⚡ Force Mode**: Override conflicts and manage multiple instances
- **🩺 Health Checks**: Comprehensive service monitoring

## 📋 Command Migration Reference

### Quick Reference Table

| Old Command | New Command | Notes |
|-------------|-------------|-------|
| `bash scripts/install/setup.sh` | `make install-dev` | Auto-detects best mode |
| `bash scripts/install/setup.sh --mode docker` | `make install-docker` | Docker development |
| `bash scripts/install/setup.sh --mode local --install-service` | `make install-service` | Systemd service |
| `automagik agents start` | `make dev` | Development mode |
| `automagik agents start` | `make prod` | Production mode |
| `automagik agents stop` | `make stop` | Stops all services |
| `automagik agents status` | `make status` | Beautiful PM2-style table |
| `automagik agents logs` | `make logs` | Auto-detects log source |
| `docker-compose up -d` | `make docker` | Docker stack |

### Installation Commands

#### Old Shell-Based Installation

```bash
# Old way (deprecated)
git clone https://github.com/namastexlabs/automagik-agents.git
cd automagik-agents
bash scripts/install/setup.sh

# Non-interactive
bash scripts/install/setup.sh --component agents --mode docker \
  --openai-key sk-your-key --non-interactive

# Service installation
bash scripts/install/setup.sh --component agents --mode local \
  --install-service --non-interactive
```

#### New Makefile-Based Installation

```bash
# New way (recommended)
git clone https://github.com/namastexlabs/automagik-agents.git
cd automagik-agents

# Show all available commands
make help

# Auto-install prerequisites and environment
make install-prerequisites    # Install system dependencies
make install                 # Auto-detect best installation mode

# Or choose specific mode
make install-dev             # Development environment
make install-docker          # Docker development
make install-prod            # Production Docker
make install-service         # Systemd service
```

### Service Management Commands

#### Old CLI Commands

```bash
# Old way (still works, but deprecated)
automagik agents start       # Start service
automagik agents stop        # Stop service
automagik agents restart     # Restart service
automagik agents status      # Basic status
automagik agents logs        # Basic logs
automagik agents dev         # Development mode

# Alias system
automagik install-alias      # Install 'agent' alias
agent start                  # Shorter commands
```

#### New Makefile Commands

```bash
# New way (recommended)
make dev                     # Start development mode
make prod                    # Start production mode
make start                   # Auto-detect mode and start
make stop                    # Stop all services
make restart                 # Restart services

# Advanced monitoring
make status                  # PM2-style status table
make status-quick           # One-line summary
make health                 # Comprehensive health check

# Log management
make logs                   # Smart log detection
make logs-f                 # Follow logs in real-time
make logs-docker           # Interactive container selection
make logs-all              # All log sources
```

## 🔄 Step-by-Step Migration

### Step 1: Backup Current Setup

```bash
# Stop current services
automagik agents stop
# or manually
pkill -f uvicorn
docker-compose down

# Backup environment (optional)
cp .env .env.backup
```

### Step 2: Update Repository

```bash
# Pull latest changes with Makefile system
git pull origin main

# Verify Makefile exists
ls -la Makefile
```

### Step 3: Install Prerequisites

```bash
# The new system can install everything automatically
make install-prerequisites

# Verify installation
make verify-prerequisites
make check-system
```

### Step 4: Choose Migration Path

#### Option A: Keep Existing Environment

```bash
# If you have a working .env file, just start the new way
make dev                    # Start development mode
make status                 # Check status with new display
```

#### Option B: Fresh Installation

```bash
# Clean slate approach
make clean                  # Clean temporary files
make venv-clean            # Remove virtual environment
make install-dev           # Fresh development install
```

#### Option C: Docker Migration

```bash
# Move from local to Docker
make stop                  # Stop local services
make install-docker        # Install Docker environment
make docker                # Start Docker stack
```

### Step 5: Verify Migration

```bash
# Check everything is working
make status                # Should show beautiful status table
make health                # Health check all services
make logs                  # View logs

# Test API
curl http://localhost:8881/health
```

## 🎯 Feature Comparisons

### Status Display

#### Old Status Output
```
Service: automagik-agents
Status: active (running)
Port: 8881
```

#### New Status Output
```
💜 Automagik Agents Status
┌────┬─────────────────────────┬──────────┬───────┬────────┬──────────┬──────────┐
│ id │ name                    │ mode     │ port  │ pid    │ uptime   │ status   │
├────┼─────────────────────────┼──────────┼───────┼────────┼──────────┼──────────┤
│ 0  │ automagik_agents        │ docker   │ 8881  │ 32ef3b │ 1h       │ online   │
│ 1  │ automagik_agents_db     │ docker   │ 5432  │ 0bd1e7 │ 1h       │ online   │
└────┴─────────────────────────┴──────────┴───────┴────────┴──────────┴──────────┘
```

### Log Viewing

#### Old Log System
```bash
automagik agents logs       # Basic logs
docker-compose logs -f      # Docker logs manually
journalctl -u automagik-agents -f  # Service logs manually
```

#### New Log System
```bash
make logs                   # Auto-detects source (systemd/docker/file)
make logs-f                 # Follow with colorization
make logs-docker           # Interactive container selection
make logs-all              # All sources simultaneously
```

### Environment Detection

#### Old System
- Manual mode selection during installation
- No automatic conflict detection
- Manual environment file management

#### New System
- Automatic environment detection (`.env` vs `.env.prod`)
- Automatic mode detection (docker/local/service)
- Conflict detection with force override option
- Multi-instance management

## 🚨 Breaking Changes

### Removed Features

1. **Setup Script Interactive Mode**: Replaced with `make install` auto-detection
2. **CLI Alias System**: Still works but `make` commands are preferred
3. **Manual Docker Compose**: Use `make docker` instead

### Changed Behavior

1. **Force Mode**: Add `FORCE=1` to override conflicts (e.g., `make dev FORCE=1`)
2. **Status Display**: Now shows all instances in PM2-style table
3. **Log Colorization**: Automatic with graceful fallback
4. **Environment Files**: Auto-detects `.env.prod` for production mode

### Migration Required

1. **Installation Scripts**: Update CI/CD to use `make install-*` commands
2. **Monitoring Scripts**: Update to use `make status` and `make health`
3. **Log Processing**: Update to use `make logs` or specific log targets

## 🔧 Advanced Migration Scenarios

### CI/CD Pipeline Migration

#### Old Pipeline
```yaml
# Old CI/CD (deprecated)
- name: Install
  run: bash scripts/install/setup.sh --non-interactive --mode docker
- name: Start
  run: automagik agents start
- name: Test
  run: curl http://localhost:8881/health
```

#### New Pipeline
```yaml
# New CI/CD (recommended)
- name: Install Prerequisites
  run: make install-prerequisites
- name: Install Environment
  run: make install-docker
- name: Start Services
  run: make docker
- name: Health Check
  run: make health
- name: Run Tests
  run: make test
```

### Docker Compose Migration

#### Old Docker Management
```bash
# Old way
cd docker
docker-compose up -d
docker-compose logs -f automagik-agents
docker-compose down
```

#### New Docker Management
```bash
# New way
make docker                 # Start Docker stack
make logs-docker           # Interactive log selection
make stop                  # Stop all services
make docker-clean          # Clean containers/images
```

### Service Management Migration

#### Old Service Control
```bash
# Old systemd approach
sudo systemctl start automagik-agents
sudo systemctl status automagik-agents
journalctl -u automagik-agents -f
```

#### New Service Control
```bash
# New unified approach
make start                 # Auto-detects systemd and starts
make status                # Shows service in status table
make logs                  # Auto-detects systemd logs
```

## ✅ Migration Checklist

### Pre-Migration
- [ ] **Backup environment**: `cp .env .env.backup`
- [ ] **Stop services**: `make stop` or manual cleanup
- [ ] **Document current setup**: Note which mode you're using
- [ ] **Check ports**: Note which ports are in use

### During Migration
- [ ] **Update repository**: `git pull origin main`
- [ ] **Install prerequisites**: `make install-prerequisites`
- [ ] **Verify prerequisites**: `make verify-prerequisites`
- [ ] **Choose installation mode**: `make install-dev/docker/prod`
- [ ] **Start services**: `make dev/docker/prod`

### Post-Migration
- [ ] **Verify status**: `make status` shows expected services
- [ ] **Health check**: `make health` passes
- [ ] **Test API**: `curl http://localhost:8881/health`
- [ ] **Check logs**: `make logs` shows activity
- [ ] **Update scripts**: Modify any automation to use `make` commands

### Troubleshooting Migration
- [ ] **Clean installation**: `make clean && make install-dev`
- [ ] **Check conflicts**: `make status` for conflicting services  
- [ ] **Force start**: `make dev FORCE=1` if conflicts persist
- [ ] **View logs**: `make logs-all` for debugging

## 💡 Best Practices

### Development Workflow
```bash
# Recommended development workflow
make install-dev           # One-time setup
make dev                   # Start development
make logs-f                # Follow logs in separate terminal
make test                  # Run tests during development
make stop                  # Stop when done
```

### Production Deployment
```bash
# Recommended production workflow
make install-prod          # One-time production setup
make prod                  # Start production stack
make health                # Regular health monitoring
make logs                  # Check for issues
```

### Multi-Environment Management
```bash
# Development and production simultaneously
make dev                   # Development on .env
make prod                  # Production on .env.prod
make status                # See both in one table
```

## 🆘 Rollback Procedure

If you need to rollback to the old system:

```bash
# Stop new services
make stop

# Restore old environment
mv .env.backup .env

# Use old commands
automagik agents start
```

**Note**: The old CLI commands still work, but the new Makefile system is recommended for better functionality and monitoring.

## 📚 Additional Resources

- [Makefile Reference](./makefile-reference.md) - Complete command documentation
- [Setup Guide](./setup.md) - Updated installation procedures  
- [Running Guide](./running.md) - Operational procedures with new commands
- [Configuration Guide](./configuration.md) - Environment configuration

## 🎯 Next Steps

After successful migration:

1. **Update documentation**: Modify any internal docs to use `make` commands
2. **Train team**: Ensure team members know the new commands
3. **Update automation**: Migrate CI/CD and scripts to new system
4. **Monitor**: Use `make status` and `make health` for regular monitoring
5. **Optimize**: Explore advanced features like force mode and multi-instance management 