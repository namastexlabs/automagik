"""Decorators for adding tracing to functions and CLI commands."""

import time
import functools
import logging
from typing import Callable, Any, Optional, TypeVar, cast
import asyncio

from automagik.tracing import get_tracing_manager

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


def trace_cli_command(
    command_name: Optional[str] = None,
    track_args: bool = True
) -> Callable[[F], F]:
    """Decorator to add tracing to CLI commands.
    
    Args:
        command_name: Name of the command for tracking (defaults to function name)
        track_args: Whether to track command arguments
        
    Returns:
        Decorated function with tracing
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Get tracing manager
            tracing = get_tracing_manager()
            if not tracing:
                return func(*args, **kwargs)
            
            cmd_name = command_name or func.__name__
            start_time = time.time()
            success = False
            error_type = None
            
            try:
                # Run the command
                result = func(*args, **kwargs)
                success = True
                return result
                
            except Exception as e:
                error_type = type(e).__name__
                
                # Track error in telemetry
                if tracing.telemetry:
                    try:
                        tracing.telemetry.track_error(
                            error_type=error_type,
                            component=f"cli.{cmd_name}"
                        )
                    except Exception:
                        pass
                
                raise
                
            finally:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Track CLI command usage
                if tracing.telemetry:
                    try:
                        tracing.telemetry.track_cli_command(
                            command=cmd_name,
                            success=success,
                            duration_ms=duration_ms
                        )
                    except Exception:
                        pass
                    
                    # Track command arguments if enabled
                    if track_args and success:
                        try:
                            # Track specific features based on arguments
                            if 'agent' in kwargs:
                                tracing.telemetry.track_feature_usage(
                                    f"cli.agent.{kwargs['agent']}",
                                    category="cli_agent_usage"
                                )
                            
                            if 'multimodal_content' in kwargs and kwargs['multimodal_content']:
                                tracing.telemetry.track_feature_usage(
                                    "cli.multimodal",
                                    category="cli_feature"
                                )
                        except Exception:
                            pass
        
        return cast(F, wrapper)
    
    return decorator


def trace_async_cli_command(
    command_name: Optional[str] = None,
    track_args: bool = True
) -> Callable[[F], F]:
    """Decorator to add tracing to async CLI commands.
    
    Args:
        command_name: Name of the command for tracking (defaults to function name)
        track_args: Whether to track command arguments
        
    Returns:
        Decorated function with tracing
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # Get tracing manager
            tracing = get_tracing_manager()
            if not tracing:
                return await func(*args, **kwargs)
            
            cmd_name = command_name or func.__name__
            start_time = time.time()
            success = False
            error_type = None
            
            try:
                # Run the command
                result = await func(*args, **kwargs)
                success = True
                return result
                
            except Exception as e:
                error_type = type(e).__name__
                
                # Track error in telemetry
                if tracing.telemetry:
                    try:
                        tracing.telemetry.track_error(
                            error_type=error_type,
                            component=f"cli.{cmd_name}"
                        )
                    except Exception:
                        pass
                
                raise
                
            finally:
                # Calculate duration
                duration_ms = (time.time() - start_time) * 1000
                
                # Track CLI command usage
                if tracing.telemetry:
                    try:
                        tracing.telemetry.track_cli_command(
                            command=cmd_name,
                            success=success,
                            duration_ms=duration_ms
                        )
                    except Exception:
                        pass
                    
                    # Track command arguments if enabled
                    if track_args and success:
                        try:
                            # Track specific features based on arguments
                            if 'agent' in kwargs:
                                tracing.telemetry.track_feature_usage(
                                    f"cli.agent.{kwargs['agent']}",
                                    category="cli_agent_usage"
                                )
                            
                            if 'multimodal_content' in kwargs and kwargs['multimodal_content']:
                                tracing.telemetry.track_feature_usage(
                                    "cli.multimodal",
                                    category="cli_feature"
                                )
                        except Exception:
                            pass
        
        return cast(F, wrapper)
    
    return decorator


def trace_function(
    trace_name: Optional[str] = None,
    component: Optional[str] = None
) -> Callable[[F], F]:
    """General purpose tracing decorator for functions.
    
    Args:
        trace_name: Name for the trace (defaults to function name)
        component: Component name for categorization
        
    Returns:
        Decorated function with tracing
    """
    def decorator(func: F) -> F:
        # Check if it's an async function
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                # Get tracing manager
                tracing = get_tracing_manager()
                if not tracing:
                    return await func(*args, **kwargs)
                
                name = trace_name or func.__name__
                comp = component or "function"
                start_time = time.time()
                success = False
                error_type = None
                
                try:
                    result = await func(*args, **kwargs)
                    success = True
                    return result
                    
                except Exception as e:
                    error_type = type(e).__name__
                    
                    if tracing.telemetry:
                        try:
                            tracing.telemetry.track_error(
                                error_type=error_type,
                                component=f"{comp}.{name}"
                            )
                        except Exception:
                            pass
                    
                    raise
                    
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if tracing.telemetry:
                        try:
                            tracing.telemetry.track_custom_event(
                                event_name=f"{comp}.{name}",
                                properties={
                                    "success": success,
                                    "duration_ms": duration_ms
                                }
                            )
                        except Exception:
                            pass
            
            return cast(F, async_wrapper)
        else:
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                # Get tracing manager
                tracing = get_tracing_manager()
                if not tracing:
                    return func(*args, **kwargs)
                
                name = trace_name or func.__name__
                comp = component or "function"
                start_time = time.time()
                success = False
                error_type = None
                
                try:
                    result = func(*args, **kwargs)
                    success = True
                    return result
                    
                except Exception as e:
                    error_type = type(e).__name__
                    
                    if tracing.telemetry:
                        try:
                            tracing.telemetry.track_error(
                                error_type=error_type,
                                component=f"{comp}.{name}"
                            )
                        except Exception:
                            pass
                    
                    raise
                    
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if tracing.telemetry:
                        try:
                            tracing.telemetry.track_custom_event(
                                event_name=f"{comp}.{name}",
                                properties={
                                    "success": success,
                                    "duration_ms": duration_ms
                                }
                            )
                        except Exception:
                            pass
            
            return cast(F, sync_wrapper)
    
    return decorator