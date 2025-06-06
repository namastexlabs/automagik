# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## PydanticAI Agents Directory Overview

This directory contains all PydanticAI-based agent implementations. Each agent follows a consistent structure and pattern that must be maintained when creating new agents or modifying existing ones.

## Directory Structure

Each agent follows this mandatory structure:
```
agent_name/
├── __init__.py        # Module initialization with create_agent() export
├── agent.py           # Main agent class extending AutomagikAgent
├── prompts/
│   ├── __init__.py   
│   └── prompt.py      # AGENT_PROMPT constant definition
├── specialized/       # Optional: Domain-specific implementations
│   └── *.py          # Specialized tools or integrations
└── models.py         # Optional: Agent-specific data models
```

## Development Rules

### MANDATORY: Agent Implementation Pattern

```python
# agent.py structure
from src.agents.models import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from typing import Dict
from .prompts.prompt import AGENT_PROMPT

class MyAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        
        # REQUIRED: Set the agent prompt
        self._code_prompt_text = AGENT_PROMPT
        
        # REQUIRED: Initialize dependencies
        self.dependencies = AutomagikAgentsDependencies(...)
        
        # REQUIRED: Register default tools
        self.tool_registry.register_default_tools(self.context)
        
        # Optional: Register agent-specific tools
        self._register_tools()
```

### MANDATORY: Module Initialization

```python
# __init__.py structure
from typing import Dict, Union
from src.agents.common.placeholder import PlaceholderAgent
from logfire import instrument_module
import src.utils.logging as log

instrument_module(__name__)

def create_agent(config: Dict[str, str]):
    """Factory function to create agent instance."""
    try:
        from .agent import MyAgent
        return MyAgent(config)
    except Exception as e:
        log.error(f"Failed to create MyAgent: {e}")
        return PlaceholderAgent(config)
```

## Common Commands

### Testing Agent Implementation
```bash
# Test single agent
pytest tests/agents/test_my_agent.py -v

# Test with specific markers
pytest -m "not integration" tests/agents/test_my_agent.py

# Run agent interactively
automagik agents chat -a my_agent
automagik agents run -a my_agent -m "Test message"
```

### Code Quality
```bash
# Format and lint agent code
ruff check --exit-zero --fix src/agents/pydanticai/my_agent/
ruff format src/agents/pydanticai/my_agent/
```

### Creating New Agent
```bash
# Use the CLI to create from template
automagik agents create -n new_agent -t simple

# Or copy existing agent structure
cp -r src/agents/pydanticai/simple src/agents/pydanticai/new_agent
```

## Architecture Patterns

### 1. Tool Registration
Agents can register tools in three ways:
- **Default tools**: Via `self.tool_registry.register_default_tools()`
- **MCP tools**: Automatically loaded from configured MCP servers
- **Custom tools**: Via `@self.agent.tool` decorator in `_register_tools()`

### 2. Context Management
All agents receive a context dictionary containing:
- `agent_id`: Unique identifier
- `user_id`: Current user
- `session_id`: Conversation session
- `channel_config`: Channel-specific settings
- `mcp_manager`: MCP server manager instance

### 3. Message History
Agents automatically maintain PydanticAI-formatted conversation history:
```python
# Accessed via
self.message_history  # List of messages
self._get_recent_messages()  # Get last N messages
```

### 4. Memory Integration
Prompts support `{{variable}}` substitution with data from:
- User preferences from memory searches
- Recent conversation context
- Agent-specific variables

## Agent Types Reference

### Simple Agent
Basic implementation demonstrating core patterns. Use as template for new agents.

### Stan Agent
Multi-state agent with different prompts based on user status:
- `approved.py`, `pending_review.py`, `rejected.py`, `verifying.py`, `not_registered.py` prompts
- Dynamic prompt loading based on BlackPearl `status_aprovacao`
- Specialized BlackPearl integration with contact management
- Tools: `verificar_cnpj`, `product_agent`, `backoffice_agent`
- **Recently refactored**: Now uses new framework-agnostic architecture with channel handlers

### Sofia Agent
Meeting management agent with:
- Airtable integration (`specialized/airtable.py`)
- Meeting creation tools (`specialized/bella.py`)
- Complex prompt with role-based responses

### Discord Agent
Discord bot integration with multimodal support:
- Handles images and attachments
- Discord-specific context management
- Channel configuration handling

### Evolution Agents (Estruturar/Flashinho)
WhatsApp integration via Evolution API:
- Message formatting for WhatsApp
- Context management for conversations
- Portuguese language support

## Testing Guidelines

### Unit Tests
```python
# tests/agents/test_my_agent.py
import pytest
from src.agents.pydanticai.my_agent import create_agent

def test_agent_creation():
    config = {"name": "test_agent"}
    agent = create_agent(config)
    assert agent is not None
    assert hasattr(agent, 'agent')

@pytest.mark.asyncio
async def test_agent_response():
    config = {"name": "test_agent"}
    agent = create_agent(config)
    response = await agent.process_message("Hello", {})
    assert response is not None
```

### Integration Tests
Mark tests requiring external services:
```python
@pytest.mark.integration
async def test_with_llm():
    # Tests requiring actual LLM calls
    pass
```

## Common Imports

Standard imports for all agents:
```python
# Core imports
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

# Framework imports
from src.agents.models import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.common.context_aware_tool_wrapper import create_context_aware_tool
from src.config import get_settings
import src.utils.logging as log

# For async operations
import asyncio
from httpx import AsyncClient
```

## Debugging Tips

1. **Enable debug logging**:
   ```bash
   export AM_LOG_LEVEL=DEBUG
   automagik agents chat -a my_agent
   ```

2. **Check agent registration**:
   ```python
   # In agent.py constructor
   log.debug(f"Registered tools: {self.tool_registry.list_tools()}")
   ```

3. **Test prompt rendering**:
   ```python
   # Check variable substitution
   rendered = self._render_prompt({"user_name": "test"})
   log.debug(f"Rendered prompt: {rendered}")
   ```

## Advanced Patterns

### Multi-Prompt Agents (like Stan)
```python
# Load different prompts based on state
def _load_prompt_for_status(self, status: str) -> str:
    prompts = {
        "approved": APPROVED_PROMPT,
        "pending": PENDING_PROMPT,
        "rejected": REJECTED_PROMPT
    }
    return prompts.get(status, DEFAULT_PROMPT)
```

### Specialized Sub-Agents
Create domain-specific functionality in `specialized/`:
```python
# specialized/domain_tool.py
class DomainSpecificTool:
    def __init__(self, context: Dict[str, Any]):
        self.context = context
    
    async def perform_action(self, params: Dict) -> Dict:
        # Implementation
        pass
```

## Checklist for New Agents

- [ ] Create directory structure following the pattern
- [ ] Extend `AutomagikAgent` base class
- [ ] Define `AGENT_PROMPT` in `prompts/prompt.py`
- [ ] Implement `create_agent()` in `__init__.py`
- [ ] Set `self._code_prompt_text = AGENT_PROMPT`
- [ ] Initialize `AutomagikAgentsDependencies`
- [ ] Register default tools via `register_default_tools()`
- [ ] Add unit tests in `tests/agents/`
- [ ] Run linting: `ruff check --fix src/agents/pydanticai/new_agent/`
- [ ] Test interactively: `automagik agents chat -a new_agent`

## Contributing

When modifying agents:
1. Maintain the established directory structure
2. Follow the mandatory implementation patterns
3. Add appropriate tests
4. Update agent-specific documentation if needed
5. Ensure backward compatibility with existing agent APIs