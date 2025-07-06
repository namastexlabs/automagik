"""CLI integration for telemetry tracking."""

import asyncio
import time
import functools
from typing import Callable, Any
import click

from automagik.tracing import get_tracing_manager
from automagik.tracing.telemetry.cli_events import CLICommandEvent


def track_cli_command(command_name: str):
    """Decorator to track CLI command execution.
    
    Usage:
        @click.command()
        @track_cli_command("agent list")
        def list_agents():
            # Command implementation
            pass
    
    Args:
        command_name: Name of the command for telemetry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            tracing = get_tracing_manager()
            start_time = time.time()
            success = False
            result = None
            
            try:
                result = func(*args, **kwargs)
                success = True
                return result
                
            except Exception as e:
                # Track error type
                if tracing.telemetry:
                    tracing.telemetry.track_error(
                        error_type=type(e).__name__,
                        component=f"cli.{command_name.replace(' ', '_')}"
                    )
                raise
                
            finally:
                # Track command execution
                duration_ms = (time.time() - start_time) * 1000
                
                if tracing.telemetry:
                    # Extract count from result if available
                    extra_kwargs = {}
                    if isinstance(result, (list, tuple)):
                        extra_kwargs["count"] = len(result)
                    elif isinstance(result, dict) and "count" in result:
                        extra_kwargs["count"] = result["count"]
                    
                    event = CLICommandEvent(
                        command=command_name,
                        success=success,
                        duration_ms=duration_ms,
                        anonymous_id=tracing.telemetry.anonymous_id,
                        session_id=tracing.telemetry.session_id,
                        **extra_kwargs
                    )
                    tracing.telemetry.track_event(event)
        
        # Handle async functions
        if asyncio.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                tracing = get_tracing_manager()
                start_time = time.time()
                success = False
                result = None
                
                try:
                    result = await func(*args, **kwargs)
                    success = True
                    return result
                    
                except Exception as e:
                    if tracing.telemetry:
                        tracing.telemetry.track_error(
                            error_type=type(e).__name__,
                            component=f"cli.{command_name.replace(' ', '_')}"
                        )
                    raise
                    
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    if tracing.telemetry:
                        event = CLICommandEvent(
                            command=command_name,
                            success=success,
                            duration_ms=duration_ms,
                            anonymous_id=tracing.telemetry.anonymous_id,
                            session_id=tracing.telemetry.session_id
                        )
                        tracing.telemetry.track_event(event)
            
            return async_wrapper
        
        return wrapper
    
    return decorator


# Convenience decorators for common commands
track_agent_list = track_cli_command("agent list")
track_agent_run = track_cli_command("agent run")
track_session_list = track_cli_command("session list")
track_session_create = track_cli_command("session create")