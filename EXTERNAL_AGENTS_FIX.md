# External Agents Discovery Fix

## Problem Summary

External agents were not being discovered properly by the AgentFactory. When trying to create agents like `flashinho_pro`, the system was returning `ClaudeCodeAgent` instead.

## Root Causes

1. **Import Path Issues**: The tools were importing from `automagik.tools.flashed` which doesn't exist after the migration
2. **Class Name Mismatch**: The `__init__.py` files were importing class names without the "Refactored" suffix
3. **Circular Dependencies**: Tools were trying to import from each other using absolute paths

## Fixes Applied

### 1. Fixed Circular Imports in Tools
Changed imports in tool files from absolute to relative:
```python
# Before
from automagik.tools.flashed.provider import FlashedProvider

# After  
from .provider import FlashedProvider
```

### 2. Updated Class Names in __init__.py Files
Updated all agent __init__.py files to use the correct class names:
```python
# Before
from .agent import FlashinhoPro

# After
from .agent import FlashinhoProRefactored
```

### 3. Environment Variable
The `AUTOMAGIK_EXTERNAL_AGENTS_DIR` environment variable must be set before importing the AgentFactory:
```python
os.environ['AUTOMAGIK_EXTERNAL_AGENTS_DIR'] = '/path/to/agents_examples'
```

## Current Status

✅ All Flashinho agents are now discovered properly:
- flashinho_pro
- flashinho_pro_external  
- flashinho_the_first
- flashinho_old_make

✅ Agents can be created successfully with proper types
✅ All agents have required `run` and `process_message` methods

## Remaining Issues

1. **Automagik Dependencies**: External agents still depend on core automagik modules:
   - `automagik.config`
   - `automagik.db`
   - `automagik.agents.models.*`
   
   This means they're not truly "external" and require the full automagik package.

2. **Database/Config Access**: Tools need access to database and configuration which couples them to the main system.

## Recommendations

For truly external agents, consider:

1. **Dependency Injection**: Pass database/config objects to agents instead of importing
2. **Plugin Interface**: Create a minimal plugin interface that external agents implement
3. **Standalone Package**: Make external agents a separate package with minimal dependencies

## Testing

To verify external agents work:

```bash
# Set environment variable
export AUTOMAGIK_EXTERNAL_AGENTS_DIR=/home/cezar/automagik/am-agents-labs/agents_examples

# Test in Python
from automagik.agents.models.agent_factory import AgentFactory
AgentFactory.discover_agents()
agent = AgentFactory.create_agent('flashinho_pro')
print(type(agent).__name__)  # Should print: FlashinhoProRefactored
```