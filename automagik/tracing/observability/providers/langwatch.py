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
        self.endpoint: str = "https://app.langwatch.ai/api/collector"
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
        
        # Defer async tracer initialization to avoid import issues
        self.async_tracer = None
        self._tracer_config = {
            "max_workers": 1,
            "queue_size": 1000,
            "batch_size": 10,
            "batch_timeout_ms": 100,
            "processor": self._process_trace_batch
        }
        
        self.enabled = True
        logger.info(f"🔍 LangWatch provider initialized with endpoint: {self.endpoint} and API key: {self.api_key[:10]}...")
    
    def _ensure_tracer(self):
        """Ensure async tracer is initialized."""
        if self.async_tracer is None:
            from ...performance import AsyncTracer
            self.async_tracer = AsyncTracer(**self._tracer_config)
    
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
        self._ensure_tracer()
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
            self._ensure_tracer()
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
        if not self.enabled:
            logger.debug("LangWatch not enabled, skipping LLM call logging")
            return
            
        if not self.current_trace_id:
            logger.warning("No active trace, creating new trace for LLM call")
            self.current_trace_id = str(uuid.uuid4())
            self.current_span_id = str(uuid.uuid4())
        
        logger.info(f"📝 Logging LLM call to LangWatch - model: {model}, messages: {len(messages)}, usage: {usage}")
        
        # Log full system prompt and conversation
        event = {
            "type": "llm_call",
            "trace_id": self.current_trace_id,
            "span_id": self.current_span_id,
            "model": model,
            "messages": messages,  # This now includes system prompt and full history
            "response": str(response),  # Full response
            "usage": usage,
            "timestamp": time.time()
        }
        
        self._ensure_tracer()
        if self.async_tracer:
            self.async_tracer.trace_event(event)
            logger.debug(f"Event queued for LangWatch: {event['type']} for trace {event['trace_id']}")
    
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
        
        self._ensure_tracer()
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
        
        self._ensure_tracer()
        if self.async_tracer:
            self.async_tracer.trace_event(event)
    
    def log_metadata(
        self,
        metadata: Dict[str, Any]
    ) -> None:
        """Log additional metadata and context to LangWatch."""
        if not self.enabled or not self.current_trace_id:
            return
        
        # Log memory variables if present
        if "memory_variables" in metadata and metadata["memory_variables"]:
            event = {
                "type": "metadata",
                "trace_id": self.current_trace_id,
                "span_id": str(uuid.uuid4()),
                "category": "memory_variables",
                "data": metadata["memory_variables"],
                "timestamp": time.time()
            }
            self._ensure_tracer()
            if self.async_tracer:
                self.async_tracer.trace_event(event)
        
        # Log tool calls as separate spans
        if "tool_calls" in metadata and metadata["tool_calls"]:
            for tool_call in metadata["tool_calls"]:
                self.log_tool_call(
                    tool_name=tool_call.get("name", "unknown"),
                    args=tool_call.get("args", {}),
                    result=tool_call.get("result", "")
                )
        
        # Store metadata for the current trace
        metadata_event = {
            "type": "trace_metadata",
            "trace_id": self.current_trace_id,
            "span_id": self.current_span_id,
            "metadata": {
                "agent_name": metadata.get("agent_name"),
                "agent_id": metadata.get("agent_id"),
                "framework": metadata.get("framework"),
                "session_id": metadata.get("session_id"),
                "multimodal": metadata.get("multimodal", False)
            },
            "timestamp": time.time()
        }
        
        self._ensure_tracer()
        if self.async_tracer:
            self.async_tracer.trace_event(metadata_event)
    
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
                "X-Auth-Token": self.api_key,
                "Content-Type": "application/json"
            }
            
            # Convert our events to LangWatch format
            # Group events by trace_id
            traces_map = {}
            
            for event in events:
                trace_id = event.get("trace_id", "unknown")
                
                if trace_id not in traces_map:
                    traces_map[trace_id] = {
                        "trace_id": trace_id,
                        "spans": [],
                        "metadata": {}
                    }
                
                # Convert event to span
                if event["type"] == "llm_call":
                    # Extract vendor from model name
                    model = event.get("model", "unknown")
                    vendor = "openai" if "gpt" in model else "anthropic" if "claude" in model else "unknown"
                    
                    span = {
                        "type": "llm",
                        "span_id": event.get("span_id", str(uuid.uuid4())),
                        "vendor": vendor,
                        "model": model,
                        "input": {
                            "type": "chat_messages",
                            "value": event.get("messages", [])
                        },
                        "output": {
                            "type": "chat_messages",
                            "value": [{
                                "role": "assistant",
                                "content": event.get("response", "")
                            }]
                        },
                        "params": {},
                        "metrics": event.get("usage", {}),
                        "timestamps": {
                            "started_at": int(event["timestamp"] * 1000),
                            "finished_at": int(event["timestamp"] * 1000) + 1000
                        }
                    }
                    traces_map[trace_id]["spans"].append(span)
                elif event["type"] == "tool_call":
                    span = {
                        "type": "tool",
                        "span_id": event.get("span_id", str(uuid.uuid4())),
                        "name": event.get("tool_name", "unknown"),
                        "input": {
                            "type": "json",
                            "value": event.get("args", {})
                        },
                        "output": {
                            "type": "json",
                            "value": event.get("result", {})
                        },
                        "timestamps": {
                            "started_at": int(event["timestamp"] * 1000),
                            "finished_at": int(event["timestamp"] * 1000) + 500
                        }
                    }
                    traces_map[trace_id]["spans"].append(span)
                elif event["type"] == "trace_metadata":
                    # Add metadata to the trace
                    traces_map[trace_id]["metadata"].update(event.get("metadata", {}))
                elif event["type"] == "metadata":
                    # Add additional metadata
                    category = event.get("category", "general")
                    traces_map[trace_id]["metadata"][category] = event.get("data", {})
            
            # Only send traces that have spans
            traces = [trace for trace in traces_map.values() if trace["spans"]]
            
            if not traces:
                return
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.endpoint,
                        json=traces[0] if len(traces) == 1 else {"traces": traces},
                        headers=headers,
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"✅ Successfully sent {len(events)} events to LangWatch")
                    elif response.status_code == 201:
                        logger.info(f"✅ Successfully created trace in LangWatch")
                    else:
                        logger.warning(f"❌ LangWatch API returned {response.status_code}: {response.text}")
                        
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