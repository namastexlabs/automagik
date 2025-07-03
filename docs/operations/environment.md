# Environment Detection and Loading System

**Part of NMSTX-108**: Environment file detection and loading for Makefile integration.

## Overview

The environment loading system provides intelligent detection and loading of environment configuration files based on deployment mode, supporting both development and production environments with automatic fallback and validation.

## Features

### 🎯 Smart Environment Detection
- **Automatic mode detection** (development/production)
- **Container-based detection** using Docker standardization
- **Environment variable analysis** (ENVIRONMENT setting)
- **Port-based inference** for production mode

### 📁 Multi-File Support
- **Development**: `.env` (default)
- **Production**: `.env.prod` (auto-detected)
- **Template**: `.env.example` (for creation)

### 🔧 Variable Management
- **Safe parsing** with comment and quote handling
- **Port extraction** with configurable defaults
- **Variable validation** with required/optional classification
- **Feature detection** (neo4j, graphiti, discord, notion)

### 🎨 Integration Ready
- **Makefile compatible** shell functions
- **Purple-themed output** matching epic design
- **Error handling** with clear status codes
- **Sourcing support** for function reuse

## Usage

### Command Line Interface

```bash
# Environment information
./scripts/env_loader.sh info

# Load environment variables
./scripts/env_loader.sh load

# Validate configuration
./scripts/env_loader.sh validate

# Get specific values
./scripts/env_loader.sh get-port
./scripts/env_loader.sh get-port POSTGRES_PORT 5432
./scripts/env_loader.sh get-var DATABASE_URL

# Feature detection
./scripts/env_loader.sh supports graphiti
./scripts/env_loader.sh supports neo4j

# Mode detection
./scripts/env_loader.sh detect
```

### Makefile Integration

```makefile
# Load environment for target
load-env:
    @./scripts/env_loader.sh load

# Validate before starting
validate-env:
    @./scripts/env_loader.sh validate

# Get port dynamically
start-dev:
    @PORT=$$(./scripts/env_loader.sh get-port) && \
     echo "Starting on port $$PORT..."

# Feature-conditional targets
start-with-neo4j:
    @if [ "$$(./scripts/env_loader.sh supports neo4j)" = "yes" ]; then \
        echo "Starting with Neo4j support..."; \
     else \
        echo "Neo4j not configured, skipping..."; \
     fi
```

### Source Integration

```bash
# Source functions for reuse
source ./scripts/env_loader.sh

# Use functions directly
env_file=$(get_env_file)
port=$(get_port "AUTOMAGIK_API_PORT" "8881")
if env_supports_feature "graphiti"; then
    echo "Graphiti enabled"
fi
```

## Environment Detection Logic

### Mode Detection Algorithm

1. **Check for .env.prod** existence
2. **Analyze ENVIRONMENT** settings in both files
3. **Check Docker containers** for production naming
4. **Port analysis** for production indicators
5. **Default to development** if unclear

### Detection Examples

```bash
# Production indicators:
# - .env.prod exists AND ENVIRONMENT=production
# - Production containers running (automagik-agents-prod)
# - Production ports in use (18881)

# Development fallback:
# - Only .env exists
# - ENVIRONMENT=development
# - No production containers
```

## Variable Validation

### Required Variables
- `AUTOMAGIK_API_KEY` - API authentication key
- `AUTOMAGIK_API_PORT` - Server port
- `DATABASE_URL` - Database connection string

### Optional but Important
- `OPENAI_API_KEY` - LLM integration
- `POSTGRES_HOST` - Database host
- `POSTGRES_PORT` - Database port

### Validation Output
```
🔍 Validating environment variables...
  ✓ AUTOMAGIK_API_KEY: configured
  ✓ AUTOMAGIK_API_PORT: configured
  ✓ DATABASE_URL: configured
  ✓ OPENAI_API_KEY: configured
  ⚠ NEO4J_URI: not set (optional)
✅ Environment validation passed
```

## Feature Detection

### Supported Features

| Feature | Detection Logic |
|---------|----------------|
| `neo4j` | NEO4J_URI set and not default |
| `graphiti` | GRAPHITI_QUEUE_ENABLED=true |
| `discord` | DISCORD_BOT_TOKEN set and not placeholder |
| `notion` | NOTION_TOKEN set and not placeholder |

### Usage Examples

```bash
# Check before enabling features
if ./scripts/env_loader.sh supports graphiti; then
    echo "Enabling Graphiti memory system"
fi

# Conditional service startup
./scripts/env_loader.sh supports neo4j && start_neo4j_container
```

## Integration with Other Components

### Docker Standardization (NMSTX-102)
- Uses standardized container naming for detection
- Detects `automagik-agents-prod` containers
- Port mapping detection from standardized compose files

### Status Display (NMSTX-101)
- Provides port information for status table
- Environment mode for display context
- Feature flags for service detection

### Health Check (NMSTX-105)
- Port configuration for health endpoints
- Feature detection for optional services
- Environment-specific service requirements

## Error Handling

### Exit Codes
- `0` - Success
- `1` - File not found or validation failed
- `>1` - Number of validation errors

### Error Messages
```bash
❌ Environment file not found: .env
❌ Cannot validate: environment file not found
❌ Environment validation failed with 2 error(s)
⚠️  Warning: NEO4J_URI not set in .env
```

## Configuration Files

### File Locations
```
.env         - Development environment
.env.prod    - Production environment  
.env.example - Template for new environments
```

### Variable Format
```bash
# Comments supported
AUTOMAGIK_API_PORT=8881
AUTOMAGIK_API_HOST="0.0.0.0"  # Quotes handled
DATABASE_URL=postgresql://user:pass@host:port/db  # No quotes needed
```

## Examples

### Development Workflow
```bash
# 1. Check environment
./scripts/env_loader.sh info

# 2. Validate before starting
./scripts/env_loader.sh validate

# 3. Load and start
./scripts/env_loader.sh load
PORT=$(./scripts/env_loader.sh get-port)
uvicorn src.main:app --host 0.0.0.0 --port $PORT --reload
```

### Production Deployment
```bash
# 1. Detect mode
MODE=$(./scripts/env_loader.sh detect)
echo "Detected mode: $MODE"

# 2. Load appropriate environment
./scripts/env_loader.sh load  # Automatically uses .env.prod

# 3. Validate production requirements
./scripts/env_loader.sh validate

# 4. Start production services
docker-compose -f docker/docker-compose-prod.yml up -d
```

### Makefile Integration Demo
```bash
# Test all Makefile integration scenarios
./scripts/makefile_env_demo.sh help

# Specific tests
./scripts/makefile_env_demo.sh env-info
./scripts/makefile_env_demo.sh start-dev
./scripts/makefile_env_demo.sh env-check-features
```

## Best Practices

### ✅ Do
- Always validate before starting services
- Use port detection instead of hardcoding
- Check feature support before enabling
- Handle missing environment files gracefully
- Use sourcing for function reuse in complex scripts

### ❌ Don't
- Hardcode ports or hostnames
- Skip environment validation
- Assume .env files exist
- Mix development and production settings
- Ignore validation errors

## Future Enhancements

### Planned Features
- **Environment switching** (`make switch-env prod`)
- **Variable encryption** for sensitive values
- **Environment inheritance** (.env.local overrides)
- **Schema validation** with JSON schemas
- **Auto-migration** between environment versions

### Integration Opportunities
- **CI/CD integration** for environment validation
- **Secret management** integration (HashiCorp Vault)
- **Configuration drift detection**
- **Environment documentation** generation

---

**Status**: Production ready for Makefile integration! 🚀

**See Also**: 
- [Docker Operations](docker.md) - Container management and best practices
- [Makefile Migration Epic](../README.md) - Overall project context 