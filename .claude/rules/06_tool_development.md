---
description: Tool development patterns, PydanticAI integration, and async patterns for automagik-agents
globs: src/tools/**/*,tests/**/*tool*
alwaysApply: false
---
# Tool Development - PydanticAI & Async Patterns

## 🎯 Overview

**Related**: [dev_workflow.md](mdc:.cursor/rules/03_dev_workflow.md) - Development modes and workflow

Tool development for automagik-agents framework using PydanticAI patterns, async operations, and external service integrations.

## 🧠 **Memory-First Tool Development**

### **Before Starting Tool Development**
```bash
# Search for established tool patterns and procedures
agent-memory_search_memory_nodes --query "tool development patterns" --entity "Procedure"
```

**Key Searches**:
- **Existing patterns**: Search for similar tool implementations
- **Integration procedures**: How to connect external services
- **Error handling patterns**: How to handle API failures gracefully
- **Authentication patterns**: How tools handle API keys and secrets

## 🔧 Core Tool Development Patterns

### **1. PydanticAI Tool Structure**
```python
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel, Field
from typing import Dict, Optional
import asyncio

class ToolInput(BaseModel):
    """Input schema for the tool"""
    query: str = Field(..., description="Search query")
    filters: Optional[Dict] = Field(None, description="Optional filters")

class ToolOutput(BaseModel):
    """Output schema for the tool"""
    success: bool
    data: Optional[Dict] = None
    error: Optional[str] = None
    message: str

@agent.tool
async def my_tool(ctx: RunContext[Dict], input_data: ToolInput) -> ToolOutput:
    """
    Tool description for the agent.
    
    Args:
        ctx: Runtime context with agent dependencies
        input_data: Validated input parameters
        
    Returns:
        ToolOutput: Structured response
    """
    try:
        # Implementation here
        result = await perform_operation(input_data.query)
        return ToolOutput(
            success=True,
            data=result,
            message="Operation completed successfully"
        )
    except Exception as e:
        return ToolOutput(
            success=False,
            error=str(e),
            message="Operation failed"
        )
```

### **2. Async Operation Patterns**
```python
import httpx
import asyncio
from typing import List

class ServiceClient:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self):
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()
    
    async def get_data(self, endpoint: str) -> Dict:
        """Get data from API endpoint"""
        response = await self._client.get(endpoint)
        response.raise_for_status()
        return response.json()
    
    async def batch_requests(self, endpoints: List[str]) -> List[Dict]:
        """Process multiple requests concurrently"""
        tasks = [self.get_data(endpoint) for endpoint in endpoints]
        return await asyncio.gather(*tasks, return_exceptions=True)
```

### **3. Error Handling Patterns**
```python
from enum import Enum
from typing import Union

class ErrorType(Enum):
    AUTHENTICATION = "authentication_error"
    RATE_LIMIT = "rate_limit_exceeded"
    NOT_FOUND = "resource_not_found"
    TIMEOUT = "request_timeout"
    UNKNOWN = "unknown_error"

class ToolError(BaseModel):
    error_type: ErrorType
    message: str
    retry_after: Optional[int] = None

async def safe_api_call(operation) -> Union[Dict, ToolError]:
    """Wrapper for safe API calls with structured error handling"""
    try:
        return await operation()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            return ToolError(
                error_type=ErrorType.AUTHENTICATION,
                message="Invalid API credentials"
            )
        elif e.response.status_code == 429:
            retry_after = int(e.response.headers.get("Retry-After", 60))
            return ToolError(
                error_type=ErrorType.RATE_LIMIT,
                message="Rate limit exceeded",
                retry_after=retry_after
            )
        elif e.response.status_code == 404:
            return ToolError(
                error_type=ErrorType.NOT_FOUND,
                message="Resource not found"
            )
        else:
            return ToolError(
                error_type=ErrorType.UNKNOWN,
                message=f"HTTP {e.response.status_code}: {e.response.text}"
            )
    except httpx.TimeoutException:
        return ToolError(
            error_type=ErrorType.TIMEOUT,
            message="Request timed out"
        )
    except Exception as e:
        return ToolError(
            error_type=ErrorType.UNKNOWN,
            message=str(e)
        )
```

### **4. Configuration & Dependencies**
```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class ToolConfig(BaseSettings):
    """Tool configuration from environment"""
    api_key: str
    base_url: str = "https://api.service.com"
    timeout: int = 30
    max_retries: int = 3
    
    class Config:
        env_prefix = "SERVICE_"

@lru_cache()
def get_tool_config() -> ToolConfig:
    """Cached configuration instance"""
    return ToolConfig()

# Usage in tool
@agent.tool
async def service_tool(ctx: RunContext[Dict], input_data: ToolInput) -> ToolOutput:
    config = get_tool_config()
    async with ServiceClient(config.api_key, config.base_url) as client:
        result = await client.get_data(f"/search?q={input_data.query}")
        return ToolOutput(success=True, data=result, message="Success")
```

## 🔗 Tool Registration & Discovery

### **Tool Registration Pattern**
```python
# tools/my_service/interface.py
from pydantic_ai import Tool

# Define your tool functions here
@agent.tool
async def search_service(ctx: RunContext[Dict], input_data: SearchInput) -> SearchOutput:
    # Implementation
    pass

@agent.tool  
async def create_item(ctx: RunContext[Dict], input_data: CreateInput) -> CreateOutput:
    # Implementation
    pass

# Export tools for registration
my_service_tools = [search_service, create_item]

# tools/my_service/__init__.py
from .interface import my_service_tools

__all__ = ["my_service_tools"]

# tools/__init__.py
from .my_service import my_service_tools
from .other_service import other_service_tools

# Collect all tools
ALL_TOOLS = []
ALL_TOOLS.extend(my_service_tools)
ALL_TOOLS.extend(other_service_tools)

__all__ = ["ALL_TOOLS", "my_service_tools", "other_service_tools"]
```

### **Agent Tool Registration**
```python
# In AutomagikAgent extension
class MyAgent(AutomagikAgent):
    def __init__(self, config: Dict[str, str]) -> None:
        super().__init__(config)
        
        # Register default tools (required)
        self.tool_registry.register_default_tools(self.context)
        
        # Register service-specific tools (optional)
        from tools.my_service import my_service_tools
        for tool in my_service_tools:
            self.agent.tool(tool)
```

## 🧪 Testing Patterns

### **Unit Testing with Mocks**
```python
import pytest
from unittest.mock import AsyncMock, patch
import httpx

@pytest.mark.asyncio
async def test_service_tool_success():
    """Test successful API call"""
    mock_response = {"results": ["item1", "item2"]}
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response_obj = AsyncMock()
        mock_response_obj.json.return_value = mock_response
        mock_response_obj.raise_for_status.return_value = None
        mock_get.return_value = mock_response_obj
        
        input_data = ToolInput(query="test query")
        result = await my_tool({}, input_data)
        
        assert result.success is True
        assert result.data == mock_response
        mock_get.assert_called_once()

@pytest.mark.asyncio
async def test_service_tool_error_handling():
    """Test error handling"""
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.side_effect = httpx.HTTPStatusError(
            message="Not Found",
            request=AsyncMock(),
            response=AsyncMock(status_code=404)
        )
        
        input_data = ToolInput(query="test query")
        result = await my_tool({}, input_data)
        
        assert result.success is False
        assert "not found" in result.error.lower()
```

### **Integration Testing with Real Context**
```python
@pytest.mark.asyncio
async def test_tool_with_agent_context():
    """Test tool with actual agent context"""
    from src.agents.simple.my_agent.agent import MyAgent
    
    agent = MyAgent({})
    context = {"session_id": "test_session"}
    
    # Test tool via agent
    response = await agent.process_message(
        "Search for Python tutorials", 
        "test_session"
    )
    
    assert "tutorials" in response.lower()
    # Verify tool was called through logs or context
```

## 💾 Memory Integration for Tools

### **Store Tool Patterns**
```bash
# After successful tool implementation
agent-memory_search_memory_nodes --query "tool development patterns" --entity "Procedure"
agent-memory_search_memory_facts --query "tool integration dependencies"

# Store new patterns
agent-memory_add_memory \
  --name "Service Integration Pattern" \
  --episode_body "Successfully integrated external API using async client with structured error handling and retry logic" \
  --source "text" \
  --source_description "tool development procedure"

# Store configuration patterns
agent-memory_add_memory \
  --name "Tool Configuration Discovery" \
  --episode_body "{\"pattern\": \"environment_config\", \"required_vars\": [\"API_KEY\", \"BASE_URL\"], \"optional_vars\": [\"TIMEOUT\", \"MAX_RETRIES\"]}" \
  --source "json" \
  --source_description "tool configuration requirements"
```

## 🚀 Common Tool Implementation Patterns

### **Search/Query Tools**
```python
class SearchInput(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    limit: int = Field(10, ge=1, le=100)
    filters: Optional[Dict] = None

@agent.tool
async def search_knowledge(ctx: RunContext[Dict], input_data: SearchInput) -> ToolOutput:
    """Search knowledge base or external service"""
    # Implementation with pagination, filtering
    pass
```

### **Creation/Modification Tools**
```python
class CreateInput(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)

@agent.tool
async def create_document(ctx: RunContext[Dict], input_data: CreateInput) -> ToolOutput:
    """Create new document in external service"""
    # Implementation with validation, error handling
    pass
```

### **Data Retrieval Tools**
```python
class RetrievalInput(BaseModel):
    resource_id: str = Field(..., pattern=r"^[a-zA-Z0-9_-]+$")
    include_metadata: bool = False

@agent.tool  
async def get_resource(ctx: RunContext[Dict], input_data: RetrievalInput) -> ToolOutput:
    """Retrieve specific resource by ID"""
    # Implementation with caching, error handling
    pass
```

## 🔒 Security & Best Practices

### **API Key Management**
```python
import os
from typing import Optional

def get_api_key(service_name: str) -> Optional[str]:
    """Securely retrieve API key from environment"""
    key = os.getenv(f"{service_name.upper()}_API_KEY")
    if not key:
        raise ValueError(f"Missing {service_name.upper()}_API_KEY environment variable")
    return key

# Usage
api_key = get_api_key("openai")  # Looks for OPENAI_API_KEY
```

### **Input Validation**
```python
from pydantic import validator, Field
import re

class SecureInput(BaseModel):
    user_query: str = Field(..., min_length=1, max_length=1000)
    
    @validator('user_query')
    def validate_query(cls, v):
        # Remove potentially dangerous patterns
        if re.search(r'[<>"\';]', v):
            raise ValueError("Query contains invalid characters")
        return v.strip()
```

### **Rate Limiting & Retry Logic**
```python
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def api_call_with_retry(client: httpx.AsyncClient, endpoint: str):
    """API call with automatic retry on failure"""
    response = await client.get(endpoint)
    response.raise_for_status()
    return response.json()
```

---

**Remember**: Always search memory for existing patterns, use structured input/output models, handle errors gracefully with proper typing, implement async patterns for I/O operations, and store successful patterns for team reuse. Tools should be composable, testable, and follow the established AutomagikAgent framework patterns.
