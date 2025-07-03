# PydanticAI Agent Enhancement Framework

This directory contains utilities and base classes that dramatically reduce verbosity in PydanticAI agent implementations while maintaining full functionality and extensibility.

## Overview

The enhancement framework reduces agent boilerplate code by 70-80% through:

- **Tool Wrapper Factory**: Eliminates repetitive tool wrapper creation
- **Agent Configuration Mixins**: Standard setup patterns
- **Multi-Prompt Manager**: Simplified status-based prompt management
- **Specialized Base Classes**: Pre-configured agent types
- **Decorator System**: Declarative agent configuration

## Quick Comparison

### Before (Original Stan Agent - 454 lines)
```python
class StanAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config, framework_type="pydantic_ai")
        self._prompts_registered = False
        self.dependencies = self.create_default_dependencies()
        if hasattr(self.dependencies, 'model_name'):
            self.dependencies.model_name = "openai:o1-mini"
        if self.db_id:
            self.dependencies.set_agent_id(self.db_id)
        self.tool_registry.register_default_tools(self.context)
        self._register_stan_tools()
        # ... 100+ more lines of setup
        
    def _register_stan_tools(self):
        async def verificar_cnpj_tool(ctx, cnpj: str) -> Dict[str, Any]:
            return await verificar_cnpj(self.context, cnpj)
        async def product_agent_tool(ctx, input_text: str) -> str:
            if hasattr(ctx, 'deps') and ctx.deps:
                ctx.deps.set_context(self.context)
            return await product_agent(ctx, input_text)
        # ... 50+ more lines of tool wrappers
        
    async def _register_all_prompts(self) -> None:
        # ... 150+ lines of prompt registration logic
```

### After (Enhanced Stan Agent - 201 lines, 55% reduction)
```python
class StanAgentEnhanced(BlackPearlAgent):
    default_model = "openai:o1-mini"
    
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)  # Handles all standard setup
        self._register_stan_tools()
        
    def _register_stan_tools(self) -> None:
        stan_tools = {
            'verificar_cnpj': verificar_cnpj,
            'product_agent': product_agent,
            'backoffice_agent': backoffice_agent,
            'order_agent': order_agent
        }
        
        for tool_name, tool_func in stan_tools.items():
            wrapper = ToolWrapperFactory.create_context_wrapper(tool_func, self.context)
            self.tool_registry.register_tool(wrapper)
```

## Components

### 1. Tool Wrapper Factory (`tool_wrapper_factory.py`)

Eliminates repetitive tool wrapper creation patterns:

```python
# Before: Manual wrapper creation (repeated across agents)
async def my_tool_wrapper(ctx, param: str) -> Dict[str, Any]:
    return await my_tool_function(self.context, param)

# After: Factory-generated wrapper
wrapper = ToolWrapperFactory.create_context_wrapper(my_tool_function, self.context)
```

**Key Methods:**
- `create_context_wrapper()`: Standard context injection
- `create_agent_tool_wrapper()`: For sub-agent calls
- `create_batch_wrappers()`: Multiple tools at once
- `create_api_tool_wrapper()`: API integration with error handling

### 2. Agent Configuration (`agent_configuration.py`)

Provides mixins and templates for standard agent setup:

```python
# Configuration templates
config = AgentConfigTemplates.get_template("blackpearl")
# Returns: {"model": "openai:o1-mini", "tools": ["default", "blackpearl"], ...}

# Mixin usage
class MyAgent(AutomagikAgent, AgentConfigurationMixin):
    def __init__(self, config, prompt):
        self.setup_standard_pydantic_agent(config, prompt)
```

### 3. Multi-Prompt Manager (`multi_prompt_manager.py`)

Simplifies status-based prompt management for agents like Stan:

```python
# Before: 150+ lines of prompt registration logic
async def _register_all_prompts(self): 
    # Complex file discovery and registration...

# After: Automatic discovery and registration
self.prompt_manager = MultiPromptManager(self, prompts_dir, package_name)
await self.prompt_manager.register_all_prompts()
await self.prompt_manager.load_prompt_by_status("APPROVED")
```

### 4. Unified Agent Architecture

All agents now inherit directly from `AutomagikAgent` with feature flags:

```python
# Standard agent with multimodal support (default)
class MyAgent(AutomagikAgent):
    def __init__(self, config):
        super().__init__(config)
        self._code_prompt_text = AGENT_PROMPT
        self.dependencies = self.create_default_dependencies()
        self.tool_registry.register_default_tools(self.context)

# Multi-prompt agent (like Stan)
class MyMultiPromptAgent(AutomagikAgent):
    def __init__(self, config):
        if config is None:
            config = {}
        config.setdefault("enable_multi_prompt", True)
        super().__init__(config)
        self._code_prompt_text = AGENT_PROMPT
        # Auto-discovers prompts when enable_multi_prompt=True
```

### 5. Decorator System (`agent_decorators.py`)

Declarative agent configuration (experimental):

```python
@pydantic_ai_agent(
    model="openai:o1-mini",
    tools=['default', 'blackpearl'],
    prompts='auto_discover',
    specialized=['product_agent', 'backoffice_agent']
)
class MyAgent(AutomagikAgent):
    pass  # All configuration handled by decorator
```

## Usage Examples

### Simple Agent Enhancement

```python
# Before (with specialized inheritance)
class SimpleAgent(MultimodalAgent):
    def __init__(self, config: dict[str, str]) -> None:
        super().__init__(config)
        # Complex multimodal setup...

# After (unified architecture)
class SimpleAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)  # Multimodal enabled by default
        self._code_prompt_text = AGENT_PROMPT
        self.dependencies = self.create_default_dependencies()
        self.tool_registry.register_default_tools(self.context)
```

### Complex Agent Enhancement

For agents with specialized business logic (like Stan), the framework handles:

- ✅ **Boilerplate elimination**: Standard initialization patterns
- ✅ **Tool registration**: Automatic wrapper creation
- ✅ **Multi-prompt management**: Status-based prompt loading
- ✅ **Business logic preservation**: All domain-specific logic maintained
- ✅ **Channel integration**: WhatsApp/Evolution payload processing
- ✅ **Memory management**: User information storage

## Migration Guide

### Step 1: Identify Required Features
- **Basic functionality**: Use `AutomagikAgent` (multimodal enabled by default)
- **Multi-prompt support**: Set `enable_multi_prompt=True` in config
- **WhatsApp/Evolution**: Built-in via channel handlers
- **BlackPearl integration**: Copy helper methods locally (see StanAgent example)

### Step 2: Configure Features
- Set `enable_multi_prompt=True` if status-based prompts needed
- Configure multimodal settings if custom vision model required
- Use `ToolWrapperFactory` for wrapper creation
- Set `self._code_prompt_text = AGENT_PROMPT` for agent prompt

### Step 3: Preserve Business Logic
- Keep domain-specific methods (like BlackPearl contact management)
- Maintain existing API contracts
- Preserve error handling and edge cases

### Step 4: Test Compatibility
- Run existing tests to ensure no regressions
- Verify multimodal functionality works
- Check tool registration and memory integration
- Test multi-prompt loading if enabled

## Performance Impact

The enhancement framework provides:

- **Development Speed**: 70-80% less code to write
- **Maintenance**: Centralized patterns reduce bugs
- **Consistency**: Standard patterns across all agents
- **Extensibility**: Easy to add new agent types
- **Runtime Performance**: Minimal overhead (wrapper creation is O(1))

## Best Practices

1. **Always extend AutomagikAgent**: Single base class with feature flags
2. **Configure features appropriately**: Enable multi-prompt, configure multimodal as needed
3. **Preserve business logic**: Don't eliminate domain-specific functionality
4. **Use factory methods**: Leverage `ToolWrapperFactory` for consistency
5. **Test thoroughly**: Agents should pass all existing tests
6. **Document customizations**: Note any deviations from standard patterns

## Architecture Benefits

The enhancement framework follows these principles:

- **DRY (Don't Repeat Yourself)**: Eliminates code duplication
- **Single Responsibility**: Each utility has a focused purpose
- **Open/Closed**: Easy to extend without modifying existing code
- **Composition over Inheritance**: Mix and match capabilities
- **Backward Compatibility**: Enhanced agents work with existing infrastructure

## Future Enhancements

Planned improvements:

- **Auto-discovery decorators**: Fully declarative agent configuration
- **Performance profiling**: Built-in performance monitoring
- **Test generation**: Automatic test scaffolding for enhanced agents
- **IDE integration**: Better development tooling support
- **Documentation generation**: Auto-generated agent documentation