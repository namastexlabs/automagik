---
description: "Core development patterns, coding standards, and best practices"
globs:
  - "**/*.py"
  - "**/src/**"
  - "**/*test*.py"
  - "**/src/agents/**"
  - "**/src/tools/**"
  - "**/src/utils/**"
alwaysApply: false
priority: 5
---

# Development Guide: Agents, Tools & Coding Patterns

This guide covers all aspects of development in the Automagik Agents framework, from creating new agents to building tools and following proper coding patterns.

## Core Development Principles

### 1. Extend, Don't Modify
- **Always extend** base functionality rather than modifying base classes
- **Override methods** in your specific implementations
- **Keep shared functionality intact** for maintainability across all components

### 2. Type Safety & Async-First
- All agent and tool functions **MUST** be `async`
- Use proper type hints throughout your code
- Return structured responses, never raw strings
- Handle errors gracefully with proper response models

### 3. Configuration Management
- **NEVER** access environment variables directly (`os.getenv`)
- **ALWAYS** use `from src.config import settings`
- All configuration must be centralized and validated

## Agent Development

### Agent Architecture Overview

```
src/agents/
├── models/                 # Abstract base classes & shared helpers
└── simple/                 # Reference implementations
    ├── simple_agent/      # "Hello-world" style template
    ├── stan_agent/        # Full CRM + Blackpearl integration
    ├── sofia_agent/       # Advanced WhatsApp (Evolution) flow
    ├── flashinho_agent/   # Lightweight memory demo
    ├── discord_agent/     # Discord chat-bot persona
    ├── prompt_maker_agent/ # Meta-agent for prompt generation
    ├── stan_email_agent/  # Email-centric CRM assistant
    └── estruturar_agent/  # Portuguese structured conversation
```

### Base Class Contract (`AutomagikAgent`)

Every agent **MUST** implement:

1. **`async initialize_prompts()`** - Register or load system prompts (idempotent)
2. **`async run(input_text: str, ...) -> AgentResponse`** - Core execution logic
3. **`tool_registry.register_default_tools(self.context)`** - Call in `__init__`
4. **Return `AgentResponse`** objects, never raw strings

### Creating a New Agent

**Step-by-Step Checklist:**

1. **Create Directory Structure**:
   ```bash
   mkdir -p src/agents/simple/<your_agent>
   cd src/agents/simple/<your_agent>
   ```

2. **Create `agent.py`**:
   ```python
   from src.agents.models.automagik_agent import AutomagikAgent
   from src.agents.models.agent_response import AgentResponse
   from pydantic_ai import RunContext
   
   class YourAgent(AutomagikAgent):
       async def initialize_prompts(self):
           """Initialize agent prompts - keep idempotent"""
           # Load your prompts here
           pass
           
       async def run(self, input_text: str, **kwargs) -> AgentResponse:
           """Core agent execution logic"""
           # Your implementation here
           return AgentResponse(
               response="Your response",
               success=True
           )
   ```

3. **Create `__init__.py`**:
   ```python
   from .agent import YourAgent
   
   __all__ = ["YourAgent"]
   
   def create_agent():
       """Factory function for auto-discovery"""
       return YourAgent()
   ```

4. **Add Prompts Directory**:
   ```bash
   mkdir prompts
   # Add prompt.py for default, or status-based prompts
   ```

5. **Register Tools in `__init__`**:
   ```python
   def __init__(self, config, system_prompt):
       super().__init__(config, system_prompt)
       
       # Register default tools (required)
       self.tool_registry.register_default_tools(self.context)
       
       # Register agent-specific tools
       self.tool_registry.register_tool(your_custom_tool)
   ```

6. **Write Tests**:
   ```python
   # tests/agents/test_your_agent.py
   import pytest
   from src.agents.simple.your_agent import YourAgent
   
   @pytest.mark.asyncio
   async def test_your_agent_run():
       agent = YourAgent()
       response = await agent.run("test input")
       assert response.success is True
   ```

### Agent Patterns & Examples

#### WhatsApp Agent Pattern (Sofia)
For WhatsApp integration with Evolution API:

```python
from src.agents.common.evolution import EvolutionMessagePayload

class WhatsAppAgent(AutomagikAgent):
    def __init__(self, config, system_prompt):
        super().__init__(config, system_prompt)
        
        # Auto-wrap Evolution tools
        self._create_evolution_wrappers()
    
    def _create_evolution_wrappers(self):
        """Create tool wrappers that auto-inject phone numbers"""
        from src.tools.evolution.tool import send_message
        
        async def send_text(ctx: RunContext, text: str):
            phone = ctx.evolution_payload.get_user_number()
            return await send_message(ctx, phone, text)
        
        self.tool_registry.register_tool(send_text)
```

#### CRM Agent Pattern (Stan)
For multi-prompt, status-based agents:

```python
class CRMAgent(AutomagikAgent):
    async def initialize_prompts(self):
        """Load different prompts based on contact status"""
        self.prompts = {
            "NOT_REGISTERED": await self.load_prompt("not_registered"),
            "APPROVED": await self.load_prompt("approved"),
            "PENDING": await self.load_prompt("pending")
        }
    
    async def run(self, input_text: str, **kwargs) -> AgentResponse:
        contact_status = kwargs.get("contact_status", "NOT_REGISTERED")
        prompt = self.prompts.get(contact_status, self.prompts["NOT_REGISTERED"])
        
        # Use appropriate prompt for contact status
        # Implementation continues...
```

### Agent Development Rules

#### ✅ DO:
- Extend `AutomagikAgent` for all custom agents
- Use `AgentResponse` objects for returns
- Register tools through `tool_registry`
- Handle errors gracefully
- Write comprehensive tests
- Use proper async/await patterns

#### ❌ DON'T:
- Modify base classes directly
- Return raw strings from `run()` method
- Access environment variables directly
- Forget to register default tools
- Block on synchronous operations

## Tool Development

### Tool Architecture

```
src/tools/<tool_name>/
    __init__.py      # Re-export `<tool_name>_tools` from interface.py
    schema.py        # Pydantic input/output models
    provider.py      # (optional) Low-level API integration
    tool.py          # Async business logic functions
    interface.py     # Wraps functions in pydantic_ai.tools.Tool objects
```

### Tool Development Rules

#### 1. Async Functions & RunContext
Every tool function **MUST** follow this pattern:

```python
async def my_tool(ctx: RunContext[Dict], <parameters>) -> Dict[str, Any]:
    """Tool description"""
    # Implementation
    return result.dict()  # Always return dict from Pydantic model
```

#### 2. Schema Definitions
Define Pydantic models for all inputs and outputs:

```python
# schema.py
from pydantic import BaseModel

class MyToolInput(BaseModel):
    query: str
    limit: int = 10

class MyToolOutput(BaseModel):
    success: bool
    data: list = []
    error_message: str = ""
```

#### 3. Error Handling
Never raise exceptions - return error models:

```python
async def my_tool(ctx: RunContext[Dict], input_data: str) -> Dict[str, Any]:
    try:
        # Tool logic here
        result = await some_operation(input_data)
        return MyToolOutput(success=True, data=result).dict()
    except Exception as e:
        return MyToolOutput(
            success=False, 
            error_message=str(e)
        ).dict()
```

#### 4. Tool Registration
Create tools in `interface.py`:

```python
# interface.py
from pydantic_ai.tools import Tool
from .tool import my_tool

def get_my_tool_description() -> str:
    return "Description of what the tool does"

my_tool_object = Tool(
    name="namespace_my_tool",
    description=get_my_tool_description(),
    function=my_tool,
)

my_tool_package_tools = [my_tool_object]
```

Export from `__init__.py`:
```python
# __init__.py
from .interface import my_tool_package_tools

__all__ = ["my_tool_package_tools"]
```

#### 5. Global Registration
Add to `src/tools/__init__.py`:

```python
from .my_tool_package import my_tool_package_tools

__all__ = [
    # ... existing tools
    "my_tool_package_tools",
]
```

### Creating a New Tool - Complete Checklist

1. **Create Directory**: `mkdir -p src/tools/<tool_name>`

2. **Create Schema** (`schema.py`):
   ```python
   from pydantic import BaseModel
   
   class ToolInput(BaseModel):
       # Input fields
       pass
   
   class ToolOutput(BaseModel):
       success: bool
       # Output fields
       error_message: str = ""
   ```

3. **Implement Provider** (`provider.py`) - if needed for external APIs:
   ```python
   from src.config import settings
   import httpx
   
   async def external_api_call(data):
       """Handle external API communication"""
       async with httpx.AsyncClient() as client:
           response = await client.post(
               settings.EXTERNAL_API_URL,
               headers={"Authorization": f"Bearer {settings.API_KEY}"},
               json=data
           )
           return response.json()
   ```

4. **Implement Business Logic** (`tool.py`):
   ```python
   from pydantic_ai import RunContext
   from .schema import ToolInput, ToolOutput
   from .provider import external_api_call
   import logging
   
   logger = logging.getLogger(__name__)
   
   async def tool_function(ctx: RunContext[Dict], input_data: str) -> Dict[str, Any]:
       """Main tool function"""
       logger.info(f"Tool called with: {input_data}")
       
       try:
           # Validate input
           validated_input = ToolInput(data=input_data)
           
           # Call provider if needed
           result = await external_api_call(validated_input.dict())
           
           # Return success response
           return ToolOutput(success=True, data=result).dict()
           
       except Exception as e:
           logger.error(f"Tool failed: {str(e)}")
           return ToolOutput(success=False, error_message=str(e)).dict()
   ```

5. **Create Interface** (`interface.py`):
   ```python
   from pydantic_ai.tools import Tool
   from .tool import tool_function
   
   def get_tool_description() -> str:
       return "Description of what this tool does"
   
   tool_object = Tool(
       name="namespace_tool_name",
       description=get_tool_description(),
       function=tool_function,
   )
   
   tool_package_tools = [tool_object]
   ```

6. **Create Package Init** (`__init__.py`):
   ```python
   from .interface import tool_package_tools
   
   __all__ = ["tool_package_tools"]
   ```

7. **Register Globally** in `src/tools/__init__.py`:
   ```python
   from .new_tool import tool_package_tools
   
   __all__.append("tool_package_tools")
   ```

8. **Write Tests**:
   ```python
   # tests/tools/test_new_tool.py
   import pytest
   from src.tools.new_tool.tool import tool_function
   
   @pytest.mark.asyncio
   async def test_tool_success():
       ctx = {}  # Mock context
       result = await tool_function(ctx, "test input")
       assert result["success"] is True
   
   @pytest.mark.asyncio
   async def test_tool_error_handling():
       ctx = {}
       result = await tool_function(ctx, "invalid input")
       assert result["success"] is False
       assert "error_message" in result
   ```

### Tool Development Patterns

#### Configuration Access
```python
# ✅ CORRECT
from src.config import settings
api_key = settings.GOOGLE_API_KEY

# ❌ WRONG
import os
api_key = os.environ.get("GOOGLE_API_KEY")
```

#### Logging
```python
import logging

logger = logging.getLogger(__name__)

async def my_tool(ctx, data):
    logger.info(f"Tool called with: {data}")
    try:
        # Tool logic
        logger.info("Tool completed successfully")
    except Exception as e:
        logger.error(f"Tool failed: {str(e)}")
```

#### HTTP Client Usage
```python
import httpx
from src.config import settings

async def api_call(data):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.API_ENDPOINT,
            headers={"Authorization": f"Bearer {settings.API_KEY}"},
            json=data,
            timeout=30.0
        )
        response.raise_for_status()
        return response.json()
```

## Coding Standards & Best Practices

### Code Style
- Follow PEP 8 style guidelines
- Use `black` for code formatting
- Use `isort` for import sorting
- Run `pre-commit run --all-files` before committing

### Naming Conventions
- Use `snake_case` for functions and variables
- Use `PascalCase` for classes
- Use descriptive names that indicate purpose
- Prefix tool objects with package name: `gmail_send_email_tool`

### Error Handling
```python
# ✅ GOOD: Structured error handling
try:
    result = await some_operation()
    return SuccessResponse(data=result).dict()
except SpecificException as e:
    logger.error(f"Specific error: {str(e)}")
    return ErrorResponse(error_message=str(e)).dict()
except Exception as e:
    logger.error(f"Unexpected error: {str(e)}")
    return ErrorResponse(error_message="An unexpected error occurred").dict()

# ❌ BAD: Letting exceptions bubble up
result = await some_operation()  # Could raise exception
return result  # No error handling
```

### Async/Await Patterns
```python
# ✅ GOOD: Proper async usage
async def fetch_multiple_resources():
    async with httpx.AsyncClient() as client:
        tasks = [
            client.get(url1),
            client.get(url2),
            client.get(url3)
        ]
        responses = await asyncio.gather(*tasks)
    return responses

# ❌ BAD: Sequential async calls
async def fetch_multiple_resources_bad():
    async with httpx.AsyncClient() as client:
        result1 = await client.get(url1)  # Waits for each
        result2 = await client.get(url2)  # sequentially
        result3 = await client.get(url3)
    return [result1, result2, result3]
```

### Testing Patterns
```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_agent_with_mocked_dependencies():
    # Mock external dependencies
    with patch('src.tools.external.provider.external_call') as mock_call:
        mock_call.return_value = {"status": "success"}
        
        agent = MyAgent()
        response = await agent.run("test input")
        
        assert response.success is True
        mock_call.assert_called_once()

@pytest.fixture
async def mock_context():
    """Reusable mock context for testing"""
    return {
        "user_id": "test_user",
        "session_id": "test_session"
    }
```

## Integration Patterns

### Database Integration
```python
from src.db.connection import get_db_connection

async def store_agent_result(result_data):
    async with get_db_connection() as db:
        # Use database connection
        await db.execute("INSERT INTO results ...", result_data)
```

### Memory Integration
```python
from src.tools.memory import create_memory, read_memory

async def agent_with_memory(ctx, input_text):
    # Store conversation
    await create_memory(ctx, {
        "type": "conversation",
        "content": input_text,
        "timestamp": datetime.utcnow()
    })
    
    # Retrieve relevant memories
    memories = await read_memory(ctx, query=input_text)
```

### Task Management Integration
Always use the Task Management System for tracking development work:

```bash
# Plan your work
task-master next

# Track progress
task-master update-subtask --id=X.Y --prompt="Implementation progress..."

# Mark completion
task-master set-status --id=X.Y --status=done
```

## Common Pitfalls & Solutions

### 1. Synchronous Code in Async Context
```python
# ❌ WRONG: Blocking operations
def process_file(file_path):
    with open(file_path, 'r') as f:
        return f.read()

# ✅ CORRECT: Async file operations
async def process_file(file_path):
    async with aiofiles.open(file_path, 'r') as f:
        return await f.read()
```

### 2. Missing Error Handling
```python
# ❌ WRONG: No error handling
async def risky_operation():
    result = await external_api_call()
    return result.data

# ✅ CORRECT: Proper error handling
async def safe_operation():
    try:
        result = await external_api_call()
        return OperationResult(success=True, data=result.data).dict()
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")
        return OperationResult(success=False, error_message=str(e)).dict()
```

### 3. Configuration Anti-patterns
```python
# ❌ WRONG: Direct environment access
import os
api_key = os.getenv("API_KEY")

# ✅ CORRECT: Centralized configuration
from src.config import settings
api_key = settings.API_KEY
```

## Development Workflow Integration

1. **Start with Task Management**: Use `task-master next` to identify work
2. **Plan Implementation**: Break down complex tasks into subtasks
3. **Follow TDD**: Write tests before implementation
4. **Use Type Hints**: Ensure proper typing throughout
5. **Document Progress**: Update subtasks with implementation details
6. **Test Thoroughly**: Run full test suite before marking complete
7. **Follow Code Style**: Use pre-commit hooks for consistency

## Performance Considerations

- Use connection pooling for database operations
- Implement proper caching for expensive operations
- Use `asyncio.gather()` for parallel operations
- Monitor memory usage in long-running agents
- Implement proper timeout handling for external calls

This development guide provides the foundation for creating robust, maintainable agents and tools. Always refer back to these patterns when implementing new functionality.
