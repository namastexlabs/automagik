# CLAUDE.md

This file provides tool development context for Claude Code working in this directory.

## Tool Development Context

This directory contains external service integrations for Automagik Agents. When working here, you're developing tools that enable agents to interact with external APIs, services, and platforms.

## 🔧 Tool Architecture Overview

### Tool Structure Pattern
```
tool_name/
├── __init__.py        # Tool exports and registration
├── tool.py           # Main tool implementation
├── interface.py      # Tool interface definition
├── schema.py         # Pydantic models for input/output
├── provider.py       # Service provider abstraction (optional)
└── api.py           # Direct API client (optional)
```

### Core Components
- **Interface** - Defines tool capabilities and contracts
- **Schema** - Type-safe input/output models with Pydantic
- **Provider** - Service abstraction layer for complex integrations
- **Tool** - Main implementation with agent integration logic

## 🏗️ Tool Development Patterns

### Standard Tool Implementation
```python
# tool.py - Main tool implementation
from typing import Dict, Any, Optional
from pydantic import BaseModel
from .interface import ServiceInterface
from .schema import ToolInput, ToolOutput

class ServiceTool:
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.interface = ServiceInterface(config)
    
    async def execute(self, input_data: ToolInput) -> ToolOutput:
        """Execute tool with service integration."""
        
        try:
            # Validate input
            validated_input = ToolInput(**input_data)
            
            # Execute service operation
            result = await self.interface.perform_operation(validated_input)
            
            # Return structured output
            return ToolOutput(
                success=True,
                result=result,
                metadata={"tool": "service_tool", "timestamp": "..."}
            )
            
        except Exception as e:
            return ToolOutput(
                success=False,
                error=str(e),
                metadata={"tool": "service_tool", "error_type": type(e).__name__}
            )
```

### Tool Interface Pattern
```python
# interface.py - Service interface abstraction
from abc import ABC, abstractmethod
from typing import Dict, Any
from .schema import ToolInput, ServiceResult

class ServiceInterface(ABC):
    """Abstract interface for service integration."""
    
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self._initialize_client()
    
    @abstractmethod
    async def _initialize_client(self):
        """Initialize service client with authentication."""
        pass
    
    @abstractmethod
    async def perform_operation(self, input_data: ToolInput) -> ServiceResult:
        """Perform the main service operation."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check if service is available."""
        pass
    
    async def get_service_info(self) -> Dict[str, Any]:
        """Get service information and capabilities."""
        return {
            "service": self.__class__.__name__,
            "available": await self.health_check(),
            "config_keys": list(self.config.keys())
        }
```

### Schema Definition Pattern
```python
# schema.py - Type-safe input/output models
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator

class ToolInput(BaseModel):
    """Input schema for service tool."""
    
    operation: str = Field(..., description="Operation to perform")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Operation parameters")
    options: Optional[Dict[str, Any]] = Field(default=None, description="Additional options")
    
    @validator('operation')
    def validate_operation(cls, v):
        allowed_operations = ['create', 'read', 'update', 'delete', 'list']
        if v not in allowed_operations:
            raise ValueError(f"Operation must be one of: {allowed_operations}")
        return v

class ServiceResult(BaseModel):
    """Service operation result."""
    
    data: Any = Field(..., description="Result data")
    status: str = Field(..., description="Operation status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

class ToolOutput(BaseModel):
    """Tool execution output."""
    
    success: bool = Field(..., description="Whether operation succeeded")
    result: Optional[ServiceResult] = Field(default=None, description="Service result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution metadata")
```

## 🔌 Service Integration Patterns

### API Client Pattern
```python
# provider.py - Service provider implementation
import httpx
from typing import Dict, Any, Optional
from .interface import ServiceInterface
from .schema import ToolInput, ServiceResult

class ServiceProvider(ServiceInterface):
    """HTTP API service provider."""
    
    async def _initialize_client(self):
        """Initialize HTTP client with authentication."""
        
        self.base_url = self.config.get("base_url")
        api_key = self.config.get("api_key")
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AutomagikAgents/1.0"
        }
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0
        )
    
    async def perform_operation(self, input_data: ToolInput) -> ServiceResult:
        """Perform API operation."""
        
        endpoint = f"/api/v1/{input_data.operation}"
        
        response = await self.client.post(
            endpoint,
            json=input_data.parameters
        )
        
        response.raise_for_status()
        data = response.json()
        
        return ServiceResult(
            data=data,
            status=response.status_code,
            metadata={
                "endpoint": endpoint,
                "response_time": response.elapsed.total_seconds()
            }
        )
    
    async def health_check(self) -> bool:
        """Check API health."""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
```

### Authentication Patterns
```python
# Common authentication patterns for different services

# API Key Authentication
class APIKeyAuth:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def get_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

# OAuth2 Authentication  
class OAuth2Auth:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
    
    async def authenticate(self):
        """Get OAuth2 access token."""
        # Implementation for OAuth2 flow
        pass
    
    def get_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.access_token}"}

# Basic Authentication
class BasicAuth:
    def __init__(self, username: str, password: str):
        self.credentials = (username, password)
    
    def get_auth(self):
        return self.credentials
```

## 🔄 Agent Integration Patterns

### Tool Registration
```python
# __init__.py - Tool registration and exports
from .tool import ServiceTool
from .schema import ToolInput, ToolOutput

def create_service_tool(config: Dict[str, str]) -> ServiceTool:
    """Factory function to create tool instance."""
    return ServiceTool(config)

# Agent registration pattern
def register_with_agent(agent_context):
    """Register tool with agent."""
    
    config = agent_context.get("service_config", {})
    tool_instance = create_service_tool(config)
    
    async def service_tool_wrapper(**kwargs):
        """Wrapper function for agent tool system."""
        input_data = ToolInput(**kwargs)
        result = await tool_instance.execute(input_data)
        
        if result.success:
            return result.result.data
        else:
            return f"Error: {result.error}"
    
    return service_tool_wrapper

# Export for centralized tool discovery
__all__ = ["ServiceTool", "ToolInput", "ToolOutput", "create_service_tool"]
```

### Context-Aware Tool Wrapper
```python
# Integration with agent context system
from src.agents.common.context_aware_tool_wrapper import create_context_aware_tool

def create_contextual_service_tool(base_config: Dict[str, str]):
    """Create context-aware version of service tool."""
    
    def tool_factory(context: Dict[str, Any]):
        # Merge base config with context-specific config
        config = {**base_config, **context.get("service_overrides", {})}
        
        # Add context-specific parameters
        config["user_id"] = context.get("user_id")
        config["session_id"] = context.get("session_id")
        
        return ServiceTool(config)
    
    return create_context_aware_tool(tool_factory)
```

## 📊 Service-Specific Patterns

### Database Service Tools (Airtable, Notion)
```python
# Pattern for database-like services
class DatabaseServiceTool(ServiceTool):
    async def list_records(self, table: str, filters: Dict = None) -> List[Dict]:
        """List records from database service."""
        pass
    
    async def create_record(self, table: str, data: Dict) -> str:
        """Create new record and return ID."""
        pass
    
    async def update_record(self, table: str, record_id: str, data: Dict) -> bool:
        """Update existing record."""
        pass
    
    async def get_schema(self, table: str) -> Dict:
        """Get table schema information."""
        pass
```

### Communication Service Tools (Discord, Evolution, Gmail)
```python
# Pattern for communication services
class CommunicationServiceTool(ServiceTool):
    async def send_message(self, channel: str, content: str, **kwargs) -> str:
        """Send message and return message ID."""
        pass
    
    async def get_messages(self, channel: str, limit: int = 10) -> List[Dict]:
        """Get recent messages from channel."""
        pass
    
    async def create_channel(self, name: str, **kwargs) -> str:
        """Create new channel and return ID."""
        pass
    
    async def upload_file(self, channel: str, file_path: str) -> str:
        """Upload file and return URL."""
        pass
```

### Business Service Tools (BlackPearl, Omie)
```python
# Pattern for business/ERP services
class BusinessServiceTool(ServiceTool):
    async def get_customer(self, customer_id: str) -> Dict:
        """Get customer information."""
        pass
    
    async def create_order(self, customer_id: str, items: List[Dict]) -> str:
        """Create new order and return order ID."""
        pass
    
    async def get_inventory(self, product_id: str = None) -> List[Dict]:
        """Get inventory information."""
        pass
    
    async def update_status(self, entity_type: str, entity_id: str, status: str) -> bool:
        """Update entity status."""
        pass
```

## 🧪 Tool Testing Patterns

### Unit Testing
```python
# test_service_tool.py
import pytest
from unittest.mock import AsyncMock, patch
from src.tools.service.tool import ServiceTool
from src.tools.service.schema import ToolInput, ToolOutput

@pytest.fixture
def tool_config():
    return {
        "api_key": "test-key",
        "base_url": "https://api.test.com"
    }

@pytest.fixture
def service_tool(tool_config):
    return ServiceTool(tool_config)

@pytest.mark.asyncio
async def test_tool_execution_success(service_tool):
    """Test successful tool execution."""
    
    input_data = ToolInput(
        operation="create",
        parameters={"name": "test item", "value": 42}
    )
    
    with patch.object(service_tool.interface, 'perform_operation') as mock_operation:
        mock_operation.return_value = ServiceResult(
            data={"id": "123", "name": "test item"},
            status="created"
        )
        
        result = await service_tool.execute(input_data)
        
        assert result.success is True
        assert result.result.data["id"] == "123"
        assert result.error is None

@pytest.mark.asyncio  
async def test_tool_execution_error(service_tool):
    """Test tool execution with error."""
    
    input_data = ToolInput(
        operation="invalid",
        parameters={}
    )
    
    result = await service_tool.execute(input_data)
    
    assert result.success is False
    assert result.error is not None
    assert "Operation must be one of" in result.error
```

### Integration Testing
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_service_integration(tool_config):
    """Test actual service integration."""
    
    # Requires actual service credentials and connectivity
    tool = ServiceTool(tool_config)
    
    # Test health check
    health = await tool.interface.health_check()
    assert health is True
    
    # Test basic operation
    input_data = ToolInput(
        operation="list",
        parameters={"limit": 5}
    )
    
    result = await tool.execute(input_data)
    assert result.success is True
```

## 🔍 Tool Development Debugging

```bash
# Test tool in isolation
uv run python -c "
from src.tools.service.tool import ServiceTool
import asyncio

async def test():
    config = {'api_key': 'test', 'base_url': 'https://api.example.com'}
    tool = ServiceTool(config)
    
    # Test health check
    health = await tool.interface.health_check()
    print(f'Health: {health}')

asyncio.run(test())
"

# Test tool schema validation
uv run python -c "
from src.tools.service.schema import ToolInput
try:
    input_data = ToolInput(operation='invalid', parameters={})
except Exception as e:
    print(f'Validation error: {e}')
"

# Enable tool debug logging
export TOOL_DEBUG=true
export AUTOMAGIK_LOG_LEVEL=DEBUG
```

## ⚠️ Tool Development Guidelines

### Security Practices
- Never log sensitive data (API keys, tokens, personal info)
- Validate all inputs with Pydantic schemas
- Use proper authentication methods for each service
- Implement rate limiting and request throttling
- Handle sensitive responses appropriately

### Error Handling
- Provide meaningful error messages to users
- Log detailed errors for debugging (without sensitive data)
- Implement retry logic for transient failures
- Handle network timeouts gracefully
- Return structured error responses

### Performance Considerations
- Use async patterns throughout
- Implement connection pooling for HTTP clients
- Cache authentication tokens when possible
- Set appropriate timeouts for operations
- Monitor API rate limits and usage

### Testing Requirements
- Unit tests for all tool operations
- Integration tests for actual service connectivity
- Mock external services in unit tests
- Test error scenarios and edge cases
- Validate schema compliance

This context focuses specifically on tool development patterns and should be used alongside the global development rules in the root CLAUDE.md.