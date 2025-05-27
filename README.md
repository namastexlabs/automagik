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
bash scripts/install/setup.sh
```

The installer guides you through:
- **Local**: Python virtual environment (development)
- **Docker**: Containerized deployment (production)

**Non-Interactive Installation:**
```bash
# Docker (recommended for production)
bash scripts/install/setup.sh --component agents --mode docker \
  --openai-key sk-your-key --non-interactive

# Local with service commands
bash scripts/install/setup.sh --component agents --mode local \
  --openai-key sk-your-key --install-service --non-interactive
```

## 📝 Post-Installation

1. **Add your API keys:**
```bash
nano .env
# Add: OPENAI_API_KEY=sk-your-actual-key
```

2. **Start the server:**
```bash
automagik agents start  # Start server
# Optional: Install alias for shorter commands
automagik install-alias  # Now you can use 'agent start'
```

3. **Test it:**
```bash
curl http://localhost:${AM_PORT}/health
```

## 🎯 Usage

### Commands
```bash
# Unified CLI Commands
automagik agents start      # Start service/container
automagik agents stop       # Stop service/container  
automagik agents restart    # Restart service/container
automagik agents status     # Show detailed service/container status
automagik agents logs       # Show live logs (with colors if available)
automagik agents dev        # Start in development mode with auto-reload
automagik agents --help     # Show all available commands

# Optional: Install shorter alias
automagik install-alias     # Install 'agent' alias
automagik uninstall-alias   # Remove 'agent' alias

# After installing alias, you can use:
agent start      # Same as 'automagik agents start'
agent stop       # Same as 'automagik agents stop'
agent status     # Same as 'automagik agents status'
# ... etc
```

### API Examples
```bash
# Test agent
curl -X POST http://localhost:${AM_PORT}/api/v1/agent/simple/run \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"message_content": "Hello!", "session_name": "test"}'

# Create memory that auto-injects into prompts
curl -X POST http://localhost:${AM_PORT}/api/v1/memories \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"name": "personality", "content": "friendly and helpful", "agent_id": 1}'
```

## Useful Endpoints

*   **API Docs:** `http://localhost:${AM_PORT}/docs`
*   **Health Check:** `http://localhost:${AM_PORT}/health`
*   **List Agents:** `http://localhost:${AM_PORT}/api/v1/agents`

## 🛠️ Create Custom Agents

```bash
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
