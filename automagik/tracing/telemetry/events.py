"""Telemetry event definitions for anonymous usage tracking."""

import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


class EventType(Enum):
    """Telemetry event types."""
    # Agent events
    AGENT_RUN = "agent.run"
    AGENT_ERROR = "agent.error"
    
    # Framework events
    FRAMEWORK_SELECTED = "framework.selected"
    
    # Tool events
    TOOL_EXECUTED = "tool.executed"
    
    # Workflow events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    
    # System events
    STARTUP = "system.startup"
    FEATURE_USED = "feature.used"
    
    # API events
    API_REQUEST = "api.request"
    API_ERROR = "api.error"


@dataclass
class TelemetryEvent:
    """Base telemetry event with privacy-first design."""
    
    event_type: EventType
    timestamp: float = field(default_factory=time.time)
    anonymous_id: str = ""
    session_id: str = ""
    
    # High-level attributes only (no actual content)
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "anonymous_id": self.anonymous_id,
            "session_id": self.session_id,
            "attributes": self._sanitize_attributes(self.attributes)
        }
    
    def to_otlp_span(self) -> Dict[str, Any]:
        """Convert to OTLP span format."""
        return {
            "name": self.event_type.value,
            "start_time_unix_nano": int(self.timestamp * 1e9),
            "end_time_unix_nano": int(self.timestamp * 1e9),
            "attributes": [
                {"key": "event.type", "value": {"string_value": self.event_type.value}},
                {"key": "user.anonymous_id", "value": {"string_value": self.anonymous_id}},
                {"key": "session.id", "value": {"string_value": self.session_id}},
                *[
                    {"key": k, "value": self._to_otlp_value(v)}
                    for k, v in self._sanitize_attributes(self.attributes).items()
                ]
            ]
        }
    
    def _sanitize_attributes(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """Remove any potentially sensitive data."""
        sanitized = {}
        
        # Whitelist of allowed attribute patterns
        allowed_prefixes = [
            "agent.type", "agent.framework", "agent.name",
            "framework.name", "framework.type",
            "tool.type", "tool.name", 
            "workflow.type", "workflow.name",
            "error.type", "error.component",
            "feature.name", "feature.category",
            "api.endpoint", "api.method", "api.status_code",
            "duration_ms", "success", "count",
            "system.os", "system.python_version", "system.architecture"
        ]
        
        for key, value in attrs.items():
            # Check if key matches allowed patterns
            if any(key.startswith(prefix) for prefix in allowed_prefixes):
                # Further sanitize values
                if isinstance(value, str):
                    # Truncate long strings
                    if len(value) > 50:
                        value = value[:50] + "..."
                    # Remove potential file paths
                    if "/" in value or "\\" in value:
                        value = value.split("/")[-1].split("\\")[-1]
                elif isinstance(value, (int, float, bool)):
                    # Numeric and boolean values are safe
                    pass
                else:
                    # Skip complex types
                    continue
                    
                sanitized[key] = value
                
        return sanitized
    
    def _to_otlp_value(self, value: Any) -> Dict[str, Any]:
        """Convert value to OTLP attribute value format."""
        if isinstance(value, bool):
            return {"bool_value": value}
        elif isinstance(value, int):
            return {"int_value": value}
        elif isinstance(value, float):
            return {"double_value": value}
        else:
            return {"string_value": str(value)}


@dataclass
class AgentRunEvent(TelemetryEvent):
    """Agent run telemetry event."""
    
    def __init__(
        self,
        agent_type: str,
        framework: str,
        success: bool,
        duration_ms: float,
        **kwargs
    ):
        super().__init__(
            event_type=EventType.AGENT_RUN,
            attributes={
                "agent.type": agent_type,
                "agent.framework": framework,
                "success": success,
                "duration_ms": int(duration_ms)
            },
            **kwargs
        )


@dataclass
class FeatureUsageEvent(TelemetryEvent):
    """Feature usage telemetry event."""
    
    def __init__(self, feature_name: str, category: Optional[str] = None, **kwargs):
        super().__init__(
            event_type=EventType.FEATURE_USED,
            attributes={
                "feature.name": feature_name,
                "feature.category": category or "general"
            },
            **kwargs
        )


@dataclass
class ErrorEvent(TelemetryEvent):
    """Error telemetry event (no error details, just type)."""
    
    def __init__(self, error_type: str, component: str, **kwargs):
        super().__init__(
            event_type=EventType.AGENT_ERROR,
            attributes={
                "error.type": error_type,
                "error.component": component
            },
            **kwargs
        )