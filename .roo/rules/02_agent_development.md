---
description: "Agent creation, extension, and management patterns for automagik-agents framework"
globs:
  - "**/src/agents/**/*.py"
  - "**/*agent*.py"
  - "**/prompts.py"
  - "**/tools.py"
  - "**/config.py"
alwaysApply: false
priority: 2
---

# Agent Development Guide

This guide covers everything you need to know about creating, customizing, and deploying agents in the Automagik Agents framework.

## 🤖 Agent Architecture Overview

### Base Agent Class: AutomagikAgent
All agents inherit from `AutomagikAgent` which provides:
- **Memory Integration**: Automatic conversation persistence
- **Tool Management**: Dynamic tool loading and execution
- **Session Handling**: Multi-user conversation management
- **Prompt Templating**: Dynamic variable injection
- **API Integration**: Automatic endpoint generation

### Agent Lifecycle
1. **Discovery**: Auto-detected from `src/agents/simple/` directory
2. **Registration**: Imported and registered with `AgentFactory`
3. **Initialization**: System prompts and tools loaded
4. **Execution**: Messages processed through Pydantic AI
5. **Memory**: Conversations automatically persisted

## 🚀 Quick Start: Creating Your First Agent

### 1. Generate Agent Template
```bash
automagik-agents create-agent -n my_agent -t simple_agent
```

This creates:
```
src/agents/simple/my_agent/
├── __init__.py               # Agent registration
├── agent.py                  # Main agent implementation  
├── config.py                 # Agent configuration
├── prompts.py                # System prompts
└── tools.py                  # Agent-specific tools
```

### 2. Basic Agent Implementation
```python
# src/agents/simple/my_agent/agent.py
from src.agents.models.automagik_agent import AutomagikAgent
from .prompts import SYSTEM_PROMPT
from .config import MyAgentConfig
from .tools import MyAgentTools

class MyAgent(AutomagikAgent):
    def __init__(self):
        super().__init__(
            agent_name="my_agent",
            system_prompt=SYSTEM_PROMPT,
            tools=MyAgentTools().get_tools(),
            config=MyAgentConfig()
        )
    
    async def process_message(self, message: str, session_name: str = "default") -> str:
        """Process incoming message with full context."""
        try:
            # Custom preprocessing if needed
            processed_message = self.preprocess_message(message)
            
            # Run agent with automatic memory injection
            response = await self.run_agent(processed_message, session_name)
            
            # Custom postprocessing if needed
            return self.postprocess_response(response)
        except Exception as e:
            self.logger.error(f"Error processing message: {str(e)}")
            return "I encountered an error processing your message. Please try again."
    
    def preprocess_message(self, message: str) -> str:
        """Custom message preprocessing."""
        # Add custom logic here
        return message
    
    def postprocess_response(self, response: str) -> str:
        """Custom response postprocessing."""
        # Add custom logic here
        return response
```

### 3. Define System Prompts
```python
# src/agents/simple/my_agent/prompts.py
SYSTEM_PROMPT = """You are a helpful AI assistant specialized in [your domain].

Key behaviors:
- Be concise but thorough
- Ask clarifying questions when needed  
- Use available tools when appropriate
- Maintain context across conversations

Memory context will be automatically injected:
- {{user_name}}: Current user's name
- {{recent_context}}: Recent conversation context
- {{preferences}}: User preferences and settings
- {{custom_memory}}: Any custom memory variables

Available tools: {tools}
"""

# Optional: Prompt variations
DETAILED_PROMPT = """Extended version for complex tasks..."""
CONCISE_PROMPT = """Shorter version for quick responses..."""
```

### 4. Configure Agent Settings
```python
# src/agents/simple/my_agent/config.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class MyAgentConfig:
    """Configuration for MyAgent."""
    max_tokens: int = 1000
    temperature: float = 0.7
    enable_memory: bool = True
    enable_graphiti: bool = False
    custom_setting: str = "default_value"
    
    # Tool-specific settings
    tool_timeout: int = 30
    max_retries: int = 3
```

### 5. Register Agent
```python
# src/agents/simple/my_agent/__init__.py
from .agent import MyAgent

# Auto-registration happens here
__all__ = ["MyAgent"]
```

## 🔧 Advanced Agent Features

### Memory Integration
```python
class AdvancedAgent(AutomagikAgent):
    async def process_message(self, message: str, session_name: str = "default") -> str:
        # Add custom memory before processing
        await self.add_memory(
            name="user_intent",
            content=f"User asked about: {self.extract_intent(message)}",
            session_name=session_name
        )
        
        # Memory automatically injected into prompts via templates
        return await self.run_agent(message, session_name)
    
    async def add_custom_context(self, context: str, session_name: str):
        """Add custom context that persists across conversations."""
        await self.memory_manager.add_memory(
            agent_id=self.agent_id,
            name="custom_context",
            content=context,
            session_name=session_name
        )
```

### Dynamic Prompt Selection
```python
class AdaptiveAgent(AutomagikAgent):
    def __init__(self):
        self.prompts = {
            "default": SYSTEM_PROMPT,
            "detailed": DETAILED_PROMPT,
            "concise": CONCISE_PROMPT
        }
        super().__init__(
            agent_name="adaptive_agent",
            system_prompt=self.prompts["default"]
        )
    
    async def process_message(self, message: str, session_name: str = "default") -> str:
        # Select prompt based on message characteristics
        prompt_type = self.select_prompt_type(message)
        self.system_prompt = self.prompts[prompt_type]
        
        return await self.run_agent(message, session_name)
    
    def select_prompt_type(self, message: str) -> str:
        if len(message) > 500:
            return "detailed"
        elif len(message) < 50:
            return "concise"
        return "default"
```

### Tool Management
```python
# src/agents/simple/my_agent/tools.py
from typing import List
from pydantic import BaseModel
from src.tools.notion import NotionTools
from src.tools.gmail import GmailTools

class CustomToolInput(BaseModel):
    query: str
    options: dict = {}

def custom_tool(input: CustomToolInput) -> str:
    """Custom tool for specific agent needs."""
    # Tool implementation
    return f"Processed: {input.query}"

class MyAgentTools:
    def get_tools(self) -> List:
        """Return all tools available to this agent."""
        tools = []
        
        # Add custom tools
        tools.append(custom_tool)
        
        # Add external integrations
        if self.config.enable_notion:
            tools.extend(NotionTools().get_tools())
        
        if self.config.enable_gmail:
            tools.extend(GmailTools().get_tools())
        
        return tools
```

## 🧠 Memory System Deep Dive

### Memory Variables
The memory system automatically injects variables into prompts:

```python
# In your prompts.py
SYSTEM_PROMPT = """You are assisting {{user_name}}.

Recent context: {{recent_context}}
User preferences: {{preferences}}
Previous tasks: {{completed_tasks}}
Current project: {{active_project}}

Custom variables you can add:
- {{specialist_knowledge}}: Domain-specific information
- {{user_mood}}: Detected emotional state
- {{conversation_goal}}: Stated objective
"""
```

### Memory Management
```python
class MemoryAwareAgent(AutomagikAgent):
    async def handle_user_preference(self, preference: str, session_name: str):
        """Store user preference for future use."""
        await self.add_memory(
            name="preferences",
            content=preference,
            session_name=session_name
        )
    
    async def get_conversation_history(self, session_name: str, limit: int = 10):
        """Retrieve recent conversation history."""
        return await self.memory_manager.get_recent_messages(
            session_name=session_name,
            limit=limit
        )
    
    async def summarize_session(self, session_name: str):
        """Create summary of session for long-term memory."""
        history = await self.get_conversation_history(session_name, limit=50)
        summary = await self.create_summary(history)
        
        await self.add_memory(
            name="session_summary",
            content=summary,
            session_name=session_name
        )
```

## 🌐 API Integration

### Automatic Endpoint Generation
Each agent automatically gets API endpoints:
- `POST /api/v1/agent/{agent_name}/run` - Execute agent
- `GET /api/v1/agent/{agent_name}/info` - Get agent information
- `POST /api/v1/agent/{agent_name}/memory` - Manage agent memory

### Custom Endpoints
```python
# Add to src/api/routes/agent_routes.py
@router.post("/agent/{agent_name}/custom-action")
async def custom_agent_action(
    agent_name: str, 
    request: CustomRequest,
    api_key: str = Depends(verify_api_key)
):
    agent = AgentFactory.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    # Custom action implementation
    result = await agent.custom_action(request.data)
    return {"result": result, "status": "success"}
```

## 🧪 Testing Agents

### Unit Tests
```python
# tests/test_agents/test_my_agent.py
import pytest
from src.agents.simple.my_agent.agent import MyAgent

@pytest.mark.asyncio
async def test_agent_basic_response():
    agent = MyAgent()
    response = await agent.process_message("Hello", "test_session")
    
    assert response is not None
    assert len(response) > 0
    assert isinstance(response, str)

@pytest.mark.asyncio
async def test_agent_with_memory():
    agent = MyAgent()
    session = "memory_test_session"
    
    # First interaction
    await agent.process_message("My name is John", session)
    
    # Second interaction should remember name
    response = await agent.process_message("What's my name?", session)
    assert "John" in response
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_agent_api_endpoint(client):
    response = client.post(
        "/api/v1/agent/my_agent/run",
        json={
            "message_content": "Test message",
            "session_name": "test_session"
        },
        headers={"X-API-Key": "test_api_key"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert data["status"] == "success"
```

## 🚀 Deployment & Scaling

### Agent Startup Configuration
```python
# Configure which agents to load
# In .env file:
AM_AGENTS_NAMES=my_agent,another_agent,specialized_agent

# Or load all agents (default):
# AM_AGENTS_NAMES=  # Empty loads all
```

### Performance Optimization
```python
class OptimizedAgent(AutomagikAgent):
    def __init__(self):
        super().__init__(
            agent_name="optimized_agent",
            system_prompt=SYSTEM_PROMPT,
            # Performance tuning
            config=OptimizedConfig(
                max_tokens=500,          # Limit response length
                temperature=0.3,         # More deterministic
                enable_streaming=True,   # Stream responses
                cache_responses=True     # Cache common responses
            )
        )
    
    async def process_message(self, message: str, session_name: str = "default") -> str:
        # Check cache first
        cached_response = await self.check_cache(message)
        if cached_response:
            return cached_response
        
        # Process normally
        response = await self.run_agent(message, session_name)
        
        # Cache response
        await self.cache_response(message, response)
        
        return response
```

## 📋 Best Practices

### Agent Design Principles
1. **Single Responsibility**: Each agent should have a clear, focused purpose
2. **Stateless Processing**: Don't store state in agent instances
3. **Error Handling**: Always provide graceful error responses
4. **Memory Efficiency**: Use memory templates wisely
5. **Tool Selection**: Only include necessary tools

### Code Organization
```python
# Good: Clear separation of concerns
class WellOrganizedAgent(AutomagikAgent):
    def __init__(self):
        super().__init__(
            agent_name="well_organized",
            system_prompt=self._load_prompt(),
            tools=self._configure_tools(),
            config=self._load_config()
        )
    
    def _load_prompt(self) -> str:
        """Load and configure system prompt."""
        return SYSTEM_PROMPT
    
    def _configure_tools(self) -> List:
        """Configure agent tools based on requirements."""
        return MyAgentTools().get_tools()
    
    def _load_config(self):
        """Load agent configuration."""
        return MyAgentConfig()
```

### Security Considerations
```python
class SecureAgent(AutomagikAgent):
    async def process_message(self, message: str, session_name: str = "default") -> str:
        # Input validation
        if not self.validate_input(message):
            return "I can't process that type of message."
        
        # Rate limiting (implement as needed)
        if not await self.check_rate_limit(session_name):
            return "Please wait before sending another message."
        
        # Process safely
        return await self.run_agent(message, session_name)
    
    def validate_input(self, message: str) -> bool:
        """Validate user input for security."""
        # Implement validation logic
        return len(message) < 10000 and message.strip()
```

---

**Remember**: Focus on agent behavior and capabilities. The Automagik framework handles infrastructure, authentication, memory, and API generation automatically.
