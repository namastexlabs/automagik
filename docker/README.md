# Docker Setup for AutoMagik Agents

This directory contains Docker Compose configuration for running the infrastructure components needed for AutoMagik Agents.

## Services

1. **PostgreSQL**: Main database for AutoMagik Agents
2. **Neo4j**: Graph database for knowledge graph storage
3. **Graphiti**: Knowledge graph service integrating with Neo4j

## Getting Started

### Option 1: Using the Project .env File (Recommended)

Run the docker-compose using the root .env file:

```bash
cd docker
docker-compose --env-file ../.env up -d
```

### Option 2: Using .env.docker

1. First, copy and configure the environment variables:

```bash
cp .env.docker .env.local
```

2. Edit `.env.local` to set your actual values (especially your OpenAI API key)

3. Start the services:

```bash
docker-compose --env-file .env.local up -d
```

## Accessing the Services

- **PostgreSQL**: Available at `localhost:5432`
- **Neo4j Browser**: Available at `http://localhost:7474`
- **Neo4j Bolt**: Available at `bolt://localhost:7687`
- **Graphiti API**: Available at `http://localhost:8000`

## Volumes

The setup creates the following persistent volumes:

- `estruturar_postgres_data`: PostgreSQL data
- `neo4j_data`: Neo4j data

## Configuration

Key environment variables:

- `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`: PostgreSQL credentials
- `NEO4J_USERNAME`, `NEO4J_PASSWORD`: Neo4j credentials
- `OPENAI_API_KEY`: Required for Graphiti's LLM functionality
- `GRAPHITI_NAMESPACE_ID`: Project namespace for Graphiti
- `GRAPHITI_ENV`: Environment for Graphiti (development, production, etc.)

## Stopping the Services

```bash
docker-compose down
```

To remove volumes as well:

```bash
docker-compose down -v
``` 