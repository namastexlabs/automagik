"""LangWatch observability provider implementation."""

import logging
import os
import time
import uuid
from contextlib import contextmanager
from typing import Any, ContextManager, Dict, List, Optional

from ..base import ObservabilityProvider, TraceContext
from ...performance import CircuitBreaker, AsyncTracer

logger = logging.getLogger(__name__)


class LangWatchProvider(ObservabilityProvider):
    """LangWatch observability provider.
    
    Note: This is a basic implementation. In production, you would use
    the official LangWatch SDK when available.
    """
    
    def __init__(self):
        """Initialize LangWatch provider."""
        self.api_key: Optional[str] = None
        self.endpoint: str = "https://app.langwatch.ai/api/v1/traces"
        self.enabled = False
        
        # Performance components
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=60,
            name="langwatch_circuit"
        )
        self.async_tracer: Optional[AsyncTracer] = None
        
        # Current trace context
        self.current_trace_id: Optional[str] = None
        self.current_span_id: Optional[str] = None
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize LangWatch with API key from environment."""
        self.api_key = os.getenv("LANGWATCH_API_KEY")
        if not self.api_key:
            logger.warning("LangWatch API key not found, provider disabled")
            self.enabled = False
            return
        
        # Override endpoint if provided
        if os.getenv("LANGWATCH_ENDPOINT"):
            self.endpoint = os.getenv("LANGWATCH_ENDPOINT")
        
        # Initialize async tracer for non-blocking sends
        self.async_tracer = AsyncTracer(
            max_workers=1,
            queue_size=1000,
            batch_size=10,
            batch_timeout_ms=100,
            processor=self._process_trace_batch
        )
        
        self.enabled = True
        logger.info(f"LangWatch provider initialized with endpoint: {self.endpoint}")
    
    @contextmanager
    def start_trace(
        self,
        name: str,
        kind: str,
        attributes: Dict[str, Any]
    ) -> ContextManager[TraceContext]:
        """Start a LangWatch trace span."""
        if not self.enabled:
            # Return dummy context
            yield TraceContext(
                trace_id="disabled",
                span_id="disabled",
                attributes={},
                sampled=False
            )
            return
        
        # Generate trace IDs
        trace_id = str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        
        # Store current context
        self.current_trace_id = trace_id
        self.current_span_id = span_id
        
        # Create trace start event
        trace_event = {
            "type": "trace_start",
            "trace_id": trace_id,
            "span_id": span_id,
            "name": name,
            "kind": kind,
            "attributes": attributes,
            "timestamp": time.time()
        }
        
        # Queue for async sending
        if self.async_tracer:
            self.async_tracer.trace_event(trace_event)
        
        context = TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            attributes=attributes,
            sampled=True
        )
        
        try:
            yield context
        finally:
            # Send trace end event
            end_event = {
                "type": "trace_end",
                "trace_id": trace_id,
                "span_id": span_id,
                "timestamp": time.time()
            }
            if self.async_tracer:
                self.async_tracer.trace_event(end_event)
    
    def log_llm_call(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response: Any,
        usage: Dict[str, Any]
    ) -> None:
        """Log LLM interaction to LangWatch."""
        if not self.enabled or not self.current_trace_id:
            return
        
        event = {
            "type": "llm_call",
            "trace_id": self.current_trace_id,
            "span_id": self.current_span_id,
            "model": model,
            "messages": messages,
            "response": str(response)[:1000],  # Truncate for safety
            "usage": usage,
            "timestamp": time.time()
        }
        
        if self.async_tracer:
            self.async_tracer.trace_event(event)
    
    def log_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any
    ) -> None:
        """Log tool execution to LangWatch."""
        if not self.enabled or not self.current_trace_id:
            return
        
        event = {
            "type": "tool_call",
            "trace_id": self.current_trace_id,
            "span_id": self.current_span_id,
            "tool_name": tool_name,
            "args": args,
            "result": str(result)[:1000],  # Truncate for safety
            "timestamp": time.time()
        }
        
        if self.async_tracer:
            self.async_tracer.trace_event(event)
    
    def log_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> None:
        """Log error to LangWatch."""
        if not self.enabled:
            return
        
        event = {
            "type": "error",
            "trace_id": self.current_trace_id or "unknown",
            "span_id": self.current_span_id or "unknown",
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": time.time()
        }
        
        if self.async_tracer:
            self.async_tracer.trace_event(event)
    
    def _process_trace_batch(self, events: List[Dict[str, Any]]) -> None:
        """Process a batch of trace events.
        
        Args:
            events: List of trace events to send
        """
        if not events or not self.enabled:
            return
        
        # Use circuit breaker to prevent cascading failures
        def send_batch():
            self._send_to_langwatch(events)
        
        self.circuit_breaker.call(send_batch)
    
    def _send_to_langwatch(self, events: List[Dict[str, Any]]) -> None:
        """Send events to LangWatch API.
        
        Args:
            events: Events to send
        """
        import asyncio
        import httpx
        
        async def send():
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "X-Source": "automagik-agents"
            }
            
            # LangWatch expects a specific format
            # Convert our events to LangWatch format
            traces = []
            for event in events:
                if event["type"] == "trace_start":
                    trace = {
                        "id": event["trace_id"],
                        "project_id": "automagik-agents",
                        "thread_id": event.get("span_id"),
                        "customer_id": event.get("attributes", {}).get("user.id"),
                        "labels": event.get("attributes", {}).get("labels", []),
                        "metadata": event.get("attributes", {}),
                        "timestamps": {
                            "started_at": int(event["timestamp"] * 1000),
                            "updated_at": int(event["timestamp"] * 1000)
                        }
                    }
                    traces.append(trace)
                elif event["type"] == "llm_call":
                    # Add LLM span to trace
                    span = {
                        "type": "llm",
                        "id": event.get("span_id", str(uuid.uuid4())),
                        "parent_id": event.get("trace_id"),
                        "model": event["model"],
                        "input": {"messages": event["messages"]},
                        "output": {"content": event["response"]},
                        "metrics": event.get("usage", {}),
                        "timestamps": {
                            "started_at": int(event["timestamp"] * 1000),
                            "first_token_at": int(event["timestamp"] * 1000) + 100,
                            "completed_at": int(event["timestamp"] * 1000) + 1000
                        }
                    }
                    # Add to appropriate trace
                    for trace in traces:
                        if trace["id"] == event["trace_id"]:
                            if "spans" not in trace:
                                trace["spans"] = []
                            trace["spans"].append(span)
                            break
            
            if not traces:
                return
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.endpoint,
                        json={"traces": traces},
                        headers=headers,
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        logger.debug(f"Successfully sent {len(events)} events to LangWatch")
                    else:
                        logger.warning(f"LangWatch API returned {response.status_code}: {response.text}")
                        
            except Exception as e:
                logger.debug(f"Failed to send to LangWatch: {e}")
        
        # Run async in sync context
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            asyncio.create_task(send())
        else:
            loop.run_until_complete(send())
    
    def flush(self) -> None:
        """Flush any pending traces."""
        # The async tracer handles this automatically
        pass
    
    def shutdown(self) -> None:
        """Cleanup LangWatch resources."""
        if self.async_tracer:
            self.async_tracer.shutdown(timeout=2.0)