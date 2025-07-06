"""CLI-specific telemetry events matching automagik-spark format."""

from typing import Optional
from .events import TelemetryEvent, EventType
from dataclasses import dataclass


@dataclass
class CLICommandEvent(TelemetryEvent):
    """CLI command execution event."""
    
    def __init__(
        self,
        command: str,
        success: bool,
        duration_ms: float,
        **kwargs
    ):
        """Initialize CLI command event.
        
        Args:
            command: Command executed (e.g., "agent list", "session create")
            success: Whether command succeeded
            duration_ms: Execution time in milliseconds
            **kwargs: Additional event attributes
        """
        # Extract any command-specific metrics
        extra_attrs = {}
        
        # Common CLI command patterns
        if "list" in command:
            if "count" in kwargs:
                extra_attrs["event.item_count"] = kwargs.pop("count")
        elif "create" in command:
            if "resource_id" in kwargs:
                extra_attrs["event.resource_id"] = kwargs.pop("resource_id")
        
        super().__init__(
            event_type=EventType.API_REQUEST,  # Use API_REQUEST type for now
            attributes={
                "event.command": command,
                "event.success": success,
                "event.duration_ms": duration_ms,
                **extra_attrs
            },
            **kwargs
        )


@dataclass 
class APIRequestEvent(TelemetryEvent):
    """API request event matching automagik-spark format."""
    
    def __init__(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        duration_ms: float,
        **kwargs
    ):
        """Initialize API request event.
        
        Args:
            endpoint: API endpoint path
            method: HTTP method
            status_code: Response status code
            duration_ms: Request duration
            **kwargs: Additional attributes
        """
        super().__init__(
            event_type=EventType.API_REQUEST,
            attributes={
                "event.endpoint": endpoint,
                "event.method": method,
                "event.status_code": float(status_code),  # OTLP uses double
                "event.duration_ms": duration_ms
            },
            **kwargs
        )


@dataclass
class AgentExecutionEvent(TelemetryEvent):
    """Agent execution event for automagik-agents specific tracking."""
    
    def __init__(
        self,
        agent_name: str,
        framework: str,
        success: bool,
        duration_ms: float,
        has_multimodal: bool = False,
        token_count: Optional[int] = None,
        **kwargs
    ):
        """Initialize agent execution event.
        
        Args:
            agent_name: Name of the agent
            framework: Framework used (pydantic_ai, agno)
            success: Whether execution succeeded
            duration_ms: Execution duration
            has_multimodal: Whether multimodal content was processed
            token_count: Total tokens used (optional)
            **kwargs: Additional attributes
        """
        attrs = {
            "event.agent_name": agent_name,
            "event.framework": framework,
            "event.success": success,
            "event.duration_ms": duration_ms,
            "event.has_multimodal": has_multimodal
        }
        
        if token_count is not None:
            attrs["event.token_count"] = float(token_count)
        
        super().__init__(
            event_type=EventType.AGENT_RUN,
            attributes=attrs,
            **kwargs
        )