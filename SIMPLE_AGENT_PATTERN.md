# Simple Agent Pattern - Database-Aware Approach

## The Real Problem

- Agents are registered in the database on first run
- Database stores: name, type, model, config, active status
- External agents should be simple - just logic, no boilerplate
- Need API compatibility for all agents

## The Simple Solution

### 1. Model as Class Attribute (Not Scattered)

Instead of scattered `create_agent` functions defining models, put it on the agent class:

```python
class MyAgent(AutomagikAgent):
    """My agent implementation."""
    
    # Declarative model configuration
    DEFAULT_MODEL = "openai:gpt-4o-mini"
    FALLBACK_MODELS = ["openai:gpt-4o", "anthropic:claude-3-5-sonnet"]
    
    # Configuration that gets stored in database
    DEFAULT_CONFIG = {
        "supported_media": ["text", "image"],
        "language": "en",
        "custom_setting": "value"
    }
    
    def __init__(self, config: Dict[str, str] = None):
        # Merge with database config if exists
        config = {**self.DEFAULT_CONFIG, **(config or {})}
        super().__init__(config)
        
        self._code_prompt_text = AGENT_PROMPT
        # ... rest of implementation
```

### 2. Factory Reads from Database First

The factory checks database first, then falls back to class defaults:

```python
# In AgentFactory.create_agent():
def create_agent(agent_type: str, config: Dict = None):
    # 1. Check database for agent config
    db_agent = get_agent_by_name(agent_type)
    if db_agent:
        # Use database config, model, etc.
        config = {**db_agent.config, **(config or {})}
        model = db_agent.model
    else:
        # 2. Fall back to class defaults
        agent_class = _get_agent_class(agent_type)
        config = {**agent_class.DEFAULT_CONFIG, **(config or {})}
        model = agent_class.DEFAULT_MODEL
    
    # 3. Create agent with merged config
    agent = agent_class(config)
    
    # 4. Register in database if new
    if not db_agent:
        register_agent(
            name=agent_type,
            type=agent_type,
            model=model,
            config=config
        )
    
    return agent
```

### 3. External Agents Stay Simple

```python
# my_external_agent/agent.py
class MyExternalAgent(AutomagikAgent):
    """External agent - just the logic."""
    
    DEFAULT_MODEL = "openai:gpt-4o-mini"
    PACKAGE_ENV_FILE = ".env"
    EXTERNAL_API_KEYS = [("MY_API_KEY", "My API key")]
    
    def __init__(self, config=None):
        super().__init__(config or {})
        self._code_prompt_text = "You are MyAgent..."
        self.dependencies = self.create_default_dependencies()
        self.tool_registry.register_default_tools(self.context)

# my_external_agent/__init__.py
from .agent import MyExternalAgent

def create_agent(config=None):
    return MyExternalAgent(config)
```

### 4. API Updates Model in Database

When users want to change models via API:

```python
# API endpoint
@router.put("/agents/{agent_name}/model")
async def update_agent_model(agent_name: str, model: str):
    # Update in database
    db_agent = get_agent_by_name(agent_name)
    if db_agent:
        db_agent.model = model
        update_agent(db_agent)
    
    # Future instances will use new model
    return {"status": "updated", "model": model}
```

## Benefits

1. ✅ **Database is source of truth** - Config stored and retrieved from DB
2. ✅ **No scattered functions** - Model defined as class attribute
3. ✅ **External agents stay simple** - Just inherit and set attributes
4. ✅ **API compatible** - Can update models via API, stored in DB
5. ✅ **Backward compatible** - Existing `create_agent` functions still work

## Migration Path

### Phase 1: Add Class Attributes (Non-Breaking)
```python
class SimpleAgent(AutomagikAgent):
    DEFAULT_MODEL = "openai:gpt-4o-mini"  # NEW
    # ... existing code unchanged
```

### Phase 2: Update Factory to Check Attributes
```python
# In factory, check for DEFAULT_MODEL attribute
if hasattr(agent_class, 'DEFAULT_MODEL'):
    model = agent_class.DEFAULT_MODEL
```

### Phase 3: Sync with Database
```python
# On first run, store in database
# On subsequent runs, use database values
```

This approach:
- Keeps external agents simple
- Respects database as source of truth
- Maintains API compatibility
- Requires minimal changes