# Declarative Agent Registry

The declarative agent registry eliminates the need for scattered `create_agent` functions across individual agents by centralizing all agent configurations in one place.

## 🎯 Benefits

1. **No More Scattered Functions**: All agent configurations in `agents_manifest.py`
2. **Centralized Model Management**: Change models without touching agent code
3. **Framework Declaration**: Explicitly declare which framework each agent uses
4. **Configuration Defaults**: Set default configs for each agent type
5. **Easy Enable/Disable**: Toggle agents without code changes
6. **Better Validation**: Compile-time checking of agent availability

## 📝 Migration Guide

### Before (Scattered Pattern)
Every agent needed its own `create_agent` function:

```python
# flashinho/__init__.py
def create_agent(config: Dict[str, str]):
    try:
        from .agent import FlashinhoAgent
        return FlashinhoAgent(config)
    except Exception as e:
        return PlaceholderAgent(config)

# simple/__init__.py  
def create_agent(config: Dict[str, str]):
    try:
        from .agent import SimpleAgent
        return SimpleAgent(config)
    except Exception as e:
        return PlaceholderAgent(config)

# ... repeated for EVERY agent
```

### After (Declarative Pattern)
All agents declared in one place:

```python
# agents_manifest.py
AgentRegistry.register(
    name="flashinho",
    agent_class=FlashinhoAgent,
    framework=Framework.PYDANTIC_AI,
    default_model="openai:gpt-4o-mini",
    description="WhatsApp automation agent",
    supported_media=["text", "image", "audio"],
    default_config={
        "whatsapp_integration": True,
        "language": "pt-BR"
    }
)

AgentRegistry.register(
    name="simple", 
    agent_class=SimpleAgent,
    framework=Framework.PYDANTIC_AI,
    default_model="openai:gpt-4o-mini",
    description="General purpose agent",
    supported_media=["text", "image", "audio", "document"]
)
```

## 🚀 Usage

### Creating Agents
```python
# AgentFactory automatically uses the registry
agent = AgentFactory.create_agent("flashinho")

# Or use registry directly
agent = AgentRegistry.create_agent("flashinho")
```

### Listing Agents
```python
# List all enabled agents
agents = AgentRegistry.list_agents()

# List by framework
agents_by_fw = AgentRegistry.list_by_framework()
# {"pydanticai": ["simple", "flashinho", "sofia"], "claude_code": ["claude_code"]}
```

### Updating Models
```python
# Change model for specific agent
AgentRegistry.update_agent_model("flashinho", "openai:gpt-4o")

# Change model for specific framework
AgentRegistry.update_agent_model("flashinho", "anthropic:claude-3-5-sonnet", framework="pydanticai")
```

### Enable/Disable Agents
```python
# Disable an agent
AgentRegistry.enable_agent("experimental_agent", enabled=False)

# Re-enable
AgentRegistry.enable_agent("experimental_agent", enabled=True)
```

## 📁 Adding New Agents

### 1. Create Agent Class (as before)
```python
# my_agent/agent.py
class MyAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str] = None):
        super().__init__(config or {})
        self._code_prompt_text = "You are MyAgent..."
        # ... rest of implementation
```

### 2. Register in Manifest (NEW!)
```python
# agents_manifest.py
AgentRegistry.register(
    name="my_agent",
    agent_class=MyAgent,
    framework=Framework.PYDANTIC_AI,
    default_model="openai:gpt-4o-mini",
    description="My custom agent",
    supported_media=["text"],
    default_config={
        "custom_setting": "value"
    }
)
```

### 3. NO create_agent Function Needed! 🎉

## 🔧 Advanced Features

### Model Fallbacks
```python
AgentRegistry.register(
    name="critical_agent",
    agent_class=CriticalAgent,
    framework=Framework.PYDANTIC_AI,
    default_model="openai:gpt-4o",
    fallback_models=[
        "openai:gpt-4o-mini",
        "anthropic:claude-3-5-sonnet",
        "gemini:gemini-pro"
    ]
)
```

### Framework Preferences
```python
AgentRegistry.register(
    name="multi_framework_agent",
    agent_class=MultiAgent,
    framework=Framework.AUTO,
    default_model="openai:gpt-4o-mini",
    framework_preferences={
        "pydanticai": "openai:gpt-4o-mini",
        "agno": "anthropic:claude-3-5-sonnet",
        "claude_code": "anthropic:claude-3-5-sonnet"
    }
)
```

### External API Keys
```python
AgentRegistry.register(
    name="api_agent",
    agent_class=ApiAgent,
    framework=Framework.PYDANTIC_AI,
    default_model="openai:gpt-4o-mini",
    external_api_keys=[
        ("SERVICE_API_KEY", "Service API access"),
        ("OTHER_API_KEY", "Other service access")
    ]
)
```

## 🎯 Summary

The declarative registry approach:
- ✅ Eliminates scattered `create_agent` functions
- ✅ Centralizes all agent configuration
- ✅ Makes model changes trivial
- ✅ Provides better discoverability
- ✅ Enables runtime configuration changes
- ✅ Maintains backward compatibility

This is exactly what was requested: "some sort of a more declarative place only to set model name and configs instead of having in the agent class + the create_agent function scattered across our agents".