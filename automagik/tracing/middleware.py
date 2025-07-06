"""FastAPI middleware for tracing HTTP requests."""

import time
import logging
from typing import Callable, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from automagik.tracing import get_tracing_manager
from automagik.tracing.performance import SamplingDecision

logger = logging.getLogger(__name__)


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware to trace HTTP requests with intelligent sampling."""
    
    def __init__(self, app):
        super().__init__(app)
        self.tracing = get_tracing_manager()
        self.sampler = self.tracing.observability.sampler if self.tracing.observability else None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with tracing."""
        # Skip ALL tracing for health checks and docs
        skip_paths = ["/health", "/", "/api/v1/docs", "/api/v1/openapi.json", "/health/workflow-services"]
        if request.url.path in skip_paths:
            return await call_next(request)
        
        start_time = time.time()
        status_code = 500
        error_type = None
        
        # Determine if we should trace this request
        sampling_decision = self._should_sample(request)
        should_sample = sampling_decision.should_sample if sampling_decision else False
        
        # Start observability trace if sampled
        trace_ctx = None
        if should_sample and self.tracing.observability:
            trace_ctx = self.tracing.observability.trace_http_request(
                method=request.method,
                path=request.url.path,
                headers=dict(request.headers)
            )
            trace_ctx.__enter__()
            
            # Log sampling decision
            if hasattr(trace_ctx, 'attributes'):
                trace_ctx.attributes["sampling.reason"] = sampling_decision.reason
                trace_ctx.attributes["sampling.rate"] = sampling_decision.sample_rate
        
        try:
            # Process the request
            response = await call_next(request)
            status_code = response.status_code
            
            # Log response if sampled (skip if provider doesn't have log_http_response)
            if should_sample and self.tracing.observability:
                for provider in self.tracing.observability.providers.values():
                    if hasattr(provider, 'log_http_response'):
                        try:
                            provider.log_http_response(
                                status_code=status_code,
                                response_headers=dict(response.headers) if hasattr(response, 'headers') else {}
                            )
                        except Exception as e:
                            logger.debug(f"Failed to log response: {e}")
            
            return response
            
        except Exception as e:
            error_type = type(e).__name__
            
            # Log error to observability if sampled
            if should_sample and self.tracing.observability:
                for provider in self.tracing.observability.providers.values():
                    try:
                        provider.log_error(e, {
                            "method": request.method,
                            "path": request.url.path
                        })
                    except Exception as log_error:
                        logger.debug(f"Failed to log error: {log_error}")
            
            # Always track errors in telemetry
            if self.tracing.telemetry:
                try:
                    self.tracing.telemetry.track_error(
                        error_type=error_type,
                        component=f"http.{request.method.lower()}"
                    )
                except Exception as tel_error:
                    logger.debug(f"Failed to track error: {tel_error}")
            
            raise
            
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Close observability trace if it was opened
            if trace_ctx:
                try:
                    trace_ctx.__exit__(None, None, None)
                except Exception as e:
                    logger.debug(f"Failed to close trace: {e}")
            
            # Always send anonymous telemetry
            if self.tracing.telemetry:
                try:
                    self.tracing.telemetry.track_http_request(
                        method=request.method,
                        path=self._anonymize_path(request.url.path),
                        status_code=status_code,
                        duration_ms=duration_ms
                    )
                except Exception as tel_error:
                    logger.debug(f"Failed to track request: {tel_error}")
                
                # Track API endpoint usage
                if request.url.path.startswith("/api/v1/"):
                    try:
                        endpoint = self._get_endpoint_name(request.method, request.url.path)
                        self.tracing.telemetry.track_feature_usage(
                            endpoint,
                            category="api_endpoint"
                        )
                    except Exception as feat_error:
                        logger.debug(f"Failed to track endpoint usage: {feat_error}")
    
    def _should_sample(self, request: Request) -> SamplingDecision:
        """Determine if this request should be sampled."""
        if not self.sampler:
            return SamplingDecision(should_sample=False, reason="no_sampler")
        
        # Check if this is an error path
        is_error = request.url.path.startswith("/error") or request.url.path.endswith("/error")
        
        return self.sampler.should_sample(
            trace_type=f"http.{request.method.lower()}",
            duration_ms=None,  # Not known yet
            is_error=is_error,
            attributes={
                "path": request.url.path,
                "method": request.method,
                "user_agent": request.headers.get("user-agent", "")
            }
        )
    
    def _anonymize_path(self, path: str) -> str:
        """Anonymize path by replacing IDs with placeholders."""
        import re
        
        # Replace UUIDs
        path = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '<uuid>',
            path
        )
        
        # Replace numeric IDs
        path = re.sub(r'/\d+(?:/|$)', '/<id>/', path)
        
        return path
    
    def _get_endpoint_name(self, method: str, path: str) -> str:
        """Get a normalized endpoint name for tracking."""
        # Remove /api/v1 prefix
        if path.startswith("/api/v1/"):
            path = path[8:]
        
        # Anonymize the path
        path = self._anonymize_path(path)
        
        return f"{method.lower()}.{path.strip('/')}"