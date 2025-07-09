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

        # Check for API key in multiple formats
        api_key = request.headers.get(API_KEY_NAME) or request.query_params.get(API_KEY_NAME)
        
        # Also check for Bearer token (from Swagger UI authorize button)
        if api_key is None:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                api_key = auth_header[7:]  # Remove "Bearer " prefix
        
        if api_key is None:
            return JSONResponse(status_code=401, content={"detail": "API key is missing. Provide via x-api-key header, query parameter, or Authorization: Bearer header"})
        if api_key != settings.AUTOMAGIK_API_KEY:
            return JSONResponse(status_code=401, content={"detail": "Invalid API Key"})
            
        return await call_next(request)

async def get_api_key(x_api_key: Optional[str] = Header(None, alias=API_KEY_NAME)):
    """Legacy dependency function for backward compatibility.
    
    Note: This function exposes x-api-key parameter in Swagger docs.
    Use verify_api_key() for routes that should only show Bearer auth.
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

async def verify_api_key():
    """Dependency to validate API key without exposing parameters in Swagger docs.
    
    This function relies on the APIKeyMiddleware to handle authentication,
    so it only validates that authentication has already passed.
    
    Returns:
        True if authentication passed (middleware ensures this)
    """
    # Since the middleware already validated the API key,
    # if we reach this point, authentication has passed
    return True 