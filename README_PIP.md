# Automagik - Pip Installation Guide

## Quick Start

### Install from PyPI (when published)
```bash
pip install automagik
```

### Install from source
```bash
git clone https://github.com/namastexlabs/automagik-agents
cd automagik-agents/am-agents-labs
pip install -e .
```

## Usage

### Starting the API Server

After installation, you can start the API server in several ways:

#### Method 1: Using the command line tool
```bash
# Start with default settings (reads from .env if present)
automagik-server

# Start with custom host and port
automagik-server --host 0.0.0.0 --port 8000

# Specify external agents directory
automagik-server --agents-dir /path/to/my/agents
```

#### Method 2: Using environment variables
```bash
# Set environment variables
export AUTOMAGIK_API_HOST=0.0.0.0
export AUTOMAGIK_API_PORT=8000
export AUTOMAGIK_EXTERNAL_AGENTS_DIR=~/.automagik/agents

# Start the server
automagik-server
```

#### Method 3: Using Python module
```python
from automagik.cli.commands.server import start_server_from_pip

# Start with default settings
start_server_from_pip()

# Or with custom settings
start_server_from_pip(host="0.0.0.0", port=8000, agents_dir="/path/to/agents")
```

### Using the CLI

The `automagik` command provides access to all CLI features:

```bash
# List available agents
automagik agents list

# Run an agent
automagik agents run -a simple -m "Hello, how are you?"

# Start interactive chat
automagik agents chat -a flashinho

# Create a new agent from template
automagik agents create -n my_agent -t simple
```

## Custom Agents

### Agent Directory Structure

By default, external agents are loaded from `~/.automagik/agents/`. Each agent should be in its own directory with either an `agent.py` or `__init__.py` file:

```
~/.automagik/agents/
├── my_custom_agent/
│   ├── agent.py          # Agent implementation
│   └── README.md         # Optional documentation
├── another_agent/
│   ├── __init__.py       # Alternative structure
│   └── prompts/
│       └── system.md
```

### Creating a Custom Agent

1. Copy the example template:
```bash
cp -r $(pip show automagik | grep Location | cut -d' ' -f2)/automagik/agents/templates/example_agent ~/.automagik/agents/my_agent
```

2. Edit the agent implementation:
```python
# ~/.automagik/agents/my_agent/agent.py
from automagik import AutomagikAgent
from automagik.agents.models.dependencies import AutomagikAgentsDependencies

AGENT_PROMPT = """You are a helpful assistant specialized in..."""

def create_agent(config=None):
    return MyAgent(config or {})

class MyAgent(AutomagikAgent):
    def __init__(self, config):
        super().__init__(config)
        self._code_prompt_text = AGENT_PROMPT
        self.dependencies = AutomagikAgentsDependencies(
            model_name="openai:gpt-4o-mini",
            model_settings={},
            api_keys={},
            tool_config={}
        )
        self.tool_registry.register_default_tools(self.context)
```

3. Test your agent:
```bash
# Restart the server to load new agents
automagik-server

# List agents (your agent should appear)
automagik agents list

# Test your agent
automagik agents run -a my_agent -m "Test message"
```

## Environment Configuration

Create a `.env` file in your working directory:

```env
# API Configuration
AUTOMAGIK_API_HOST=0.0.0.0
AUTOMAGIK_API_PORT=8000
AUTOMAGIK_API_KEY=your-api-key

# External Agents Directory
AUTOMAGIK_EXTERNAL_AGENTS_DIR=/path/to/agents

# LLM Providers
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=...

# Database
AUTOMAGIK_DATABASE_URL=sqlite:///automagik.db
```

## API Usage

Once the server is running, you can interact with agents via the REST API:

```bash
# List agents
curl http://localhost:8000/api/v1/agents \
  -H "X-API-Key: your-api-key"

# Invoke an agent
curl -X POST http://localhost:8000/api/v1/agents/simple/invoke \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"message": "Hello!"}'

# Chat with an agent (streaming)
curl -X POST http://localhost:8000/api/v1/agents/flashinho/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"message": "Tell me a joke", "stream": true}'
```

## Advanced Configuration

### Using Different Package Indexes

To install from a private package index:
```bash
pip install automagik --index-url https://your-private-pypi.com/simple/
```

### Docker Integration

You can also run Automagik in a Docker container with pip-installed package:

```dockerfile
FROM python:3.12-slim
RUN pip install automagik
ENV AUTOMAGIK_EXTERNAL_AGENTS_DIR=/agents
CMD ["automagik-server", "--host", "0.0.0.0"]
```

## Troubleshooting

### Common Issues

1. **Module not found errors**
   - Ensure you've activated your virtual environment
   - Try reinstalling: `pip install -e . --force-reinstall`

2. **Agents not loading**
   - Check `AUTOMAGIK_EXTERNAL_AGENTS_DIR` is set correctly
   - Ensure agent files have proper structure
   - Check server logs for loading errors

3. **API connection refused**
   - Verify the server is running: `ps aux | grep automagik-server`
   - Check firewall settings
   - Ensure correct host/port configuration

### Debug Mode

Enable debug logging:
```bash
export AUTOMAGIK_LOG_LEVEL=DEBUG
automagik-server
```

## Contributing

See the main repository README for contribution guidelines.