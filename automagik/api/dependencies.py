"""API dependencies."""
from typing import Optional
from fastapi import Security, HTTPException, status, Depends, Query
from fastapi.security import APIKeyHeader, APIKeyQuery
from .config import get_api_key
from ..core.database.session import get_async_session

# Define API key security schemes
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)
API_KEY_QUERY = APIKeyQuery(name="api_key", auto_error=False)

async def get_api_key_from_header(api_key_header: str = Security(API_KEY_HEADER)):
    return api_key_header

async def get_api_key_from_query(api_key_query: str = Security(API_KEY_QUERY)):
    return api_key_query

async def verify_api_key(
    api_key_header: str = Depends(get_api_key_from_header),
    api_key_query: str = Depends(get_api_key_from_query)
) -> str:
    """
    Verify the API key from the X-API-Key header or api_key query parameter.
    If AUTOMAGIK_API_KEY is not set, all requests are allowed.
    """
    # Use header by default, fall back to query parameter
    api_key = api_key_header or api_key_query
    
    configured_api_key = get_api_key()
    
    # If no API key is configured, allow all requests
    if not configured_api_key:
        # If a key is provided, return it; otherwise return "anonymous"
        return api_key if api_key else "anonymous"
    
    # If API key is configured but not provided in request
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    # If API key is configured and provided but doesn't match
    if api_key != configured_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    return api_key

# Use the FastAPI-compatible session dependency
get_session = get_async_session
