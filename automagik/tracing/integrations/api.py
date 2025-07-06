"""API integration for telemetry tracking."""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from automagik.tracing import get_tracing_manager
from automagik.tracing.telemetry.cli_events import APIRequestEvent


class TelemetryMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for tracking API requests."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Track API request execution.
        
        Args:
            request: FastAPI request
            call_next: Next middleware/handler
            
        Returns:
            Response from handler
        """
        # Skip telemetry endpoints to avoid recursion
        if request.url.path.startswith("/telemetry"):
            return await call_next(request)
        
        tracing = get_tracing_manager()
        start_time = time.time()
        
        # Process request
        response = await call_next(request)
        
        # Track request
        duration_ms = (time.time() - start_time) * 1000
        
        if tracing.telemetry:
            # Only track API v1 endpoints
            if request.url.path.startswith("/api/v1/"):
                event = APIRequestEvent(
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    duration_ms=duration_ms,
                    anonymous_id=tracing.telemetry.anonymous_id,
                    session_id=tracing.telemetry.session_id
                )
                tracing.telemetry.track_event(event)
            
            # Track errors
            if response.status_code >= 400:
                tracing.telemetry.track_error(
                    error_type=f"HTTP_{response.status_code}",
                    component=f"api.{request.url.path}"
                )
        
        return response


def track_api_endpoint(endpoint_name: str):
    """Decorator for tracking specific API endpoints.
    
    Usage:
        @router.get("/agents")
        @track_api_endpoint("agent_list")
        async def list_agents():
            pass
    
    Args:
        endpoint_name: Name for telemetry tracking
    """
    def decorator(func: Callable) -> Callable:
        # For endpoints that need custom tracking beyond middleware
        # Implementation similar to CLI decorator
        return func
    
    return decorator