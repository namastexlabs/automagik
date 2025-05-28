# Archived Shell Scripts

This directory contains the original shell-based installation scripts that were replaced by the new Makefile system.

## 📅 **Archive Date**: January 28, 2025

## 🚀 **Migration Context**

These scripts were part of the **Makefile Migration Epic (NMSTX-113)** that modernized the automagik-agents installation and deployment system.

### **What Was Replaced**

| Old Script | New Makefile Target | Notes |
|------------|-------------------|-------|
| `setup.sh` | `make install` | Auto-detection and installation |
| `setup.sh --mode docker` | `make install-docker` | Docker development |
| `setup.sh --mode local --install-service` | `make install-service` | Systemd service |
| `installers/agents.sh` | `make install-dev` | Development environment |
| `installers/docker.sh` | `make install-docker` | Docker stack |

### **Why Migrated**

- **🎯 AI-Friendly**: Declarative commands that AI agents can easily parse
- **📊 Better Monitoring**: PM2-style status displays with real-time health
- **🔧 Multi-Platform**: Automatic OS detection and package management
- **🎨 Beautiful Output**: Colorized logs and status with automagik purple theme
- **⚡ Force Mode**: Override conflicts and manage multiple instances
- **🩺 Health Checks**: Comprehensive service monitoring

## 📁 **Archive Contents**

### **Core Scripts**
- `setup.sh` - Main installation script (306 lines)
- `installers/agents.sh` - Agent installation (722 lines)
- `installers/docker.sh` - Docker setup (683 lines)
- `installers/quick-update.sh` - Quick update utility (399 lines)

### **Library Functions**
- `lib/common.sh` - Common utilities (180 lines)
- `lib/config.sh` - Configuration management (386 lines)
- `lib/python.sh` - Python environment setup (271 lines)
- `lib/service.sh` - Service management (322 lines)
- `lib/system.sh` - System detection and packages (506 lines)

### **Templates**
- `templates/` - Configuration templates and helpers

## 🔄 **Migration Guide**

For teams migrating from these scripts:

### **Quick Reference**
```bash
# Old way (archived)
bash scripts/install/setup.sh

# New way (current)
make install
```

### **Full Migration Commands**
```bash
# Show all available commands
make help

# Install development environment
make install-dev

# Start development mode
make dev

# Check status with beautiful PM2-style display
make status

# View colorized logs
make logs
```

## 📚 **Documentation**

- **[docs/makefile-reference.md](../../docs/makefile-reference.md)** - Complete command reference
- **[docs/migration-guide.md](../../docs/migration-guide.md)** - Detailed migration guide
- **[docs/setup.md](../../docs/setup.md)** - New installation guide
- **[docs/running.md](../../docs/running.md)** - Service management guide

## ⚠️ **Important Notes**

1. **These scripts are NO LONGER MAINTAINED**
2. **Use the new Makefile system for all operations**
3. **Scripts preserved for reference and rollback purposes only**
4. **Git history preserved - no commits were lost**

## 🆘 **Emergency Rollback**

If needed, these scripts can be temporarily restored:

```bash
# Copy back (emergency only)
cp -r scripts/install.archive/* scripts/install/

# Use old installation
bash scripts/install/setup.sh
```

**⚠️ Not recommended - use new Makefile system instead!**

---

**Migration completed by**: Automagik AI Agent  
**Linear Epic**: NMSTX-113 - Makefile Migration  
**Documentation**: See [docs/makefile-reference.md](../../docs/makefile-reference.md) 