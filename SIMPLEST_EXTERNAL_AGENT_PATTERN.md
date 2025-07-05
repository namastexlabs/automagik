# The Simplest External Agent Pattern

## 🎯 The Absolute Minimum

External agents now require **ZERO boilerplate**. No factory functions, no `create_agent`, just your agent class.

### Directory Structure
```
my_agent/
├── __init__.py         # Can be empty or just imports
└── agent.py            # Your agent class
```

### Complete Agent Implementation

```python
# my_agent/agent.py
from automagik.agents.models.automagik_agent import AutomagikAgent

class MyAgent(AutomagikAgent):
    """My external agent - just the logic."""
    
    # Declarative configuration (used at API startup)
    DEFAULT_MODEL = "openai:gpt-4o-mini"
    DEFAULT_CONFIG = {
        "supported_media": ["text", "image"],
        "custom_setting": "value"
    }
    
    def __init__(self, config=None):
        super().__init__(config or {})
        self._code_prompt_text = "You are MyAgent..."
        self.dependencies = self.create_default_dependencies()
        self.tool_registry.register_default_tools(self.context)

# my_agent/__init__.py (OPTIONAL - can be completely empty!)
# Or just for convenience:
from .agent import MyAgent
```

That's it! No `create_agent` function needed.

## 🚀 How It Works

### 1. Discovery
The AgentFactory now automatically:
- Scans for directories in `AUTOMAGIK_EXTERNAL_AGENTS_DIR`
- Imports the module
- Looks for a class ending with "Agent" that inherits from `AutomagikAgent`
- Registers it directly

### 2. Database Registration (at API startup)
```python
# Reads DEFAULT_MODEL and DEFAULT_CONFIG from your agent class
# Registers in database:
{
  "name": "my_agent",
  "model": "openai:gpt-4o-mini",  # From DEFAULT_MODEL
  "config": {                      # From DEFAULT_CONFIG
    "supported_media": ["text", "image"],
    "custom_setting": "value"
  }
}
```

### 3. Agent Creation
```python
# AgentFactory creates instances directly:
agent = MyAgent(config)  # No factory function needed!
```

## 📝 Real Examples

### Simple External Agent
```python
# hello_agent/agent.py
from automagik.agents.models.automagik_agent import AutomagikAgent

class HelloAgent(AutomagikAgent):
    DEFAULT_MODEL = "openai:gpt-4o-mini"
    
    def __init__(self, config=None):
        super().__init__(config or {})
        self._code_prompt_text = "You are a friendly greeting agent."
        self.dependencies = self.create_default_dependencies()
        self.tool_registry.register_default_tools(self.context)

# hello_agent/__init__.py is EMPTY or doesn't exist!
```

### External Agent with Environment Variables
```python
# weather_agent/agent.py  
from automagik.agents.models.automagik_agent import AutomagikAgent

class WeatherAgent(AutomagikAgent):
    DEFAULT_MODEL = "openai:gpt-4o"
    PACKAGE_ENV_FILE = ".env"
    EXTERNAL_API_KEYS = [("WEATHER_API_KEY", "Weather service API key")]
    
    def __init__(self, config=None):
        super().__init__(config or {})
        self._code_prompt_text = "You are a weather information agent."
        self.dependencies = self.create_default_dependencies()
        self.tool_registry.register_default_tools(self.context)
        self._register_weather_tools()
    
    def _register_weather_tools(self):
        # Your custom tools
        pass
```

## 🔄 Migration Guide

### Before (with create_agent)
```python
# old_agent/__init__.py
from .agent import OldAgent

def create_agent(config=None):
    return OldAgent(config)
```

### After (no create_agent needed!)
```python
# old_agent/__init__.py
# This file can now be EMPTY or deleted!
# Or just have imports for convenience:
from .agent import OldAgent
```

## 🎉 Benefits

1. **Zero Boilerplate**: No factory functions needed
2. **Direct Discovery**: AgentFactory finds your class automatically
3. **Database Integration**: Still registers at API startup
4. **API Compatible**: Model updates work via API
5. **Simpler Testing**: Just import and instantiate your class

## 🔧 Advanced Patterns

### Multiple Agents in One Package
```python
# multi_agent/__init__.py
from .chat_agent import ChatAgent
from .code_agent import CodeAgent

# Both will be discovered if they end with "Agent"
```

### Custom Agent Discovery
```python
# custom_agent/__init__.py
# If your class doesn't end with "Agent", you can help discovery:
from .my_custom_bot import MyCustomBot as MyCustomAgent
```

## 📋 Summary

The new pattern eliminates ALL unnecessary code:
- ❌ No `create_agent` function
- ❌ No factory boilerplate  
- ❌ No required `__init__.py` content
- ✅ Just your agent class
- ✅ Automatic discovery
- ✅ Database integration unchanged
- ✅ API compatibility maintained

This is the simplest possible external agent pattern - just write your agent class and it works!