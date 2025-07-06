"""HTTP sender for telemetry data using OTLP format."""

import httpx
import logging
import uuid
from typing import Dict, Any, List
import platform
import os

logger = logging.getLogger(__name__)


class TelemetrySender:
    """Sends telemetry data to Namastex endpoint in OTLP format."""
    
    def __init__(self, endpoint: str, timeout: int = 5):
        """Initialize telemetry sender.
        
        Args:
            endpoint: OTLP endpoint URL
            timeout: Request timeout in seconds
        """
        self.endpoint = endpoint
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            limits=httpx.Limits(max_keepalive_connections=5)
        )
    
    async def send_batch(self, events: List[Dict[str, Any]], anonymous_id: str, session_id: str) -> bool:
        """Send batch of events in OTLP format.
        
        Args:
            events: List of telemetry events
            anonymous_id: Anonymous user ID
            session_id: Session ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to OTLP format matching automagik-spark exactly
            otlp_payload = self._create_otlp_payload(events, anonymous_id, session_id)
            
            # Send to endpoint
            response = await self.client.post(
                self.endpoint,
                json=otlp_payload,
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "automagik-agents/1.0.0"
                }
            )
            
            if response.status_code == 200:
                logger.debug(f"✅ Successfully sent {len(events)} telemetry events to {self.endpoint}")
                return True
            else:
                logger.warning(f"❌ Telemetry send failed with status {response.status_code} to {self.endpoint}")
                logger.debug(f"Response: {response.text}")
                return False
                
        except Exception as e:
            logger.debug(f"Failed to send telemetry: {e}")
            return False
    
    def _create_otlp_payload(self, events: List[Dict[str, Any]], anonymous_id: str, session_id: str) -> Dict[str, Any]:
        """Create OTLP payload matching automagik-spark format exactly.
        
        Args:
            events: Telemetry events
            anonymous_id: Anonymous user ID
            session_id: Session ID
            
        Returns:
            OTLP formatted payload
        """
        # Get system info once
        system_info = self._get_system_info()
        
        # Convert events to spans
        spans = []
        for event in events:
            span = self._event_to_span(event, system_info)
            spans.append(span)
        
        # Create OTLP payload matching automagik-spark format
        return {
            "resourceSpans": [{
                "resource": {
                    "attributes": [
                        {"key": "service.name", "value": {"stringValue": "automagik-agents"}},
                        {"key": "service.version", "value": {"stringValue": "1.0.0"}},
                        {"key": "service.organization", "value": {"stringValue": "namastex"}},
                        {"key": "user.id", "value": {"stringValue": anonymous_id}},
                        {"key": "session.id", "value": {"stringValue": session_id}},
                        {"key": "telemetry.sdk.name", "value": {"stringValue": "automagik-agents"}},
                        {"key": "telemetry.sdk.version", "value": {"stringValue": "1.0.0"}}
                    ]
                },
                "scopeSpans": [{
                    "scope": {
                        "name": "automagik-agents.telemetry",
                        "version": "1.0.0"
                    },
                    "spans": spans
                }]
            }]
        }
    
    def _event_to_span(self, event: Dict[str, Any], system_info: Dict[str, str]) -> Dict[str, Any]:
        """Convert telemetry event to OTLP span.
        
        Args:
            event: Telemetry event
            system_info: System information
            
        Returns:
            OTLP span
        """
        # Generate IDs
        trace_id = uuid.uuid4().hex
        span_id = uuid.uuid4().hex[:16]
        
        # Extract event info
        event_type = event.get("event_type", "unknown")
        timestamp = int(event.get("timestamp", 0) * 1e9)  # Convert to nanoseconds
        attributes = event.get("attributes", {})
        
        # Build span attributes
        span_attributes = []
        
        # Add system info (matching automagik-spark format)
        for key, value in system_info.items():
            span_attributes.append({
                "key": key,
                "value": self._to_otlp_value(value)
            })
        
        # Add event attributes
        for key, value in attributes.items():
            span_attributes.append({
                "key": key,
                "value": self._to_otlp_value(value)
            })
        
        return {
            "traceId": trace_id,
            "spanId": span_id,
            "name": event_type,
            "kind": "SPAN_KIND_INTERNAL",
            "startTimeUnixNano": timestamp,
            "endTimeUnixNano": timestamp,
            "attributes": span_attributes,
            "status": {"code": "STATUS_CODE_OK"}
        }
    
    def _get_system_info(self) -> Dict[str, Any]:
        """Get system information matching automagik-spark format.
        
        Returns:
            System information dictionary
        """
        return {
            "system.os": platform.system(),
            "system.os_version": platform.version(),
            "system.python_version": platform.python_version(),
            "system.architecture": platform.machine(),
            "system.is_docker": os.path.exists("/.dockerenv"),
            "system.project_name": "automagik-agents",
            "system.project_version": "1.0.0",
            "system.organization": "namastex"
        }
    
    def _to_otlp_value(self, value: Any) -> Dict[str, Any]:
        """Convert value to OTLP attribute value format.
        
        Args:
            value: Python value
            
        Returns:
            OTLP value dict
        """
        if isinstance(value, bool):
            return {"boolValue": value}
        elif isinstance(value, int):
            return {"intValue": value}
        elif isinstance(value, float):
            return {"doubleValue": value}
        else:
            return {"stringValue": str(value)}
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()