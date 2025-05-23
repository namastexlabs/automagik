# Automagik Modular Installer

This directory contains the next-generation modular installation framework for the Automagik Bundle.

## Quick Start

```bash
# Interactive installation
./scripts/install/setup.sh

# Non-interactive agents installation with Docker
./scripts/install/setup.sh --component agents --mode docker

# Help
./scripts/install/setup.sh --help
```

## Structure

- `setup.sh` - Main orchestrator script
- `lib/` - Shared utility modules
  - `common.sh` - Print functions, logging, error handling
  - `system.sh` - OS detection, package installation
- `installers/` - Component-specific installation scripts
- `templates/` - Configuration templates

## Migration from Legacy Script

The original monolithic `scripts/setup.sh` will remain functional while we build out the modular system. Once feature-complete, it will be replaced.

### Current Status

- ✅ **Common utilities** - Print functions, logging, error handling
- ✅ **System detection** - OS detection, package management
- ⏳ **Python management** - UV installation, virtual environments
- ⏳ **Docker operations** - Container management, smart rebuilds
- ⏳ **Configuration** - Environment files, templates
- ⏳ **Health checks** - API testing, validation
- ⏳ **Service management** - Systemd integration

### Components

- ✅ **Agents installer** - Stub (redirects to legacy script)
- ⏳ **Omni installer** - Coming soon
- ⏳ **Langflow installer** - Coming soon
- ⏳ **Bundle installer** - Coming soon

## Development

To add a new component:

1. Create `installers/{component}.sh`
2. Implement `install_{component}()` function
3. Add component to main menu in `setup.sh`
4. Create templates in `templates/` if needed

## Testing

```bash
# Test system detection
./scripts/install/setup.sh --component agents --mode local --no-docker

# Test help system
./scripts/install/setup.sh --help
``` 