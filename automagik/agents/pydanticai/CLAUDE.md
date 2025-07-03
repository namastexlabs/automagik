# CLAUDE.md

This file provides PydanticAI agent development context for Claude Code working in this directory.

## PydanticAI Agent Development Context

This directory contains PydanticAI-based agent implementations. When working here, you're developing agents that use the PydanticAI framework for structured AI interactions.

## 🤖 Agent Architecture Patterns

### Mandatory Agent Structure
```
agent_name/
├── __init__.py        # create_agent() factory function
├── agent.py           # Main agent class extending AutomagikAgent
├── prompts/
│   ├── __init__.py   
│   └── prompt.py      # AGENT_PROMPT constant definition
├── specialized/       # Optional: Domain-specific implementations
│   └── *.py          # Specialized tools or integrations
└── models.py         # Optional: Agent-specific data models
```

### Core Implementation Pattern
```python
# agent.py - MANDATORY structure
from src.agents.models import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
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

### Factory Function Pattern
```python
# __init__.py - MANDATORY for agent discovery
from typing import Dict
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

## 🔧 PydanticAI-Specific Patterns

### Tool Registration Strategies
```python
# Three ways to register tools for PydanticAI agents:

# 1. Default tools (automatic)
self.tool_registry.register_default_tools(self.context)

# 2. MCP tools (automatic from configured servers)
# Loaded automatically via mcp_manager

# 3. Custom tools (manual via decorator)
@self.agent.tool
async def custom_tool(ctx: RunContext, param: str) -> str:
    """Custom tool specific to this agent."""
    return f"Processed: {param}"
```

### Context Management
```python
# Agent context contains:
# - agent_id: Unique identifier
# - user_id: Current user
# - session_id: Conversation session
# - channel_config: Channel-specific settings
# - mcp_manager: MCP server manager instance
```

### Memory Template System
```python
# Prompts support {{variable}} substitution
AGENT_PROMPT = """You are a helpful assistant.
User: {{user_name}} | Context: {{recent_context}}
Preferences: {{user_preferences}}
Available tools: {tools}"""

# Variables auto-injected from:
# - User preferences from memory searches
# - Recent conversation context
# - Agent-specific variables
```

### Message History Handling
```python
# PydanticAI agents automatically maintain conversation history
self.message_history  # List of messages
self._get_recent_messages(n=10)  # Get last N messages
```

## 🎯 Agent Types & Patterns

### Simple Agent Pattern
Basic implementation for general-purpose agents:
```python
# Use src/agents/pydanticai/simple/ as template
# Single prompt, basic tool registration
# Standard conversation handling
```

### Multi-State Agent Pattern (Stan)
Dynamic prompts based on user state:
```python
# prompts/approved.py, pending_review.py, etc.
def _load_prompt_for_status(self, status: str) -> str:
    prompts = {
        "approved": APPROVED_PROMPT,
        "pending": PENDING_PROMPT,
        "rejected": REJECTED_PROMPT
    }
    return prompts.get(status, DEFAULT_PROMPT)
```

### Specialized Integration Pattern (Sofia)
Domain-specific functionality:
```python
# specialized/airtable.py - Domain-specific tools
# specialized/bella.py - Meeting creation tools
# Complex prompt with role-based responses
```

### Multimodal Agent Pattern (Discord)
Handling images and attachments:
```python
# Discord-specific context management
# Multimodal message processing
# Channel configuration handling
```

### WhatsApp Integration Pattern (Evolution Agents)
```python
# Message formatting for WhatsApp
# Context management for conversations
# Portuguese language support
```

## 🛠️ Development Commands

```bash
# Test specific agent
pytest tests/agents/test_my_agent.py -v

# Test with markers  
pytest -m "not integration" tests/agents/test_my_agent.py

# Interactive testing
automagik agents chat -a my_agent
automagik agents run -a my_agent -m "Test message"

# Code quality
ruff check --exit-zero --fix src/agents/pydanticai/my_agent/
ruff format src/agents/pydanticai/my_agent/

# Create new agent from template
automagik agents create -n new_agent -t simple
```

## 🧪 Testing Patterns

### Unit Test Structure
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

@pytest.mark.integration
async def test_with_llm():
    # Tests requiring actual LLM calls
    pass
```

## 🔍 Debugging Techniques

```bash
# Enable debug logging
export AUTOMAGIK_LOG_LEVEL=DEBUG
automagik agents chat -a my_agent

# Check agent registration
# In agent.py constructor:
log.debug(f"Registered tools: {self.tool_registry.list_tools()}")

# Test prompt rendering
rendered = self._render_prompt({"user_name": "test"})
log.debug(f"Rendered prompt: {rendered}")
```

## 📚 Common Imports for PydanticAI Agents

```python
# Core PydanticAI imports
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext

# Framework imports
from src.agents.models import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.common.context_aware_tool_wrapper import create_context_aware_tool
from src.config import get_settings
import src.utils.logging as log

# Async operations
import asyncio
from httpx import AsyncClient
```

## ✅ Development Checklist

When creating/modifying PydanticAI agents:

- [ ] Follow mandatory directory structure
- [ ] Extend `AutomagikAgent` base class  
- [ ] Define `AGENT_PROMPT` in `prompts/prompt.py`
- [ ] Implement `create_agent()` factory in `__init__.py`
- [ ] Set `self._code_prompt_text = AGENT_PROMPT`
- [ ] Initialize `AutomagikAgentsDependencies`
- [ ] Register default tools via `register_default_tools()`
- [ ] Add unit tests in `tests/agents/`
- [ ] Run linting: `ruff check --fix`
- [ ] Test interactively: `automagik agents chat -a agent_name`
- [ ] Verify tool registration and message handling

## 🚨 PydanticAI-Specific Considerations

### Framework Constraints
- PydanticAI agents require structured prompts
- Tool definitions must be compatible with PydanticAI's tool system
- Context passing follows PydanticAI's RunContext pattern
- Message history maintained in PydanticAI format

### Performance Patterns
- Use async/await for all tool operations
- Leverage PydanticAI's built-in streaming for long responses
- Implement proper error handling with PydanticAI's error system
- Use structured outputs for complex responses

This context focuses specifically on PydanticAI agent development patterns and should be used alongside the global development rules in the root CLAUDE.md.