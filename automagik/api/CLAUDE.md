# CLAUDE.md

This file provides API development context for Claude Code working in this directory.

## API Development Context

This directory contains the FastAPI-based REST API for Automagik Agents. When working here, you're developing endpoints, middleware, authentication, and API models that power the platform's HTTP interface.

## 🌐 API Architecture Overview

### Core Components
- **Routes** (`routes/`) - Endpoint definitions organized by feature
- **Controllers** (`controllers/`) - Business logic layer
- **Models** (`models.py`) - Pydantic models for request/response
- **Middleware** (`middleware.py`) - Cross-cutting concerns (auth, logging, CORS)
- **Docs** (`docs.py`) - API documentation configuration

### API Structure
```
/api/v1/
├── agents/           # Agent management endpoints
├── users/            # User account management  
├── sessions/         # Conversation sessions
├── messages/         # Message handling
├── memories/         # Agent memory operations
├── tools/            # Tool discovery and execution
├── mcp/              # MCP server management
├── claude_code/      # Workflow orchestration
└── analytics/        # Usage analytics
```

## 🛠️ API Development Patterns

### FastAPI Route Pattern
```python
# routes/feature_routes.py
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from ..models import FeatureRequest, FeatureResponse, ErrorResponse
from ..middleware import verify_api_key
from ..controllers.feature_controller import FeatureController

router = APIRouter(prefix="/api/v1/features", tags=["features"])

@router.post(
    "/",
    response_model=FeatureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new feature",
    description="Create a new feature with the provided configuration"
)
async def create_feature(
    request: FeatureRequest,
    api_key: str = Depends(verify_api_key)
) -> FeatureResponse:
    """Create a new feature."""
    
    try:
        controller = FeatureController()
        result = await controller.create_feature(request)
        
        return FeatureResponse(
            success=True,
            data=result,
            message="Feature created successfully"
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )

@router.get(
    "/{feature_id}",
    response_model=FeatureResponse,
    summary="Get feature by ID"
)
async def get_feature(
    feature_id: str,
    api_key: str = Depends(verify_api_key)
) -> FeatureResponse:
    """Get feature by ID."""
    
    controller = FeatureController()
    feature = await controller.get_feature(feature_id)
    
    if not feature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feature not found"
        )
    
    return FeatureResponse(
        success=True,
        data=feature,
        message="Feature retrieved successfully"
    )

@router.get(
    "/",
    response_model=List[FeatureResponse],
    summary="List features"
)
async def list_features(
    limit: int = 20,
    offset: int = 0,
    api_key: str = Depends(verify_api_key)
) -> List[FeatureResponse]:
    """List features with pagination."""
    
    controller = FeatureController()
    features = await controller.list_features(limit=limit, offset=offset)
    
    return [
        FeatureResponse(success=True, data=feature, message="Success")
        for feature in features
    ]
```

### Controller Pattern
```python
# controllers/feature_controller.py
from typing import List, Optional, Dict, Any
from src.db import create_feature, get_feature, list_features
from src.db.models import Feature
from ..models import FeatureRequest
import src.utils.logging as log

class FeatureController:
    """Business logic for feature operations."""
    
    async def create_feature(self, request: FeatureRequest) -> Dict[str, Any]:
        """Create new feature with validation."""
        
        # Validate request data
        if not request.name or len(request.name) < 3:
            raise ValueError("Feature name must be at least 3 characters")
        
        # Check for duplicates
        existing = await self.get_feature_by_name(request.name)
        if existing:
            raise ValueError(f"Feature with name '{request.name}' already exists")
        
        # Create feature model
        feature = Feature(
            name=request.name,
            description=request.description,
            config=request.config or {},
            metadata=request.metadata or {}
        )
        
        # Save to database
        feature_id = create_feature(feature)
        
        # Log creation
        log.info(f"Created feature: {request.name} (ID: {feature_id})")
        
        # Return created feature data
        return {
            "id": feature_id,
            "name": feature.name,
            "description": feature.description,
            "config": feature.config,
            "metadata": feature.metadata,
            "created_at": feature.created_at
        }
    
    async def get_feature(self, feature_id: str) -> Optional[Dict[str, Any]]:
        """Get feature by ID."""
        
        feature = get_feature(feature_id)
        if not feature:
            return None
        
        return {
            "id": feature.id,
            "name": feature.name,
            "description": feature.description,
            "config": feature.config,
            "metadata": feature.metadata,
            "created_at": feature.created_at,
            "updated_at": feature.updated_at
        }
    
    async def list_features(
        self,
        limit: int = 20,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """List features with pagination and filtering."""
        
        features, total_count = list_features(
            limit=limit,
            offset=offset,
            filters=filters or {}
        )
        
        return [
            {
                "id": feature.id,
                "name": feature.name,
                "description": feature.description,
                "config": feature.config,
                "metadata": {
                    **feature.metadata,
                    "total_count": total_count
                }
            }
            for feature in features
        ]
```

### API Models Pattern
```python
# models.py - Pydantic models for API
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime

class FeatureRequest(BaseModel):
    """Request model for feature creation."""
    
    name: str = Field(..., min_length=3, max_length=100, description="Feature name")
    description: Optional[str] = Field(None, max_length=500, description="Feature description")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Feature configuration")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    
    @validator('name')
    def validate_name(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Name must contain only alphanumeric characters, hyphens, and underscores")
        return v.lower()

class FeatureResponse(BaseModel):
    """Response model for feature operations."""
    
    success: bool = Field(..., description="Whether operation succeeded")
    data: Optional[Dict[str, Any]] = Field(None, description="Feature data")
    message: str = Field(..., description="Response message")
    errors: Optional[List[str]] = Field(None, description="Error details")

class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    success: bool = Field(False, description="Always false for errors")
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")

class PaginationParams(BaseModel):
    """Standard pagination parameters."""
    
    limit: int = Field(20, ge=1, le=100, description="Maximum number of items to return")
    offset: int = Field(0, ge=0, description="Number of items to skip")

class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""
    
    items: List[Any] = Field(..., description="Response items")
    total: int = Field(..., description="Total number of items")
    limit: int = Field(..., description="Items per page")
    offset: int = Field(..., description="Items skipped")
    has_more: bool = Field(..., description="Whether more items are available")
```

## 🔐 Authentication & Security Patterns

### API Key Authentication
```python
# middleware.py - Authentication middleware
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import src.utils.logging as log

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """Verify API key from Authorization header."""
    
    api_key = credentials.credentials
    
    # Validate API key format
    if not api_key or len(api_key) < 20:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format"
        )
    
    # Check API key against database/config
    is_valid = await validate_api_key(api_key)
    if not is_valid:
        log.warning(f"Invalid API key attempted: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return api_key

async def validate_api_key(api_key: str) -> bool:
    """Validate API key against stored keys."""
    
    # Check against environment variable (development)
    from src.config import get_settings
    settings = get_settings()
    
    if api_key == settings.api_key:
        return True
    
    # Check against database (production)
    # Implementation for database-stored API keys
    
    return False

# Optional dependency for endpoints that don't require auth
async def optional_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[str]:
    """Optional API key verification."""
    
    if not credentials:
        return None
    
    try:
        return await verify_api_key(credentials)
    except HTTPException:
        return None
```

### CORS and Security Headers
```python
# middleware.py - Security middleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

def setup_security_middleware(app: FastAPI):
    """Configure security middleware."""
    
    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://app.automagik.dev", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )
    
    # Trusted host middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["api.automagik.dev", "localhost", "127.0.0.1"]
    )
    
    # Custom security headers
    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        return response
```

## 📊 Error Handling Patterns

### Global Exception Handler
```python
# middleware.py - Global exception handling
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import ValidationError
import traceback
import src.utils.logging as log

def setup_exception_handlers(app: FastAPI):
    """Configure global exception handlers."""
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions."""
        
        log.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
        
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": exc.detail,
                "status_code": exc.status_code
            }
        )
    
    @app.exception_handler(ValidationError)
    async def validation_exception_handler(request: Request, exc: ValidationError):
        """Handle Pydantic validation errors."""
        
        log.warning(f"Validation error: {exc.errors()}")
        
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": "Validation error",
                "detail": exc.errors()
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Handle unexpected exceptions."""
        
        log.error(f"Unexpected error: {traceback.format_exc()}")
        
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error",
                "detail": "An unexpected error occurred"
            }
        )
```

### Custom Exception Classes
```python
# exceptions.py - Custom API exceptions
class APIException(Exception):
    """Base API exception."""
    
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class ValidationException(APIException):
    """Validation error exception."""
    
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, 400)

class NotFoundError(APIException):
    """Resource not found exception."""
    
    def __init__(self, resource: str, identifier: str):
        message = f"{resource} not found: {identifier}"
        super().__init__(message, 404)

class DuplicateError(APIException):
    """Duplicate resource exception."""
    
    def __init__(self, resource: str, field: str, value: str):
        message = f"{resource} with {field} '{value}' already exists"
        super().__init__(message, 409)
```

## 🔄 Async Patterns for API

### Database Operations
```python
# controllers/base_controller.py - Async database patterns
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
import src.utils.logging as log

class BaseController:
    """Base controller with common async patterns."""
    
    @asynccontextmanager
    async def database_transaction(self):
        """Context manager for database transactions."""
        
        transaction = None
        try:
            # Start transaction
            transaction = await self.db.begin()
            yield transaction
            await transaction.commit()
        except Exception as e:
            if transaction:
                await transaction.rollback()
            log.error(f"Database transaction failed: {e}")
            raise
    
    async def safe_execute(self, operation, *args, **kwargs):
        """Execute database operation with error handling."""
        
        try:
            return await operation(*args, **kwargs)
        except Exception as e:
            log.error(f"Database operation failed: {e}")
            raise APIException(f"Database operation failed: {str(e)}")
    
    async def paginated_query(
        self,
        query_func,
        limit: int = 20,
        offset: int = 0,
        **filters
    ) -> Dict[str, Any]:
        """Execute paginated query with standard response format."""
        
        # Get total count
        total = await self.safe_execute(query_func, count=True, **filters)
        
        # Get items
        items = await self.safe_execute(
            query_func,
            limit=limit,
            offset=offset,
            **filters
        )
        
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(items) < total
        }
```

### External Service Integration
```python
# controllers/service_controller.py - Async service patterns
import httpx
from typing import Dict, Any, Optional
import src.utils.logging as log

class ServiceController:
    """Controller for external service integration."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def call_external_service(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Call external service with error handling."""
        
        try:
            response = await self.client.request(
                method=method,
                url=url,
                json=data,
                headers=headers or {}
            )
            
            response.raise_for_status()
            return response.json()
            
        except httpx.TimeoutException:
            log.error(f"Service timeout: {url}")
            raise APIException("External service timeout", 504)
        except httpx.HTTPStatusError as e:
            log.error(f"Service error: {e.response.status_code} - {url}")
            raise APIException(f"External service error: {e.response.status_code}", 502)
        except Exception as e:
            log.error(f"Service call failed: {e}")
            raise APIException("External service unavailable", 503)
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
```

## 📋 API Documentation Patterns

### OpenAPI Configuration
```python
# docs.py - API documentation configuration
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

def configure_openapi(app: FastAPI):
    """Configure OpenAPI documentation."""
    
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title="Automagik Agents API",
            version="1.0.0",
            description="REST API for Automagik Agents platform",
            routes=app.routes,
        )
        
        # Add security scheme
        openapi_schema["components"]["securitySchemes"] = {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "API Key"
            }
        }
        
        # Add global security requirement
        openapi_schema["security"] = [{"BearerAuth": []}]
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
```

## 🧪 API Testing Patterns

### Integration Testing
```python
# test_api.py - API testing patterns
import pytest
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-api-key"}

def test_create_feature(auth_headers):
    """Test feature creation endpoint."""
    
    feature_data = {
        "name": "test-feature",
        "description": "Test feature description",
        "config": {"enabled": True}
    }
    
    response = client.post(
        "/api/v1/features/",
        json=feature_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["data"]["name"] == "test-feature"

def test_get_feature_not_found(auth_headers):
    """Test feature not found scenario."""
    
    response = client.get(
        "/api/v1/features/nonexistent",
        headers=auth_headers
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False

def test_unauthorized_access():
    """Test unauthorized access."""
    
    response = client.get("/api/v1/features/")
    assert response.status_code == 401
```

## 🔍 API Debugging Techniques

```bash
# Enable API debug logging
export AUTOMAGIK_LOG_LEVEL=DEBUG
export API_DEBUG=true

# Test API endpoints
curl -H "Authorization: Bearer your-api-key" \
     -H "Content-Type: application/json" \
     http://localhost:8000/api/v1/features/

# Check API documentation
open http://localhost:8000/docs

# Test with different HTTP methods
curl -X POST \
     -H "Authorization: Bearer your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"name": "test", "description": "test feature"}' \
     http://localhost:8000/api/v1/features/
```

## ⚠️ API Development Guidelines

### Security Best Practices
- Always require authentication on `/api/v1/` endpoints
- Use HTTPS in production
- Validate all input data with Pydantic models
- Implement rate limiting for public endpoints
- Log security events and failed authentication attempts

### Performance Considerations
- Use async patterns throughout
- Implement request/response caching where appropriate
- Set appropriate timeouts for external service calls
- Use connection pooling for database operations
- Monitor API response times and error rates

### Error Handling
- Return consistent error response formats
- Provide meaningful error messages to users
- Log detailed errors for debugging (without sensitive data)
- Implement proper HTTP status codes
- Handle validation errors gracefully

### Documentation Standards
- Document all endpoints with clear descriptions
- Provide request/response examples
- Include error response documentation
- Keep OpenAPI schema up to date
- Use meaningful parameter descriptions

This context focuses specifically on API development patterns and should be used alongside the global development rules in the root CLAUDE.md.