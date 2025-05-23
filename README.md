<p align="center">
  <img src=".github/images/automagik_logo.png" alt="AutoMagik Logo" width="600"/>
</p>

## 🚀 From Ideas to Production in Minutes

Automagik Agents is a powerful deployment layer over Pydantic AI that accelerates your AI agent development from concept to production. Born from our daily work at Namastex Labs, it provides a reliable, tested foundation for rapidly building, deploying, and managing AI agents with advanced capabilities like persistent memory and knowledge graph integration.

We built Automagik because we needed to save time while creating high-quality, production-ready agents. By focusing on standardized patterns, best practices, and reusable components, Automagik lets you create sophisticated AI assistants in minutes instead of days.

## 🌟 Features

### 🤖 **Extensible Agent System**
- Template-based agent creation with built-in best practices
- Ready-to-use templates: Simple Agent, Sofia Agent, Notion Agent, Discord Agent
- Easy-to-use CLI for creating and managing agents
- Automatic tool registration and management
- High-performance async architecture

### 🌐 **Powerful API Integration**
- FastAPI-based RESTful endpoints with automatic documentation
- Session management with conversation history
- Structured request/response models with validation
- Built-in authentication and CORS support
- Health monitoring and version tracking
- **Performance**: 200+ req/sec capability with proper configuration

### 🧠 **Advanced Memory System**
- Persistent conversation history with PostgreSQL storage
- Session-based memory management
- Tool call and output tracking
- Agent-specific memories with customizable access controls
- Dynamic memory injection via `{{variable}}` templating
- Memory creation, reading, and updating tools

### 📊 **Knowledge Graph Integration (Graphiti)**
- **Async Queue System**: High-performance background processing
- **Scalable Architecture**: Handles thousands of requests without blocking
- **Configurable Performance**: Adjustable workers, queue size, and retry logic
- **Fast Mock Mode**: Testing without real Graphiti overhead
- **Complete Disable Options**: Multiple levels of Graphiti control
- Automatic storage of user interactions as episodes
- Built-in Neo4j connectivity for graph database operations
- Groundwork for advanced knowledge extraction and retrieval

### 🧪 **Comprehensive Testing & Benchmarking**
- **Mock Agent Testing**: Fast infrastructure testing without API costs
- **Real API Benchmarks**: End-to-end performance validation
- **Stress Testing Suite**: Validate performance under load
- **Automated Reporting**: Markdown reports with performance metrics
- **CPU & Memory Monitoring**: System resource tracking

### 📋 **Built-in Templates**
- **Simple Agent**: Basic chat functionality with memory tools
- **Sofia Agent**: Memory-enhanced agent with comprehensive knowledge management
- **Notion Agent**: Full Notion integration with database management
- **Discord Agent**: Discord integration for managing servers and channels

## 🚀 Quick Start

### 1. Installation

```bash
git clone https://github.com/namastexlabs/automagik-agents
cd automagik-agents
```

Create and manage a virtual environment using [uv](https://docs.astral.sh/uv/):
```bash
uv venv

# On Linux/macOS/WSL
source .venv/bin/activate

# On Windows
.venv/Scripts/activate

# Install dependencies
uv pip install -e .
```

### 2. Environment Setup

```bash
# Copy example environment file
cp .env-example .env
```

Configure required variables in `.env`:
```bash
# Required - Authentication
AM_API_KEY=your_api_key_here
OPENAI_API_KEY=your_openai_key_here
DISCORD_BOT_TOKEN=your_discord_token

# Server Configuration
AM_HOST=0.0.0.0
AM_PORT=8881
AM_ENV=development

# Database
DATABASE_URL=postgresql://automagik:automagik@localhost:5432/automagik_agents

# Optional - Graphiti Knowledge Graph
GRAPHITI_ENABLED=true
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_password

# Optional - Third-party Integrations
NOTION_TOKEN=your_notion_token
AIRTABLE_TOKEN=your_airtable_token
```

### 3. Database Setup

**Option A: Docker Compose (Recommended)**
```bash
cd docker/
docker-compose --env-file ../.env up -d postgres
```

**Option B: Existing Database**
Update `DATABASE_URL` in `.env` with your connection string.

**Initialize Database Structure:**
```bash
automagik-agents db init
```

### 4. Optional: Graphiti Setup

For knowledge graph functionality:
```bash
cd docker
docker-compose --env-file ../.env up -d neo4j
```

Neo4j will be available at http://localhost:7474

### 5. Start the API Server

```bash
automagik-agents api start --reload
```

### 6. Verify Installation

**Health Check:**
```bash
curl http://localhost:8881/health
```

**Start Your First Chat:**
```bash
automagik-agents agent chat start --agent simple
```

## 💡 Usage Examples

### CLI Commands

**Interactive Chat**
```bash
# Start chat session
automagik-agents agent chat start --agent simple_agent

# List available agents
automagik-agents agent chat list
```

**Agent Testing**
```bash
# Single message
automagik-agents agent run message --agent simple_agent --message "What time is it?"

# With session continuity
automagik-agents agent run message --agent simple_agent --session my_session --message "Remember: I like coffee"
automagik-agents agent run message --agent simple_agent --session my_session --message "What do I like?"
```

**Debug Mode**
```bash
automagik-agents --debug agent run message --agent simple_agent --message "Debug test"
```

### API Endpoints

**Agent Interaction**
```bash
# Run agent
curl -X POST http://localhost:8881/api/v1/agent/simple_agent/run \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "message_content": "What time is it?",
    "session_name": "my_session"
  }'
```

**Memory Management**
```bash
# Create memory
curl -X POST http://localhost:8881/api/v1/memories \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "user_preference",
    "content": "User prefers dark mode",
    "agent_id": 1,
    "read_mode": "tool_calling"
  }'
```

**Session Management**
```bash
# Get session history
curl http://localhost:8881/api/v1/sessions/my_session \
  -H "X-API-Key: your_api_key"
```

## 🧪 Testing & Benchmarking

### Performance Benchmarking

**Mock Testing (Fast Infrastructure Testing)**
```bash
# Quick infrastructure test
python scripts/benchmarks/comprehensive_benchmark.py --mode mock

# Mock tests don't hit real APIs - perfect for CI/CD
```

**Real API Testing**
```bash
# End-to-end performance testing
python scripts/benchmarks/comprehensive_benchmark.py --mode api --api-key your-key

# Full stack validation with real OpenAI calls
```

**Custom Benchmarks**
```bash
# Individual stress test
python scripts/benchmarks/api_stress_test.py \
  --base-url http://localhost:8881 \
  --test-type agent_run \
  --concurrency 50 \
  --requests 500 \
  --api-key your-key
```

### Test Suite

**Run All Tests**
```bash
python tests/run_all_tests.py
```

**Specific Test Categories**
```bash
# Memory tests only
python tests/run_all_tests.py --memory --no-api --no-cli

# Verbose output
python tests/run_all_tests.py --verbose
```

### Benchmark Reports

Results are automatically saved to `scripts/benchmarks/benchmark/`:
- `benchmark_report_v{version}_{date}.md` - Human-readable report
- `benchmark_data_v{version}_{date}.json` - Machine-readable data

## ⚙️ Graphiti Configuration

### Performance Modes

**High Performance (Default)**
```bash
GRAPHITI_ENABLED=true
GRAPHITI_QUEUE_ENABLED=true
GRAPHITI_QUEUE_MAX_WORKERS=10
GRAPHITI_MOCK_ENABLED=false
```

**Testing Mode (Fast)**
```bash
GRAPHITI_ENABLED=true
GRAPHITI_MOCK_ENABLED=true  # 1ms mock operations
```

**Disabled Mode**
```bash
GRAPHITI_ENABLED=false  # Master disable switch
```

### Queue Configuration

```bash
# Performance tuning
GRAPHITI_QUEUE_MAX_WORKERS=10        # Concurrent background workers
GRAPHITI_QUEUE_MAX_SIZE=1000         # Queue capacity
GRAPHITI_QUEUE_RETRY_ATTEMPTS=3      # Retry failed operations
GRAPHITI_BACKGROUND_MODE=true        # Async processing
```

### Monitoring

```bash
# Check queue status
curl -H "x-api-key: your-key" http://localhost:8881/health/graphiti-queue
```

## 🔧 Creating Custom Agents

### 1. Generate Agent Template

```bash
automagik-agents agent create agent --name custom_agent --template simple_agent
```

### 2. Customize Agent Files

**Prompt Template** (`src/agents/simple/custom_agent/prompts/prompt.py`):
```python
AGENT_PROMPT = """
You are {{agent_name}} with personality: {{personality}}.
Current user preferences: {{user_preferences}}

Your capabilities include:
- Memory management
- Tool usage
- Custom functionality
"""
```

**Agent Implementation** (`src/agents/simple/custom_agent/agent.py`):
```python
def register_tools(self):
    """Register tools with the agent."""
    # Built-in memory tools
    from src.tools.memory_tools import read_memory, create_memory
    self.agent.tool(read_memory)
    self.agent.tool(create_memory)
    
    # Custom tools
    self.agent.tool(self.custom_tool)

def custom_tool(self, query: str) -> str:
    """Custom tool description."""
    return f"Processed: {query}"
```

### 3. Dynamic Memory System

**Template Variables**: Use `{{variable_name}}` syntax in prompts
**Memory Creation**: Create memories with matching names
**Automatic Injection**: Values are injected at runtime

```bash
# Create memory for template variable
curl -X POST http://localhost:8881/api/v1/memories \
  -d '{
    "name": "personality",
    "content": "friendly and helpful",
    "agent_id": 1,
    "read_mode": "system_prompt"
  }'
```

## 📊 Performance Metrics

### Benchmark Results (v0.1.3)

**Infrastructure Performance (Mock Mode)**:
- **Peak Throughput**: 585 req/sec
- **Mean Latency**: 0.7ms
- **Concurrency**: 500 concurrent requests
- **Error Rate**: 0%

**Real API Performance**:
- **Throughput**: 2.86 req/sec (OpenAI limited)
- **Queue Success**: 0% error rate (fixed from 85%)
- **Memory Usage**: ~55MB peak
- **CPU Efficiency**: <1% average

### Configuration Recommendations

**Development**:
```bash
GRAPHITI_MOCK_ENABLED=true    # Fast testing
AM_LOG_LEVEL=DEBUG           # Detailed logging
```

**Production**:
```bash
GRAPHITI_ENABLED=true
GRAPHITI_QUEUE_MAX_WORKERS=20
LLM_MAX_CONCURRENT_REQUESTS=30
UVICORN_LIMIT_CONCURRENCY=200
```

## 🚧 Troubleshooting

### Common Issues

**Graphiti Queue Issues**:
```bash
# Check queue status
curl -H "x-api-key: your-key" http://localhost:8881/health/graphiti-queue

# Disable if needed
GRAPHITI_ENABLED=false
```

**Performance Issues**:
```bash
# Enable verbose logging
AM_VERBOSE_LOGGING=true
AM_LOG_TO_FILE=true

# Run benchmark
python scripts/benchmarks/comprehensive_benchmark.py --mode mock
```

**Database Connection**:
```bash
# Test database
automagik-agents db check

# Reset if needed
automagik-agents db reset
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 API Documentation

Interactive API documentation available at:
- **Swagger UI**: http://localhost:8881/api/v1/docs
- **ReDoc**: http://localhost:8881/api/v1/redoc

## 🗺️ Roadmap

- **Graph Agents**: Advanced agent orchestration and workflows
- **MCP Integration**: Model Context Protocol for tool reusability
- **Smart Context Management**: Optimal handling of large context windows
- **Enhanced Benchmarking**: Real-time performance monitoring
- **Agent Analytics**: Usage patterns and optimization insights
- **Deployment Tools**: One-click deployment to major cloud providers

## 🔗 Resources

- **Documentation**: [Full documentation](docs/)
- **Benchmarks**: [Performance reports](scripts/benchmarks/benchmark/)
- **Examples**: [Example agents](examples/)
- **Discord**: [Join our community](https://discord.gg/xcW8c7fF3R)

---

Automagik Agents is and will always be open source. Since this is our daily work tool at Namastex Labs, we provide high priority maintenance and updates.
