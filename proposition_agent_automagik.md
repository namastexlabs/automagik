# Proposition: Enhance AutomagikAgent for External Agent Support

## Executive Summary

This proposition outlines enhancements to the `AutomagikAgent` base class to natively support external agent development patterns, with special focus on **seamless PydanticAI integration** for users migrating from or using PydanticAI agents.

## Problem Statement

Currently, creating external agents requires:
- ~100+ lines of boilerplate code per agent
- Manual API key registration
- Manual tool registration
- Duplicated dependency setup logic
- Complex import path management
- No standard patterns for common tasks

**New Finding**: PydanticAI users face additional friction:
- PydanticAI agents are 5-10 lines vs our 40+ lines
- Different conceptual models (simple function vs class inheritance)
- Tool registration patterns don't match (`@agent.tool` vs `register_tool`)
- No direct path to use existing PydanticAI agents

## Proposed Solution

Three-pronged approach to simplify external agent integration:

1. **PydanticAI Direct Wrapper** - Zero-friction integration for existing PydanticAI agents
2. **Simplified Base Classes** - Match PydanticAI's simplicity for new agents  
3. **Enhanced AutomagikAgent** - Declarative configuration to reduce boilerplate

## Implementation Details

### Phase 1: PydanticAI Direct Wrapper (PRIORITY 1)

Enable existing PydanticAI agents to work with zero code changes:

```python
# New file: automagik/agents/adapters/pydantic_wrapper.py
from pydantic_ai import Agent as PydanticAgent
from automagik.agents.models.automagik_agent import AutomagikAgent

class PydanticAIWrapper(AutomagikAgent):
    """Zero-friction wrapper for existing PydanticAI agents."""
    
    def __init__(self, pydantic_agent: PydanticAgent, name: Optional[str] = None):
        config = {"name": name or "wrapped_agent", "framework_type": "pydanticai"}
        super().__init__(config)
        
        self.pydantic_agent = pydantic_agent
        self._code_prompt_text = self._extract_system_prompt()
        self._register_pydantic_tools()
    
    async def run_agent(self, user_input: Any, **kwargs):
        deps = kwargs.get('dependencies', None)
        result = await self.pydantic_agent.run(user_input, deps=deps)
        return result.data if hasattr(result, 'data') else str(result)

def wrap_pydantic_agent(agent: PydanticAgent, name: Optional[str] = None):
    """One-line integration for PydanticAI agents."""
    return PydanticAIWrapper(agent, name)
```

**Usage - User's code stays unchanged:**
```python
# User's existing PydanticAI code
from pydantic_ai import Agent
my_agent = Agent('openai:gpt-4o', system_prompt='Be helpful')

@my_agent.tool
def calculate(x: int, y: int) -> int:
    return x + y

# ONE LINE to make it API-ready!
from automagik import wrap_pydantic_agent
api_agent = wrap_pydantic_agent(my_agent, name="calculator")
```

### Phase 2: Simplified External Agent Base

Create a new simplified base class that matches PydanticAI's ease of use:

```python
# New file: automagik/agents/external/simple_base.py
class SimpleExternalAgent(AutomagikAgent):
    """Minimal base class matching PydanticAI simplicity."""
    
    def __init__(
        self,
        model: str = "openai:gpt-4o",
        system_prompt: str = "You are a helpful assistant",
        tools: Optional[List[Callable]] = None,
        name: Optional[str] = None,
        **kwargs
    ):
        config = {"model": model, "name": name or self.__class__.__name__, **kwargs}
        super().__init__(config)
        
        # Direct assignment - no abstract methods!
        self._code_prompt_text = system_prompt
        self.dependencies = self.create_default_dependencies()
        
        # Register tools directly
        for tool in (tools or []):
            self.tool_registry.register_tool(tool)
        
        self.tool_registry.register_default_tools(self.context)

# Factory function for even simpler usage
def create_simple_agent(model="openai:gpt-4o", prompt="", tools=None):
    return SimpleExternalAgent(model, prompt, tools)
```

**Usage - As simple as PydanticAI:**
```python
from automagik import create_simple_agent

def get_weather(city: str) -> str:
    return f"Weather in {city}: Sunny"

# 3 lines to create an agent!
agent = create_simple_agent(
    prompt="You are a weather assistant",
    tools=[get_weather]
)
```

### Comparison: PydanticAI vs Current vs Proposed

| Aspect | PydanticAI Native | Current Automagik | Proposed Solution |
|--------|-------------------|-------------------|-------------------|
| **Lines of Code** | 5-10 | 100+ | 1 (wrapper) or 3-5 (new) |
| **Concept** | Simple function | Class inheritance | Both supported |
| **Tool Registration** | `@agent.tool` | `register_tool()` | Both patterns |
| **Dependencies** | Direct in `run()` | Complex object | Auto-configured |
| **API Ready** | No | Yes | Yes |
| **Session Management** | No | Yes | Yes |
| **Database Storage** | No | Yes | Yes |
| **Production Features** | No | Yes | Yes |

### Phase 3: Enhanced AutomagikAgent (Original Proposal)

Add class-level attributes to `AutomagikAgent` for declarative configuration:

```python
class AutomagikAgent:
    # Optional external configuration
    EXTERNAL_API_KEYS: List[Tuple[str, str]] = []
    EXTERNAL_URLS: List[Tuple[str, str]] = []
    
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        
        # Auto-register external keys if defined
        if self.EXTERNAL_API_KEYS or self.EXTERNAL_URLS:
            self._register_external_config()
    
    def _register_external_config(self) -> None:
        """Auto-register external API keys and URLs."""
        settings = get_settings()
        
        for key_name, description in self.EXTERNAL_API_KEYS:
            value = os.environ.get(key_name)
            if value:
                settings.add_external_api_key(key_name, value, description)
                logger.debug(f"Registered external API key: {key_name}")
        
        for url_name, description in self.EXTERNAL_URLS:
            value = os.environ.get(url_name)
            if value:
                settings.add_external_url(url_name, value, description)
                logger.debug(f"Registered external URL: {url_name}")
```

### 2. Automatic Tool Registration

Add support for declarative tool registration:

```python
class AutomagikAgent:
    # Optional tool configuration
    AUTO_REGISTER_TOOLS: List[Callable] = []
    
    def __init__(self, config: Dict[str, str]) -> None:
        # ... existing init ...
        
        # Auto-register tools if defined
        if self.AUTO_REGISTER_TOOLS:
            for tool in self.AUTO_REGISTER_TOOLS:
                self.tool_registry.register_tool(tool)
                logger.debug(f"Auto-registered tool: {tool.__name__}")
```

### 3. Enhanced Dependency Management

Add smart dependency creation with model detection:

```python
class AutomagikAgent:
    # Optional model configuration
    DEFAULT_MODEL: Optional[str] = None
    MODEL_SETTINGS: Dict[str, Any] = {"temperature": 0.7, "max_tokens": 4096}
    
    def create_default_dependencies(self) -> AutomagikAgentsDependencies:
        """Create dependencies with sensible defaults based on model."""
        if not self.DEFAULT_MODEL:
            return super().create_default_dependencies()
        
        # Auto-detect API key based on model provider
        provider = self.DEFAULT_MODEL.split(":")[0]
        api_key_mapping = {
            "openai": {"openai_api_key": os.environ.get("OPENAI_API_KEY", "")},
            "google": {"google_api_key": os.environ.get("GEMINI_API_KEY", "")},
            "anthropic": {"anthropic_api_key": os.environ.get("ANTHROPIC_API_KEY", "")},
            "groq": {"groq_api_key": os.environ.get("GROQ_API_KEY", "")},
        }
        
        api_keys = api_key_mapping.get(provider, {})
        
        dependencies = AutomagikAgentsDependencies(
            model_name=self.DEFAULT_MODEL,
            model_settings=self.MODEL_SETTINGS,
            api_keys=api_keys,
            tool_config={}
        )
        
        if self.db_id:
            dependencies.set_agent_id(self.db_id)
            
        return dependencies
```

### 4. Lifecycle Hooks

Add extensibility points for custom initialization:

```python
class AutomagikAgent:
    def __init__(self, config: Dict[str, str]) -> None:
        # ... existing init ...
        
        # Setup dependencies if DEFAULT_MODEL is set
        if self.DEFAULT_MODEL and not hasattr(self, 'dependencies'):
            self.dependencies = self.create_default_dependencies()
            self.tool_registry.register_default_tools(self.context)
        
        # Call post-init hook
        self._post_init()
    
    def _post_init(self) -> None:
        """Override this method for custom initialization logic.
        
        This is called after all standard initialization is complete.
        Use this to:
        - Set custom prompts
        - Register additional tools
        - Initialize agent-specific components
        """
        pass
```

### 5. Utility Methods

Add helpful utilities for external agent development:

```python
class AutomagikAgent:
    def register_tools_from_module(self, module) -> int:
        """Register all async functions from a module as tools.
        
        Args:
            module: Python module containing tool functions
            
        Returns:
            Number of tools registered
        """
        import inspect
        registered = 0
        
        for name, obj in inspect.getmembers(module):
            if (inspect.iscoroutinefunction(obj) and 
                not name.startswith('_') and
                hasattr(obj, '__module__') and 
                obj.__module__ == module.__name__):
                self.tool_registry.register_tool(obj)
                registered += 1
        
        logger.debug(f"Auto-registered {registered} tools from {module.__name__}")
        return registered
    
    @property
    def agent_directory(self) -> Optional[Path]:
        """Get the directory containing this agent."""
        import inspect
        from pathlib import Path
        
        try:
            file = inspect.getfile(self.__class__)
            return Path(file).parent
        except:
            return None
    
    def add_parent_to_path(self) -> None:
        """Add parent directory to Python path for imports.
        
        Useful for external agents that need to import from
        sibling directories (e.g., shared tools).
        """
        if self.agent_directory:
            import sys
            parent = str(self.agent_directory.parent)
            if parent not in sys.path:
                sys.path.insert(0, parent)
```

## Usage Examples

### Before (Current Approach) - 94 lines
```python
class FlashinhoAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        config = config or {}
        config.setdefault("supported_media", ["image", "audio", "document"])
        
        super().__init__(config)
        
        self._code_prompt_text = AGENT_PROMPT
        
        # Register external API keys
        from automagik.config import get_settings
        settings = get_settings()
        settings.add_external_api_key("FLASHED_API_KEY", os.environ.get("FLASHED_API_KEY"))
        settings.add_external_url("FLASHED_API_URL", os.environ.get("FLASHED_API_URL"))
        
        # Setup dependencies
        self.dependencies = AutomagikAgentsDependencies(
            model_name="openai:gpt-4o-mini",
            model_settings={"temperature": 0.7, "max_tokens": 2048},
            api_keys={"openai_api_key": os.environ.get("OPENAI_API_KEY", "")},
            tool_config={}
        )
        
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
            
        self.tool_registry.register_default_tools(self.context)
        
        # Register tools
        self.tool_registry.register_tool(get_user_data)
        self.tool_registry.register_tool(get_user_score)
        # ... more tools
```

### After (Proposed Approach) - 15 lines
```python
class FlashinhoAgent(AutomagikAgent):
    # Declarative configuration
    DEFAULT_MODEL = "openai:gpt-4o-mini"
    MODEL_SETTINGS = {"temperature": 0.7, "max_tokens": 2048}
    EXTERNAL_API_KEYS = [
        ("FLASHED_API_KEY", "Flashed API authentication key"),
    ]
    EXTERNAL_URLS = [
        ("FLASHED_API_URL", "Flashed API base URL"),
    ]
    AUTO_REGISTER_TOOLS = [get_user_data, get_user_score]
    
    def _post_init(self) -> None:
        self._code_prompt_text = AGENT_PROMPT
```

## Benefits

1. **Zero-Friction PydanticAI Migration**: One line to make existing agents API-ready
2. **95% Less Boilerplate**: From ~100 lines to 3-5 lines for new agents
3. **Backward Compatible**: All existing agents continue to work unchanged
4. **Multiple Integration Paths**: Choose complexity level that fits your needs
5. **Familiar Patterns**: Matches PydanticAI's simple, functional approach
6. **Gradual Adoption**: Start simple, add advanced features as needed
7. **Market Advantage**: "Turn any PydanticAI agent into a production API"

## Implementation Timeline

### Priority 1: PydanticAI Integration (Release Blocker)
1. **Day 1-2**: PydanticAI wrapper implementation and testing
2. **Day 3**: SimpleExternalAgent base class
3. **Day 4**: Integration guides and examples
4. **Day 5**: Testing with real PydanticAI agents

### Priority 2: Enhanced AutomagikAgent
5. **Day 6**: Declarative configuration support
6. **Day 7**: Automatic tool and dependency management  
7. **Day 8**: Documentation and migration tools

**Total: 8 days (5 for Priority 1, 3 for Priority 2)**

## Success Metrics

- **PydanticAI Integration**: 1-line integration for existing agents
- **New Agent Creation**: 3-5 lines vs current 100+ lines  
- **Migration Rate**: 50%+ of PydanticAI users can adopt without code changes
- **Time to Production**: From hours to minutes for external agents
- **Zero Breaking Changes**: All existing agents continue working

## Migration Paths

### For PydanticAI Users
```python
# Path 1: Zero code changes
api_agent = wrap_pydantic_agent(existing_agent)

# Path 2: Minimal refactor (5 lines)
agent = create_simple_agent("openai:gpt-4o", "Your prompt", [tools])

# Path 3: Full integration (gradual adoption)
class MyAgent(SimpleExternalAgent):
    # Add Automagik features as needed
```

### For Current External Agent Users
```python
# Before: 100+ lines with BaseExternalAgent
# After: 15 lines with enhanced AutomagikAgent
class MyAgent(AutomagikAgent):
    DEFAULT_MODEL = "openai:gpt-4o"
    AUTO_REGISTER_TOOLS = [tool1, tool2]
    
    def _post_init(self):
        self._code_prompt_text = "Your prompt"
```

## Risks and Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing agents | High | Extensive testing, maintain all current APIs |
| PydanticAI API changes | Medium | Version pinning, adapter pattern isolation |
| Adoption friction | Medium | Multiple integration paths, clear examples |
| Performance overhead | Low | Minimal wrapper, lazy initialization |

## Recommendation

**Immediate Action**: Implement Priority 1 (PydanticAI integration) before release. This provides:
- Instant value for PydanticAI users
- Competitive advantage in the AI agent market
- Low-risk, high-reward enhancement
- Clear migration path for the largest agent framework community

The simplified approach will dramatically reduce friction for new users while maintaining the power and flexibility of the Automagik platform.