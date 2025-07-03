from fastapi import HTTPException, Request, Header
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Optional
from automagik.config import settings

API_KEY_NAME = "x-api-key"

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Skip auth for CORS preflight requests (OPTIONS)
        if request.method == "OPTIONS":
            return await call_next(request)
            
        # Skip auth for health check, root, and documentation endpoints
        no_auth_paths = [
            "/health",
            "/",
            "/api/v1/docs",
            "/api/v1/redoc",
            "/api/v1/openapi.json",
            "/api/v1/mcp/health"
        ]
        
        # Check if this path should bypass authentication
        if request.url.path in no_auth_paths:
            return await call_next(request)

        api_key = request.headers.get(API_KEY_NAME) or request.query_params.get(API_KEY_NAME)
        if api_key is None:
            return JSONResponse(status_code=401, content={"detail": "x-api-key is missing in headers or query parameters"})
        if api_key != settings.AUTOMAGIK_API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Invalid API Key"})
            
        return await call_next(request)

async def get_api_key(x_api_key: Optional[str] = Header(None, alias=API_KEY_NAME)):
    """Dependency to validate API key in FastAPI routes.
    
    Args:
        x_api_key: The API key provided in the request header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if x_api_key is None:
        raise HTTPException(
            status_code=401,
            detail="API key is missing"
        )
    
    if x_api_key != settings.AUTOMAGIK_API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    return x_api_key 