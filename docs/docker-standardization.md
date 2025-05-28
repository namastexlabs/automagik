# Docker Container Standardization

## Overview

As part of the Makefile Migration Epic (NMSTX-99), all Docker containers now follow a standardized naming convention to enable better automation and detection.

## Naming Convention

All automagik-agents containers use the pattern: `automagik-agents-{suffix}`

### Examples
- `automagik-agents-dev` - Development instance
- `automagik-agents-prod` - Production instance  
- `automagik-agents-db` - PostgreSQL database
- `automagik-agents-neo4j` - Neo4j graph database
- `automagik-agents-graphiti` - Graphiti service (dev)
- `automagik-agents-graphiti-prod` - Graphiti service (prod)

## Detection Pattern

Use this Docker command to find all automagik-agents containers:

```bash
docker ps -a --filter "name=automagik-agents-" --format "table {{.Names}}\t{{.State}}\t{{.Ports}}"
```

For running containers only:
```bash
docker ps --filter "name=automagik-agents-" --format "table {{.Names}}\t{{.State}}\t{{.Ports}}"
```

## Environment Variables

### No Hardcoded Ports
All ports are now configurable via environment variables:

- **Development**: `AM_PORT` (default: 8881)
- **Production**: `AM_PORT` (default: 18881) 
- **Database**: `POSTGRES_PORT` (default: 5432)

### Environment Files
- **Development/Docker**: Uses `.env`
- **Production**: Uses `.env.prod`

## Compose File Changes

### docker-compose.yml (Development)
```yaml
services:
  automagik-agents-dev:
    container_name: automagik-agents-dev
    ports:
      - "${AM_PORT:-8881}:${AM_PORT:-8881}"
    environment:
      - AM_PORT=${AM_PORT:-8881}
```

### docker-compose-prod.yml (Production)
```yaml
services:
  automagik-agents-prod:
    container_name: automagik-agents-prod
    ports:
      - "${AM_PORT:-18881}:${AM_PORT:-18881}"
    environment:
      - AM_PORT=${AM_PORT:-18881}
```

## Benefits

1. **Predictable Naming**: All containers follow the same pattern
2. **Easy Detection**: Simple filter pattern finds all instances
3. **Makefile Integration**: Enables automated status checking
4. **Port Flexibility**: No hardcoded values, fully configurable
5. **Environment Awareness**: Uses appropriate config files

## Migration Notes

The old naming patterns have been completely replaced:
- ❌ `automagik_agents` → ✅ `automagik-agents-dev`
- ❌ `automagik_agents_db` → ✅ `automagik-agents-db`
- ❌ `automagik_neo4j` → ✅ `automagik-agents-neo4j`
- ❌ `automagik_graphiti` → ✅ `automagik-agents-graphiti`

## Testing

Use the provided test script to validate detection:

```bash
./dev/test_docker_detection.sh
```

This script verifies that container detection patterns work correctly with the new naming convention. 