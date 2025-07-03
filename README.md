<p align="center">
  <img src=".github/images/automagik_logo.png" alt="AutoMagik Logo" width="600"/>
</p>

## 🚀 AI Agents from Ideas to Production in Minutes

Automagik Agents is a powerful deployment layer over Pydantic AI that accelerates your AI agent development from concept to production. Born from our daily work at Namastex Labs, it provides a reliable, tested foundation for rapidly building, deploying, and managing AI agents with advanced capabilities like persistent memory and tool integration.

We built Automagik because we needed to save time while creating high-quality, production-ready agents. By focusing on standardized patterns, best practices, and reusable components, Automagik lets you create sophisticated AI assistants in minutes instead of days.

## ⚠️ **Important: Requires API Keys**

Agents need LLM provider keys to function. Examples: `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`. Get them from [OpenAI](https://platform.openai.com/api-keys), [Google AI Studio](https://makersuite.google.com/app/apikey), or [Anthropic](https://console.anthropic.com/).

## 🌟 What Makes Automagik Special

- **🤖 Extensible Agent System**: Template-based creation, automatic tool registration, and easy CLI for new agents
- **💾 Advanced Memory System**: Persistent conversations with dynamic `{{variable}}` templating that automatically injects context
- **🔧 Production-Ready API**: FastAPI endpoints with authentication, session management, and health monitoring
- **🧠 Knowledge Graph Integration**: Built-in Neo4j/Graphiti support for semantic understanding and complex reasoning
- **🔗 Multiple LLM Support**: Works with OpenAI, Gemini, Claude, Groq, and more - switch providers easily
- **📦 Zero-Config Deployment**: Docker and local installation with automated dependency management

## 🚀 Quick Start

```bash
git clone https://github.com/namastexlabs/automagik-agents.git
cd automagik-agents

# Show all available commands
make help

# Quick installation and startup
make install-dev    # Install development environment
make dev           # Start development mode

# Check status and logs
make status        # PM2-style status of all instances
make logs          # View colorized logs
```

**Auto-Install Prerequisites:**
```bash
# Install system dependencies (all platforms)
make install-prerequisites

# Quick environment setup
make install        # Auto-detects best installation mode
```

**Installation Modes:**
```bash
# Development (local Python + venv)
make install-dev

# Docker development
make install-docker

# Production Docker
make install-prod

# Systemd service
make install-service
```

## 📦 Pip Installation

You can also install Automagik as a Python package:

```bash
# Install from local directory
pip install -e /path/to/automagik-agents

# Or from git (coming soon)
# pip install git+https://github.com/namastexlabs/automagik-agents.git
```

**After pip installation:**
```bash
# Start server with default settings
automagik-server

# Start on custom port
automagik-server --port 38881

# Specify external agents directory
automagik-server --agents-dir /path/to/my/agents

# Or use environment variables
export AUTOMAGIK_API_PORT=38881
export AUTOMAGIK_EXTERNAL_AGENTS_DIR=/path/to/my/agents
automagik-server
```

**Default External Agents Directory:** `./automagik_agents`

This is where you can place custom agents that will be automatically discovered when the server starts. The directory is created relative to your current working directory. Each agent should be in its own subdirectory with an `agent.py` file containing a `create_agent` factory function.

**Creating an External Agent:**
```python
# ./automagik_agents/my_custom_agent/agent.py
from typing import Dict, Optional
from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.dependencies import AutomagikAgentsDependencies

def create_agent(config: Optional[Dict[str, str]] = None) -> AutomagikAgent:
    """Factory function to create your custom agent."""
    return MyCustomAgent(config or {})

class MyCustomAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]):
        super().__init__(config)
        self._code_prompt_text = "Your agent prompt here"
        self.dependencies = AutomagikAgentsDependencies(
            model_name=config.get("model", "openai:gpt-4o-mini"),
            model_settings={},
            api_keys={},
            tool_config={}
        )
        self.tool_registry.register_default_tools(self.context)
    
    @property
    def model_name(self) -> str:
        return self.dependencies.model_name or "openai:gpt-4o-mini"
```

## 📝 Post-Installation

1. **Add your API keys:**
```bash
nano .env
# Add: OPENAI_API_KEY=sk-your-actual-key
# Default API Key: namastex888 (unless AUTOMAGIK_API_KEY is set)
```

2. **Start and monitor:**
```bash
make dev           # Start development mode
make status        # Show PM2-style status table
make logs-f        # Follow logs in real-time
```

3. **Test it:**
```bash
curl http://localhost:${AUTOMAGIK_API_PORT}/health
```

## 🎯 Usage

### Make Commands

```bash
# 🚀 Quick Start
make help                    # Show all available commands
make install-dev            # Install development environment  
make dev                     # Start development mode

# 📊 Monitoring & Status
make status                  # PM2-style status table of all instances
make status-quick           # Quick one-line status summary
make health                 # Check health of all services
make logs                   # View colorized logs (auto-detect source)
make logs-f                 # Follow logs in real-time

# 🎛️ Service Management  
make start                  # Start services (auto-detect mode)
make stop                   # Stop all services
make restart                # Restart services
make docker                 # Start Docker development stack
make prod                   # Start production Docker stack

# 🗄️ Database
make db-init               # Initialize database
make db-migrate            # Run database migrations

# 🛠️ Development
make test                  # Run test suite
make lint                  # Run code linting
make format                # Format code with ruff
```

**Force Mode for Conflicts:**
```bash
make dev FORCE=1           # Stop existing services and start dev
make docker FORCE=1        # Force start Docker stack
```

### API Examples
```bash
# Test agent (using default API key)
curl -X POST http://localhost:${AUTOMAGIK_API_PORT}/api/v1/agent/simple/run \
  -H "X-API-Key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{"message_content": "Hello!", "session_name": "test"}'

# Create memory that auto-injects into prompts
curl -X POST http://localhost:${AUTOMAGIK_API_PORT}/api/v1/memories \
  -H "X-API-Key: namastex888" \
  -H "Content-Type: application/json" \
  -d '{"name": "personality", "content": "friendly and helpful", "agent_id": 1}'
```

## Useful Endpoints

*   **API Docs:** `http://localhost:${AUTOMAGIK_API_PORT}/docs`
*   **Health Check:** `http://localhost:${AUTOMAGIK_API_PORT}/health`
*   **List Agents:** `http://localhost:${AUTOMAGIK_API_PORT}/api/v1/agents`

## 🛠️ Create Custom Agents

```bash
# Create new agent
make create-agent name=my_agent type=simple

# Or use CLI
automagik agents create -n my_agent -t simple
# Customize: src/agents/simple/my_agent/
```

## 🔧 Configuration

Edit `.env` with your keys:
```bash
# LLM Providers (choose one or more)
OPENAI_API_KEY=sk-your-key
GEMINI_API_KEY=your-key  
ANTHROPIC_API_KEY=your-key

# Platform Integrations (optional)
DISCORD_BOT_TOKEN=your-token
NOTION_TOKEN=your-token
```

## 🗺️ Roadmap

- **Graph Agents**: Advanced agent orchestration and workflows 
- **Heartbeat Mode**: Keep agents alive 24/7 doing autonomous tasks
- **MCP Integration**: Model Context Protocol for easier tool reusing
- **Support for Other Agent Frameworks**: Expand compatibility beyond Pydantic AI
- **Smart Context Management**: Optimal handling of large context windows

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

---

<p align="center">
  <b>Part of the AutoMagik Ecosystem</b><br>
  <a href="https://github.com/namastexlabs/automagik">AutoMagik</a> |
  <a href="https://github.com/namastexlabs/automagik-agents">AutoMagik Agents</a> |
  <a href="https://github.com/namastexlabs/automagik-ui">AutoMagik UI</a>
</p>

**Automagik Agents is and will always be open source.** Since this is our daily work tool at Namastex Labs, we provide high priority maintenance and regular updates. We built this because we believe AI agent development should be fast, reliable, and production-ready from day one.
