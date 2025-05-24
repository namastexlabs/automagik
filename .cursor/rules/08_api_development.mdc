---
description: "FastAPI endpoint development, authentication, and optimization patterns"
globs:
  - "**/src/api/**/*.py"
  - "**/*api*.py"
  - "**/*router*.py"
  - "**/*endpoint*.py"
  - "**/src/main.py"
  - "**/src/auth.py"
alwaysApply: false
priority: 8
---

# API Development Guide

This guide covers everything you need to know about developing, extending, and maintaining the FastAPI-based API in Automagik Agents.

## 🌐 API Architecture Overview

### FastAPI Application Structure
```
src/api/
├── routes/                    # Endpoint handlers
│   ├── __init__.py           # Router registration
│   ├── agent_routes.py       # Agent execution endpoints
│   ├── session_routes.py     # Session management
│   ├── message_routes.py     # Message history
│   ├── prompt_routes.py      # Prompt management
│   └── user_routes.py        # User management
├── models.py                 # Pydantic schemas
├── middleware.py             # HTTP middleware
├── memory_models.py          # Memory-specific schemas
├── memory_routes.py          # Memory API endpoints
└── docs.py                   # API documentation
```

### Core Features
- **Automatic Authentication**: API key middleware
- **Agent Integration**: Direct agent execution endpoints
- **Memory Management**: Persistent conversation APIs
- **Auto-documentation**: OpenAPI/Swagger integration
- **Error Handling**: Structured error responses
- **CORS Support**: Cross-origin request handling

## 🔐 Authentication System

### API Key Middleware
All `/api/v1/` endpoints are automatically protected:

```python
# src/auth.py
class APIKeyMiddleware:
    async def __call__(self, request: Request, call_next):
        if request.url.path.startswith("/api/v1/"):
            api_key = request.headers.get("X-API-Key")
            if not api_key or not await self.verify_api_key(api_key):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or missing API key"}
                )
        
        return await call_next(request)
```

### API Key Management
```python
# Generate API keys
import secrets
api_key = secrets.token_urlsafe(32)

# Store in database
INSERT INTO api_keys (name, key_hash, is_active) 
VALUES ('development', $1, true);
```

### Using API Keys
```bash
# All authenticated requests require X-API-Key header
curl -X POST http://localhost:8000/api/v1/agent/simple_agent/run \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"message_content": "Hello", "session_name": "test"}'
```

## 🤖 Agent API Endpoints

### Core Agent Routes
```python
# src/api/routes/agent_routes.py
router = APIRouter(prefix="/agent", tags=["Agents"])

@router.get("/", response_model=List[AgentInfo])
async def list_agents():
    """List all available agents."""
    return AgentFactory.list_available_agents()

@router.get("/{agent_name}/info", response_model=AgentInfo)  
async def get_agent_info(agent_name: str):
    """Get information about a specific agent."""
    agent = AgentFactory.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.get_info()

@router.post("/{agent_name}/run", response_model=AgentResponse)
async def run_agent(agent_name: str, request: AgentRequest):
    """Execute agent with message."""
    agent = AgentFactory.get_agent(agent_name) 
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    try:
        response = await agent.process_message(
            message=request.message_content,
            session_name=request.session_name
        )
        return AgentResponse(response=response, status="success")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Pydantic Models
```python
# src/api/models.py
class AgentRequest(BaseModel):
    message_content: str = Field(..., description="Message to send to agent")
    session_name: str = Field(default="default", description="Session identifier")
    user_id: Optional[int] = Field(None, description="User ID for tracking")

class AgentResponse(BaseModel):
    response: str = Field(..., description="Agent's response")
    status: str = Field(..., description="Response status")
    session_name: str = Field(..., description="Session identifier")
    timestamp: datetime = Field(default_factory=datetime.now)

class AgentInfo(BaseModel):
    name: str = Field(..., description="Agent name")
    description: str = Field(..., description="Agent description")
    available_tools: List[str] = Field(..., description="Available tools")
    status: str = Field(..., description="Agent status")
```

## 💾 Memory API Integration

### Memory Endpoints
```python
# Automatic memory endpoints for each agent
GET    /api/v1/agent/{agent_name}/memory           # List memories
POST   /api/v1/agent/{agent_name}/memory           # Add memory
GET    /api/v1/agent/{agent_name}/memory/{name}    # Get specific memory
PUT    /api/v1/agent/{agent_name}/memory/{name}    # Update memory
DELETE /api/v1/agent/{agent_name}/memory/{name}    # Delete memory
```

### Memory Models
```python
# src/api/memory_models.py
class MemoryRequest(BaseModel):
    name: str = Field(..., description="Memory variable name")
    content: str = Field(..., description="Memory content")
    session_name: str = Field(default="default", description="Session identifier")

class MemoryResponse(BaseModel):
    name: str
    content: str  
    session_name: str
    created_at: datetime
    updated_at: datetime

class MemoryListResponse(BaseModel):
    memories: List[MemoryResponse]
    count: int
    session_name: str
```

### Memory Route Implementation
```python
# src/api/memory_routes.py
@router.post("/agent/{agent_name}/memory", response_model=MemoryResponse)
async def add_memory(
    agent_name: str,
    request: MemoryRequest,
    api_key: str = Depends(verify_api_key)
):
    """Add memory variable for agent."""
    agent = AgentFactory.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    await agent.memory_manager.add_memory(
        agent_id=agent.agent_id,
        name=request.name,
        content=request.content,
        session_name=request.session_name
    )
    
    return MemoryResponse(
        name=request.name,
        content=request.content,
        session_name=request.session_name,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
```

## 📝 Session Management

### Session Endpoints
```python
# src/api/routes/session_routes.py
@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions(
    user_id: Optional[int] = None,
    agent_name: Optional[str] = None
):
    """List user sessions."""
    # Implementation

@router.get("/sessions/{session_name}", response_model=SessionDetail)
async def get_session(session_name: str):
    """Get session details with message history."""
    # Implementation

@router.delete("/sessions/{session_name}")
async def delete_session(session_name: str):
    """Delete session and all associated data."""
    # Implementation
```

### Session Models
```python
class SessionInfo(BaseModel):
    session_name: str
    agent_name: str
    user_id: Optional[int]
    message_count: int
    last_activity: datetime
    created_at: datetime

class SessionDetail(BaseModel):
    session_info: SessionInfo
    messages: List[MessageInfo]
    memories: List[MemoryResponse]
```

## 🔧 Custom Endpoint Development

### Adding New Routes
1. **Create Route File**: Add to `src/api/routes/`
2. **Define Models**: Add Pydantic schemas to `src/api/models.py`
3. **Register Router**: Import in `src/api/routes/__init__.py`
4. **Test Endpoint**: Verify in auto-generated docs

### Example Custom Route
```python
# src/api/routes/custom_routes.py
from fastapi import APIRouter, HTTPException, Depends
from src.api.models import CustomRequest, CustomResponse
from src.auth import verify_api_key

router = APIRouter(prefix="/custom", tags=["Custom"])

@router.post("/action", response_model=CustomResponse)
async def custom_action(
    request: CustomRequest,
    api_key: str = Depends(verify_api_key)
):
    """Custom business logic endpoint."""
    try:
        # Your custom logic here
        result = await process_custom_request(request)
        
        return CustomResponse(
            success=True,
            data=result,
            message="Action completed successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_custom_status():
    """Public endpoint (no auth required)."""
    return {"status": "operational", "timestamp": datetime.now()}
```

### Model Definitions
```python
# src/api/models.py
class CustomRequest(BaseModel):
    action: str = Field(..., description="Action to perform")
    parameters: Dict[str, Any] = Field(default={}, description="Action parameters")
    session_name: Optional[str] = Field(None, description="Session context")

class CustomResponse(BaseModel):
    success: bool = Field(..., description="Operation success status")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    message: str = Field(..., description="Human-readable message")
    timestamp: datetime = Field(default_factory=datetime.now)
```

### Router Registration
```python
# src/api/routes/__init__.py
from fastapi import APIRouter
from .agent_routes import router as agent_router
from .session_routes import router as session_router
from .custom_routes import router as custom_router

main_router = APIRouter()

main_router.include_router(agent_router)
main_router.include_router(session_router)
main_router.include_router(custom_router)  # Add your custom router
```

## 🎛️ Middleware Development

### Custom Middleware
```python
# src/api/middleware.py
class CustomMiddleware:
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)
            
            # Pre-processing
            start_time = time.time()
            
            # Process request
            response = await self.app(scope, receive, send)
            
            # Post-processing
            process_time = time.time() - start_time
            logger.info(f"Request processed in {process_time:.4f}s")
            
            return response
        
        return await self.app(scope, receive, send)

# Add to main.py
app.add_middleware(CustomMiddleware)
```

### Request/Response Logging
```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all API requests and responses."""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.info(f"Response: {response.status_code} ({process_time:.4f}s)")
    
    return response
```

## 📊 Error Handling

### Structured Error Responses
```python
# src/api/models.py
class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional details")
    timestamp: datetime = Field(default_factory=datetime.now)

# Custom exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTP_ERROR",
            message=exc.detail,
            details={"status_code": exc.status_code}
        ).dict()
    )
```

### Custom Exceptions
```python
# src/api/exceptions.py
class AgentNotFoundError(HTTPException):
    def __init__(self, agent_name: str):
        super().__init__(
            status_code=404,
            detail=f"Agent '{agent_name}' not found"
        )

class MemoryNotFoundError(HTTPException):
    def __init__(self, memory_name: str):
        super().__init__(
            status_code=404,
            detail=f"Memory '{memory_name}' not found"
        )

class InvalidSessionError(HTTPException):
    def __init__(self, session_name: str):
        super().__init__(
            status_code=400,
            detail=f"Invalid session '{session_name}'"
        )
```

## 📚 API Documentation

### OpenAPI Configuration
```python
# src/main.py
app = FastAPI(
    title="Automagik Agents API",
    description="Production-ready AI agent framework API",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
    openapi_tags=[
        {
            "name": "Agents",
            "description": "Agent execution and management",
        },
        {
            "name": "Sessions", 
            "description": "Conversation session management",
        },
        {
            "name": "Memory",
            "description": "Agent memory and context management",
        }
    ]
)
```

### Enhanced Documentation
```python
@router.post(
    "/{agent_name}/run",
    response_model=AgentResponse,
    summary="Execute Agent",
    description="Send a message to an agent and get a response",
    responses={
        200: {"description": "Successful agent execution"},
        404: {"description": "Agent not found"},
        500: {"description": "Agent execution error"}
    }
)
async def run_agent(
    agent_name: str = Path(..., description="Name of the agent to execute"),
    request: AgentRequest = Body(..., description="Message and session information")
):
    """
    Execute an agent with a message and return the response.
    
    - **agent_name**: The name of the agent to execute
    - **message_content**: The message to send to the agent
    - **session_name**: Session identifier for conversation context
    - **user_id**: Optional user ID for tracking
    """
    # Implementation
```

## 🧪 API Testing

### Test Structure
```python
# tests/test_api/test_agent_endpoints.py
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_list_agents():
    response = client.get("/api/v1/agent/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

def test_run_agent():
    response = client.post(
        "/api/v1/agent/simple_agent/run",
        json={
            "message_content": "Hello",
            "session_name": "test_session"
        },
        headers={"X-API-Key": "test_key"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "status" in data

def test_agent_not_found():
    response = client.post(
        "/api/v1/agent/nonexistent_agent/run",
        json={"message_content": "Hello"},
        headers={"X-API-Key": "test_key"}
    )
    assert response.status_code == 404
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_agent_memory_integration():
    """Test agent execution with memory persistence."""
    # Add memory
    memory_response = client.post(
        "/api/v1/agent/simple_agent/memory",
        json={
            "name": "user_preference",
            "content": "Likes detailed explanations",
            "session_name": "integration_test"
        },
        headers={"X-API-Key": "test_key"}
    )
    assert memory_response.status_code == 200
    
    # Run agent - should use memory
    agent_response = client.post(
        "/api/v1/agent/simple_agent/run", 
        json={
            "message_content": "Explain Python",
            "session_name": "integration_test"
        },
        headers={"X-API-Key": "test_key"}
    )
    assert agent_response.status_code == 200
```

## 🚀 Performance & Scaling

### Async Best Practices
```python
# Good: Async all the way down
@router.post("/agent/{agent_name}/run")
async def run_agent(agent_name: str, request: AgentRequest):
    agent = await AgentFactory.get_agent_async(agent_name)
    response = await agent.process_message_async(request.message_content)
    return AgentResponse(response=response)

# Avoid: Blocking operations in async context
@router.post("/agent/{agent_name}/run")
async def run_agent_bad(agent_name: str, request: AgentRequest):
    agent = AgentFactory.get_agent(agent_name)  # Blocking!
    response = agent.process_message(request.message_content)  # Blocking!
    return AgentResponse(response=response)
```

### Connection Pooling
```python
# Database connection management
from src.db.connection import get_connection_pool

@router.get("/sessions/{session_name}")
async def get_session(session_name: str):
    pool = get_connection_pool()
    async with pool.acquire() as conn:
        # Use connection
        result = await conn.fetch("SELECT * FROM sessions WHERE name = $1", session_name)
    return result
```

### Caching
```python
from functools import lru_cache
import redis

# In-memory caching
@lru_cache(maxsize=100)
def get_agent_info(agent_name: str):
    """Cache agent information."""
    agent = AgentFactory.get_agent(agent_name)
    return agent.get_info() if agent else None

# Redis caching
redis_client = redis.Redis(host='localhost', port=6379, db=0)

async def get_cached_response(key: str):
    """Get cached response if available."""
    cached = redis_client.get(key)
    return json.loads(cached) if cached else None

async def cache_response(key: str, response: dict, ttl: int = 300):
    """Cache response for specified TTL."""
    redis_client.setex(key, ttl, json.dumps(response))
```

## 🔐 Security Best Practices

### Input Validation
```python
class SecureAgentRequest(BaseModel):
    message_content: str = Field(
        ..., 
        min_length=1, 
        max_length=10000,
        description="Message content (1-10000 characters)"
    )
    session_name: str = Field(
        default="default",
        regex=r"^[a-zA-Z0-9_-]+$",
        max_length=50,
        description="Session name (alphanumeric, underscore, hyphen only)"
    )
    
    @validator('message_content')
    def validate_message_content(cls, v):
        # Check for malicious content
        forbidden_patterns = ['<script', '<?php', 'SELECT * FROM']
        if any(pattern in v.lower() for pattern in forbidden_patterns):
            raise ValueError('Invalid message content')
        return v
```

### Rate Limiting
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/agent/{agent_name}/run")
@limiter.limit("10/minute")
async def run_agent(request: Request, agent_name: str, req: AgentRequest):
    # Implementation with rate limiting
    pass
```

---

**Remember**: The API is automatically generated and documented. Focus on business logic and agent integration rather than reimplementing core infrastructure.
