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
        usage: Dict[str, Any],
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ) -> None:
        """Log LLM interaction to LangWatch."""
        if not self.enabled:
            logger.debug("LangWatch not enabled, skipping LLM call logging")
            return
            
        # Use provided trace_id or current trace_id or create new one
        used_trace_id = trace_id or self.current_trace_id or str(uuid.uuid4())
        used_span_id = span_id or self.current_span_id or str(uuid.uuid4())
        if not self.current_trace_id:
            self.current_trace_id = used_trace_id
            self.current_span_id = used_span_id
        
        logger.debug(f"Logging LLM call to LangWatch - model: {model}, messages: {len(messages)}")
        
        # Log full system prompt and conversation
        event = {
            "type": "llm_call",
            "trace_id": used_trace_id,
            "span_id": used_span_id,
            "parent_span_id": parent_span_id,
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
        result: Any,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
        trace_id: Optional[str] = None,
        parent_span_id: Optional[str] = None
    ) -> None:
        """Log tool execution to LangWatch with proper span structure."""
        if not self.enabled:
            return
        
        # Use provided trace_id or current trace_id
        used_trace_id = trace_id or self.current_trace_id
        if not used_trace_id:
            return
        
        logger.debug(f"Logging tool call to LangWatch - tool: {tool_name}")
        
        # Create a unique span ID for this tool call
        tool_span_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Enhanced tool call event with proper span structure
        event = {
            "type": "tool_call",
            "trace_id": used_trace_id,
            "span_id": tool_span_id,
            "parent_span_id": parent_span_id or self.current_span_id,  # Use provided parent_span_id or fallback to current
            "tool_name": tool_name,
            "args": self._sanitize_tool_args(args),
            "result": self._sanitize_tool_result(result),
            "duration_ms": duration_ms or 100,  # Default duration if not provided
            "status": "error" if error else "success",
            "error": error,
            "timestamp": start_time,
            "finished_at": start_time + (duration_ms or 100) / 1000
        }
        
        self._ensure_tracer()
        if self.async_tracer:
            self.async_tracer.trace_event(event)
            logger.debug(f"Tool call event queued for LangWatch: {tool_name} for trace {event['trace_id']}")
    
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
    
    def log_memory_operation(
        self,
        operation: str,  # "store", "retrieve", "list"
        key: Optional[str] = None,
        content: Optional[str] = None,
        result: Any = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None
    ) -> None:
        """Log memory operations as separate spans with detailed context."""
        if not self.enabled or not self.current_trace_id:
            return
        
        logger.info(f"💾 Logging memory operation to LangWatch - operation: {operation}, key: {key}")
        
        memory_span_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Create specific memory operation span
        event = {
            "type": "memory_operation",
            "trace_id": self.current_trace_id,
            "span_id": memory_span_id,
            "parent_span_id": self.current_span_id,
            "operation": operation,
            "key": key,
            "content_length": len(str(content)) if content else 0,
            "result": str(result)[:500] if result else None,  # Truncate for safety
            "duration_ms": duration_ms or 50,
            "status": "error" if error else "success",
            "error": error,
            "timestamp": start_time,
            "finished_at": start_time + (duration_ms or 50) / 1000
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
        
        # Log tool calls as separate spans with enhanced information
        if "tool_calls" in metadata and metadata["tool_calls"]:
            for tool_call in metadata["tool_calls"]:
                self.log_tool_call(
                    tool_name=tool_call.get("name", "unknown"),
                    args=tool_call.get("args", {}),
                    result=tool_call.get("result", ""),
                    duration_ms=tool_call.get("duration_ms"),
                    error=tool_call.get("error")
                )
        
        # Store metadata for the current trace with enhanced agent context
        metadata_event = {
            "type": "trace_metadata",
            "trace_id": self.current_trace_id,
            "span_id": self.current_span_id,
            "metadata": {
                "agent_name": metadata.get("agent_name"),
                "agent_id": metadata.get("agent_id"),
                "framework": metadata.get("framework"),
                "session_id": metadata.get("session_id"),
                "user_id": metadata.get("user_id"),
                "thread_id": metadata.get("thread_id"),  # For conversation grouping
                "customer_id": metadata.get("customer_id"),  # For multi-tenancy
                "multimodal": metadata.get("multimodal", False),
                "model": metadata.get("model"),
                "temperature": metadata.get("temperature"),
                "max_tokens": metadata.get("max_tokens")
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
    
    def _sanitize_tool_args(self, args: Any) -> Dict[str, Any]:
        """Sanitize tool arguments for LangWatch."""
        # Handle case where args is a string (like from PydanticAI)
        if isinstance(args, str):
            try:
                import json
                args = json.loads(args)
            except (json.JSONDecodeError, ValueError):
                # If it's not valid JSON, treat it as a raw string argument
                return {"raw_args": args}
        
        # Handle case where args is not a dictionary
        if not isinstance(args, dict):
            return {"value": str(args)}
        
        sanitized = {}
        for key, value in args.items():
            if isinstance(value, str) and len(value) > 1000:
                sanitized[key] = value[:1000] + "... [truncated]"
            elif key.lower() in ['password', 'token', 'key', 'secret']:
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = value
        return sanitized
    
    def _sanitize_tool_result(self, result: Any) -> str:
        """Sanitize tool result for LangWatch."""
        result_str = str(result)
        if len(result_str) > 2000:
            return result_str[:2000] + "... [truncated]"
        return result_str
    
    def _send_to_langwatch(self, events: List[Dict[str, Any]]) -> None:
        """Send events to LangWatch API with enhanced span formatting.
        
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
            
            # Convert our events to LangWatch format with proper span structure
            traces_map = {}
            
            for event in events:
                trace_id = event.get("trace_id", "unknown")
                
                if trace_id not in traces_map:
                    traces_map[trace_id] = {
                        "trace_id": trace_id,
                        "spans": [],
                        "metadata": {}
                    }
                
                # Convert event to proper LangWatch span format
                if event["type"] == "llm_call":
                    # Extract vendor from model name with better detection
                    model = event.get("model", "unknown")
                    vendor = self._detect_llm_vendor(model)
                    
                    span = {
                        "type": "llm",
                        "span_id": event.get("span_id", str(uuid.uuid4())),
                        "parent_span_id": event.get("parent_span_id"),
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
                        "params": {
                            "temperature": event.get("temperature"),
                            "max_tokens": event.get("max_tokens")
                        },
                        "metrics": event.get("usage", {}),
                        "timestamps": {
                            "started_at": int(event["timestamp"] * 1000),
                            "finished_at": int((event.get("finished_at", event["timestamp"]) * 1000))
                        }
                    }
                    traces_map[trace_id]["spans"].append(span)
                    
                elif event["type"] == "tool_call":
                    # Enhanced tool span with better categorization
                    tool_name = event.get("tool_name", "unknown")
                    tool_category = self._categorize_tool(tool_name)
                    
                    # Clean result text for tool output - extract meaningful user-facing text
                    tool_result = event.get("result", "")
                    clean_result = self._extract_clean_tool_result(tool_result, tool_name)
                    
                    span = {
                        "type": "span",  # Generic span for tools
                        "span_id": event.get("span_id", str(uuid.uuid4())),
                        "parent_span_id": event.get("parent_span_id"),
                        "name": f"{tool_category}: {tool_name}",
                        "input": {
                            "type": "text",
                            "value": f"Calling {tool_name}"
                        },
                        "output": {
                            "type": "text",
                            "value": clean_result
                        },
                        "metrics": {
                            "duration_ms": event.get("duration_ms", 0)
                        },
                        "timestamps": {
                            "started_at": int(event["timestamp"] * 1000),
                            "finished_at": int(event.get("finished_at", event["timestamp"]) * 1000)
                        },
                        "error": event.get("error")
                    }
                    traces_map[trace_id]["spans"].append(span)
                    
                elif event["type"] == "memory_operation":
                    # Special span for memory operations
                    operation = event.get("operation", "unknown")
                    
                    span = {
                        "type": "span",
                        "span_id": event.get("span_id", str(uuid.uuid4())),
                        "parent_span_id": event.get("parent_span_id"),
                        "name": f"Memory: {operation}",
                        "input": {
                            "type": "json",
                            "value": {
                                "operation": operation,
                                "key": event.get("key"),
                                "content_length": event.get("content_length", 0)
                            }
                        },
                        "output": {
                            "type": "json",
                            "value": {
                                "result": event.get("result", ""),
                                "status": event.get("status", "success")
                            }
                        },
                        "metrics": {
                            "duration_ms": event.get("duration_ms", 0)
                        },
                        "timestamps": {
                            "started_at": int(event["timestamp"] * 1000),
                            "finished_at": int(event.get("finished_at", event["timestamp"]) * 1000)
                        },
                        "error": event.get("error")
                    }
                    traces_map[trace_id]["spans"].append(span)
                    
                elif event["type"] == "trace_metadata":
                    # Add metadata to the trace with better structure
                    trace_metadata = event.get("metadata", {})
                    
                    # Extract key fields for LangWatch
                    if "user_id" in trace_metadata:
                        traces_map[trace_id]["user_id"] = trace_metadata["user_id"]
                    if "thread_id" in trace_metadata:
                        traces_map[trace_id]["thread_id"] = trace_metadata["thread_id"]
                    if "customer_id" in trace_metadata:
                        traces_map[trace_id]["customer_id"] = trace_metadata["customer_id"]
                    
                    # Store all metadata
                    traces_map[trace_id]["metadata"].update(trace_metadata)
                    
                elif event["type"] == "metadata":
                    # Add additional metadata
                    category = event.get("category", "general")
                    traces_map[trace_id]["metadata"][category] = event.get("data", {})
                
                elif event["type"] == "trace_start":
                    # Initialize trace with metadata
                    trace_metadata = event.get("metadata", {})
                    
                    # Extract key LangWatch fields
                    if "user_id" in trace_metadata:
                        traces_map[trace_id]["user_id"] = trace_metadata["user_id"]
                    if "thread_id" in trace_metadata:
                        traces_map[trace_id]["thread_id"] = trace_metadata["thread_id"]
                    if "customer_id" in trace_metadata:
                        traces_map[trace_id]["customer_id"] = trace_metadata["customer_id"]
                    
                    # Store all metadata
                    traces_map[trace_id]["metadata"].update(trace_metadata)
                    traces_map[trace_id]["input"] = {"value": event.get("input", "")}
                
                elif event["type"] in ["agent_config", "input_processing", "output_generation"]:
                    # Create spans for agent lifecycle events with clean text outputs
                    span_name_map = {
                        "agent_config": "Agent Configuration",
                        "input_processing": "Input Processing", 
                        "output_generation": "Output Generation"
                    }
                    
                    # Get the output and ensure it's clean text
                    output_text = event.get("output", "Completed successfully")
                    
                    span = {
                        "type": "span",
                        "span_id": event.get("span_id", str(uuid.uuid4())),
                        "parent_span_id": event.get("parent_span_id"),
                        "name": span_name_map[event["type"]],
                        "input": {
                            "type": "text",
                            "value": event.get("input", "")
                        },
                        "output": {
                            "type": "text", 
                            "value": output_text
                        },
                        "timestamps": {
                            "started_at": int(event["timestamp"] * 1000),
                            "finished_at": int(event["timestamp"] * 1000)
                        }
                    }
                    traces_map[trace_id]["spans"].append(span)
                
                elif event["type"] == "trace_end":
                    # Set final output for the trace
                    traces_map[trace_id]["output"] = {"value": event.get("output", "Agent execution completed")}
            
            # Only send traces that have spans
            traces = [trace for trace in traces_map.values() if trace["spans"]]
            
            if not traces:
                return
            
            try:
                async with httpx.AsyncClient() as client:
                    # Send each trace separately for better LangWatch handling
                    for trace in traces:
                        response = await client.post(
                            self.endpoint,
                            json=trace,
                            headers=headers,
                            timeout=10.0
                        )
                        
                        if response.status_code in [200, 201]:
                            logger.debug(f"✅ Successfully sent trace {trace['trace_id']} with {len(trace['spans'])} spans to LangWatch")
                        else:
                            logger.warning(f"❌ LangWatch API returned {response.status_code} for trace {trace['trace_id']}: {response.text}")
                            
            except Exception as e:
                logger.error(f"Failed to send to LangWatch: {e}")
        
        # Execute the async function
        try:
            # Check if there's a running loop
            try:
                loop = asyncio.get_running_loop()
                asyncio.create_task(send())
            except RuntimeError:
                # No running loop, run in a new one
                asyncio.run(send())
        except Exception as e:
            logger.error(f"Failed to send to LangWatch: {e}")
    
    def _detect_llm_vendor(self, model: str) -> str:
        """Detect LLM vendor from model name."""
        model_lower = model.lower()
        if "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        elif "claude" in model_lower or "anthropic" in model_lower:
            return "anthropic"
        elif "gemini" in model_lower or "google" in model_lower:
            return "google"
        elif "llama" in model_lower or "meta" in model_lower:
            return "meta"
        elif "mistral" in model_lower:
            return "mistral"
        elif "groq" in model_lower:
            return "groq"
        else:
            return "unknown"
    
    def _categorize_tool(self, tool_name: str) -> str:
        """Categorize tool for better span naming."""
        tool_lower = tool_name.lower()
        if "memory" in tool_lower or "store" in tool_lower or "get_memory" in tool_lower:
            return "Memory"
        elif "time" in tool_lower or "date" in tool_lower:
            return "DateTime"
        elif "search" in tool_lower:
            return "Search"
        elif "message" in tool_lower or "send" in tool_lower:
            return "Communication"
        elif "multimodal" in tool_lower or "image" in tool_lower or "audio" in tool_lower:
            return "Multimodal"
        else:
            return "Tool"
    
    def _extract_clean_tool_result(self, tool_result: Any, tool_name: str) -> str:
        """Extract clean, user-friendly text from tool result."""
        try:
            # Handle different tool result structures
            if isinstance(tool_result, dict):
                # For get_current_time tool specifically
                if tool_name == "get_current_time" and "result" in tool_result:
                    return f"Current time: {tool_result['result']}"
                
                # For dictionary results, extract the most relevant field
                if "result" in tool_result:
                    result_value = tool_result["result"]
                    if isinstance(result_value, str):
                        return result_value
                    else:
                        return str(result_value)
                
                # Try other common result fields
                for key in ["content", "text", "message", "output", "value"]:
                    if key in tool_result:
                        return str(tool_result[key])
                
                # If no obvious result field, create a summary
                summary_parts = []
                for key, value in tool_result.items():
                    if key not in ["timestamp", "metadata"] and value is not None:
                        summary_parts.append(f"{key}: {value}")
                
                if summary_parts:
                    return "; ".join(summary_parts[:3])  # Limit to first 3 fields
                
                return "Tool executed successfully"
            
            elif isinstance(tool_result, str):
                return tool_result
            
            elif tool_result is None:
                return "Tool executed successfully"
            
            else:
                # For other types, convert to string but keep it clean
                result_str = str(tool_result)
                if len(result_str) > 100:
                    return result_str[:100] + "..."
                return result_str
                
        except Exception as e:
            logger.warning(f"Error extracting clean tool result: {e}")
            return "Tool executed"
    
    def flush(self) -> None:
        """Flush any pending traces."""
        # The async tracer handles this automatically
        pass
    
    def shutdown(self) -> None:
        """Cleanup LangWatch resources."""
        if self.async_tracer:
            self.async_tracer.shutdown(timeout=2.0)
    
    # Enhanced tracing methods for better user experience
    
    def start_trace(self, trace_id: str, span_id: str, name: str, input_text: str, metadata: Dict[str, Any]) -> None:
        """Start a new trace with comprehensive metadata for LangWatch."""
        self.current_trace_id = trace_id
        self.current_span_id = span_id
        
        # Create trace start event with full context
        event = {
            "type": "trace_start",
            "trace_id": trace_id,
            "span_id": span_id,
            "name": name,
            "input": input_text,
            "metadata": metadata,
            "timestamp": time.time()
        }
        
        self._ensure_tracer()
        if self.async_tracer:
            self.async_tracer.trace_event(event)
    
    def log_agent_config(self, trace_id: str, span_id: str, parent_span_id: str, agent_name: str, model: str, system_prompt: str, memory_variables: Dict, framework: str) -> None:
        """Log agent configuration as a dedicated span."""
        
        # Create clean text summary for configuration
        config_summary = f"Agent: {agent_name}\nModel: {model}\nFramework: {framework}\nMemory Variables: {len(memory_variables)}"
        
        event = {
            "type": "agent_config",
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "input": f"Configuring agent {agent_name}",
            "output": config_summary,
            "agent_name": agent_name,
            "model": model,
            "system_prompt": system_prompt[:500] + "..." if len(system_prompt) > 500 else system_prompt,
            "memory_variables": list(memory_variables.keys()) if memory_variables else [],
            "framework": framework,
            "timestamp": time.time()
        }
        
        self._ensure_tracer()
        if self.async_tracer:
            self.async_tracer.trace_event(event)
    
    def log_input_processing(self, trace_id: str, span_id: str, parent_span_id: str, raw_input: str, processed_input: str, message_history: List, multimodal_content: bool) -> None:
        """Log input processing as a dedicated span."""
        
        # Create clean text output for input processing
        processing_summary = f"Input processed successfully"
        if message_history:
            processing_summary += f" (with {len(message_history)} previous messages)"
        if multimodal_content:
            processing_summary += " (multimodal content detected)"
        
        event = {
            "type": "input_processing",
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "input": raw_input,
            "output": processing_summary,
            "raw_input": raw_input,
            "processed_input": processed_input,
            "message_history_length": len(message_history) if message_history else 0,
            "multimodal": multimodal_content,
            "timestamp": time.time()
        }
        
        self._ensure_tracer()
        if self.async_tracer:
            self.async_tracer.trace_event(event)
    
    def log_output_generation(self, trace_id: str, span_id: str, parent_span_id: str, raw_output: str, final_output: str, tool_calls: List, usage: Dict) -> None:
        """Log output generation as a dedicated span."""
        
        # Create clean text summary for output generation
        generation_summary = f"Generated response"
        if tool_calls:
            generation_summary += f" (used {len(tool_calls)} tools)"
        if usage.get('total_tokens'):
            generation_summary += f" - {usage['total_tokens']} tokens"
        
        event = {
            "type": "output_generation",
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
            "input": "Generating final response",
            "output": final_output,  # Clean final text output
            "raw_output": raw_output[:1000] + "..." if len(raw_output) > 1000 else raw_output,
            "final_output": final_output,
            "tool_calls_count": len(tool_calls),
            "usage": usage,
            "timestamp": time.time()
        }
        
        self._ensure_tracer()
        if self.async_tracer:
            self.async_tracer.trace_event(event)
    
    def complete_trace(self, trace_id: str, final_output: str) -> None:
        """Complete the trace and trigger sending to LangWatch."""
        end_event = {
            "type": "trace_end",
            "trace_id": trace_id,
            "span_id": self.current_span_id,
            "output": final_output,  # Set final trace output
            "timestamp": time.time()
        }
        
        self._ensure_tracer()
        if self.async_tracer:
            self.async_tracer.trace_event(end_event)
            # Force flush to send immediately
            if hasattr(self.async_tracer, 'flush'):
                self.async_tracer.flush()