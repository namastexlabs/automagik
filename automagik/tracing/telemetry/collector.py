"""Privacy-first telemetry collector for anonymous usage analytics."""

import hashlib
import json
import logging
import platform
import time
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..config import TracingConfig
from ..performance import AsyncTracer, CircuitBreaker
from .events import (
    AgentRunEvent,
    ErrorEvent,
    EventType,
    FeatureUsageEvent,
    TelemetryEvent,
)

logger = logging.getLogger(__name__)


class TelemetryCollector:
    """Collects anonymous usage telemetry with privacy-first design.
    
    Features:
    - No personal information collected
    - Anonymous user IDs
    - Aggregated metrics only
    - Local buffering with async sending
    - Automatic failure handling
    """
    
    def __init__(self, config: TracingConfig):
        """Initialize telemetry collector.
        
        Args:
            config: Tracing configuration
        """
        self.config = config
        self.anonymous_id = self._get_or_create_anonymous_id()
        self.session_id = str(uuid.uuid4())
        
        # Feature usage counters
        self.feature_counters = defaultdict(int)
        
        # System info (collected once)
        self.system_info = self._get_system_info()
        
        # Async tracer for non-blocking sends
        self.tracer = AsyncTracer(
            max_workers=1,  # Single worker for telemetry
            queue_size=config.max_queue_size,
            batch_size=config.batch_size,
            batch_timeout_ms=config.batch_timeout_ms,
            processor=self._process_event_batch
        )
        
        # Circuit breaker for endpoint failures
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=300,  # 5 minutes
            name="telemetry_circuit"
        )
        
        # Send startup event
        self._send_startup_event()
    
    def _get_or_create_anonymous_id(self) -> str:
        """Get or create persistent anonymous ID."""
        id_file = Path.home() / ".automagik" / "anonymous_id"
        
        # Check if ID already exists
        if id_file.exists():
            try:
                return id_file.read_text().strip()
            except Exception:
                pass
        
        # Generate new anonymous ID
        # Hash machine characteristics for consistency without exposing info
        machine_data = f"{platform.system()}-{platform.machine()}-{platform.node()}"
        anonymous_id = hashlib.sha256(machine_data.encode()).hexdigest()[:16]
        
        # Save for future sessions
        try:
            id_file.parent.mkdir(exist_ok=True, parents=True)
            id_file.write_text(anonymous_id)
        except Exception as e:
            logger.debug(f"Could not save anonymous ID: {e}")
        
        return anonymous_id
    
    def _get_system_info(self) -> Dict[str, str]:
        """Get anonymized system information."""
        try:
            return {
                "system.os": platform.system(),
                "system.python_version": platform.python_version(),
                "system.architecture": platform.machine(),
            }
        except Exception:
            return {}
    
    def _send_startup_event(self):
        """Send telemetry startup event."""
        event = TelemetryEvent(
            event_type=EventType.STARTUP,
            anonymous_id=self.anonymous_id,
            session_id=self.session_id,
            attributes=self.system_info
        )
        self.track_event(event)
    
    def track_agent_run(
        self,
        agent_type: str,
        framework: str,
        success: bool,
        duration_ms: float
    ):
        """Track agent execution (no content).
        
        Args:
            agent_type: Type of agent (e.g., "simple", "claude_code")
            framework: Framework used (e.g., "pydantic_ai", "agno")
            success: Whether the run succeeded
            duration_ms: Execution duration in milliseconds
        """
        logger.debug(f"📊 Tracking agent run: {agent_type} ({framework}) - success: {success}, duration: {duration_ms:.2f}ms")
        event = AgentRunEvent(
            agent_type=agent_type,
            framework=framework,
            success=success,
            duration_ms=duration_ms,
            anonymous_id=self.anonymous_id,
            session_id=self.session_id
        )
        self.track_event(event)
    
    def track_feature_usage(self, feature_name: str, category: Optional[str] = None):
        """Track feature usage.
        
        Args:
            feature_name: Name of the feature
            category: Optional category
        """
        self.feature_counters[feature_name] += 1
        
        event = FeatureUsageEvent(
            feature_name=feature_name,
            category=category,
            anonymous_id=self.anonymous_id,
            session_id=self.session_id
        )
        self.track_event(event)
    
    def track_error(self, error_type: str, component: str):
        """Track error occurrence (no details).
        
        Args:
            error_type: Type of error (e.g., "timeout", "api_error")
            component: Component where error occurred
        """
        event = ErrorEvent(
            error_type=error_type,
            component=component,
            anonymous_id=self.anonymous_id,
            session_id=self.session_id
        )
        self.track_event(event)
    
    def track_http_request(self, method: str, path: str, status_code: int, duration_ms: float):
        """Track HTTP request (anonymized).
        
        Args:
            method: HTTP method
            path: Request path (should be anonymized)
            status_code: Response status code
            duration_ms: Request duration in milliseconds
        """
        event = TelemetryEvent(
            event_type=EventType.API_REQUEST,
            anonymous_id=self.anonymous_id,
            session_id=self.session_id,
            attributes={
                "event.method": method,
                "event.path": path,
                "event.status_code": status_code,
                "event.duration_ms": duration_ms,
                "event.success": 200 <= status_code < 400
            }
        )
        self.track_event(event)
    
    def track_event(self, event: TelemetryEvent):
        """Track a telemetry event.
        
        Args:
            event: Event to track
        """
        # Add system info to all events
        event.attributes.update(self.system_info)
        
        # Queue for async processing
        self.tracer.trace_event(event.to_dict())
    
    def _process_event_batch(self, events: List[Dict[str, Any]]):
        """Process a batch of events.
        
        Args:
            events: List of event dictionaries
        """
        # Use circuit breaker to prevent cascading failures
        def send_batch():
            self._send_telemetry_batch(events)
        
        self.circuit_breaker.call(send_batch)
    
    def _send_telemetry_batch(self, events: List[Dict[str, Any]]):
        """Send telemetry batch to endpoint.
        
        Args:
            events: List of events to send
        """
        if not events:
            return
        
        # Send using async in sync context
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop in thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Import sender
        from .sender import TelemetrySender
        
        async def send():
            sender = TelemetrySender(self.config.telemetry_endpoint)
            try:
                success = await sender.send_batch(events, self.anonymous_id, self.session_id)
                if success:
                    logger.debug(f"Sent {len(events)} telemetry events")
                else:
                    logger.debug(f"Failed to send telemetry batch")
            finally:
                await sender.close()
        
        # Run in event loop
        if loop.is_running():
            # Schedule as task if loop is already running
            asyncio.create_task(send())
        else:
            # Run directly if no loop running
            loop.run_until_complete(send())
    
    def _convert_to_otlp(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert events to OTLP format.
        
        Args:
            events: List of event dictionaries
            
        Returns:
            OTLP formatted data
        """
        spans = []
        for event_dict in events:
            # Recreate event object for OTLP conversion
            event = TelemetryEvent(
                event_type=EventType(event_dict["event_type"]),
                timestamp=event_dict["timestamp"],
                anonymous_id=event_dict["anonymous_id"],
                session_id=event_dict["session_id"],
                attributes=event_dict["attributes"]
            )
            spans.append(event.to_otlp_span())
        
        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"string_value": "automagik-agents"}},
                        {"key": "service.version", "value": {"string_value": "1.0.0"}},
                        {"key": "telemetry.sdk.name", "value": {"string_value": "automagik-telemetry"}},
                        {"key": "telemetry.sdk.version", "value": {"string_value": "1.0.0"}}
                    ]
                },
                "scopeSpans": [{
                    "scope": {
                        "name": "automagik.telemetry",
                        "version": "1.0.0"
                    },
                    "spans": spans
                }]
            }]
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get telemetry collection metrics."""
        tracer_metrics = self.tracer.get_metrics()
        circuit_state = self.circuit_breaker.get_state()
        
        return {
            "anonymous_id": self.anonymous_id,
            "session_id": self.session_id,
            "feature_usage": dict(self.feature_counters),
            "tracer": tracer_metrics,
            "circuit_breaker": circuit_state
        }
    
    def shutdown(self):
        """Shutdown telemetry collector gracefully."""
        logger.debug("Shutting down telemetry collector")
        
        # Send any remaining events
        self.tracer.shutdown(timeout=2.0)
        
        # Log final metrics
        metrics = self.get_metrics()
        logger.debug(f"Telemetry shutdown. Final metrics: {metrics}")