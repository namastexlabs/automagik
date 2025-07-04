# External Agents Examples

This directory contains examples of external agents using the minimal pattern introduced in the Automagik platform.

## 🚀 Minimal Agent Pattern

Each agent only needs:
1. `agent.py` - The agent class with declarative configuration
2. `prompt.md` - The agent's prompt in markdown format
3. `.env.example` - Example environment variables (optional)

## 📁 Structure

```
agent_name/
├── agent.py      # Agent class (30-40 lines)
└── prompt.md     # Agent prompt (markdown)
```

## 🎯 Key Features

- **No boilerplate**: No `create_agent` functions needed
- **Declarative config**: Use class attributes for configuration
- **Markdown prompts**: Prompts are in `.md` files, not Python
- **Automatic discovery**: Agents are found and registered automatically
- **Centralized tools**: Tools are shared across all agents

## 📝 Creating a New External Agent

```python
# agent.py
from typing import Dict
from automagik.agents.models.automagik_agent import AutomagikAgent

class MyAgent(AutomagikAgent):
    """My custom agent."""
    
    # Declarative configuration
    DEFAULT_MODEL = "openai:gpt-4o-mini"
    DEFAULT_CONFIG = {
        "language": "en",
        "custom_setting": "value"
    }
    
    # External agent settings
    PACKAGE_ENV_FILE = ".env"
    EXTERNAL_API_KEYS = [
        ("MY_API_KEY", "Description of the key"),
    ]
    
    # Prompt file
    PROMPT_FILE = "prompt.md"
    
    def __init__(self, config: Dict[str, str] = None) -> None:
        """Initialize the agent."""
        super().__init__(config or {})
        
        # Create dependencies
        self.dependencies = self.create_default_dependencies()
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        
        # Register tools
        self.tool_registry.register_default_tools(self.context)
```

## 🔧 Running External Agents

1. Set the external agents directory:
   ```bash
   export AUTOMAGIK_EXTERNAL_AGENTS_DIR=/path/to/agents_examples
   ```

2. Start the API:
   ```bash
   automagik api start --external-dir ./agents_examples
   ```

3. Use your agent:
   ```bash
   automagik agents chat -a my_agent
   ```

## 📦 Example Agents

- **flashinho_old_make**: Basic educational assistant (pt-BR)
- **flashinho_pro**: Advanced educational assistant with Pro/Free tiers
- **flashinho_pro_external**: External API integration example
- **flashinho_the_first**: The original simple version

Each demonstrates the minimal pattern while showcasing different features.