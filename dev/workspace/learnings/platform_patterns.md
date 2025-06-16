# Platform Patterns

## Automagik Agents Platform Architecture
- Agent Framework → Memory Layer → API Layer → Deployment Layer → Integration Layer → Orchestration Layer
- Template-based agent creation with multi-LLM support
- Neo4j/Graphiti knowledge graph integration
- Production deployment with Docker, systemd, PM2-style management
- MCP Protocol tool integration (Linear, memory, SQLite)

## Workflow Orchestration
- Sequential: BUILDER → GUARDIAN → SHIPPER
- Parallel: Multiple features with independent workflows
- Context coordination through GENIE's persistent workspace
- Real Linear synchronization with task tracking

## Development Standards
- FastAPI + Pydantic AI + PostgreSQL/SQLite architecture
- Multi-LLM provider support (OpenAI, Gemini, Claude, Groq)
- Comprehensive testing with asyncio and mocking patterns
- Security validation and performance optimization
- Zero-config deployment optimization