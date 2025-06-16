"""
Raw Claude CLI Stream Processor

This module processes the raw JSON stream from Claude CLI to extract
comprehensive metrics and events that were missing from our previous
logging implementation.
"""

import json
import logging
from collections import deque
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ClaudeStreamMetrics:
    """Comprehensive metrics extracted from Claude CLI stream."""
    
    # Session info
    session_id: Optional[str] = None
    model: Optional[str] = None
    tools_available: List[str] = field(default_factory=list)
    mcp_servers: List[str] = field(default_factory=list)
    
    # Execution metrics
    total_turns: int = 0
    total_cost_usd: float = 0.0
    duration_ms: int = 0
    duration_api_ms: int = 0
    
    # Token usage (comprehensive)
    total_input_tokens: int = 0
    total_cache_creation_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_output_tokens: int = 0
    
    # Tool usage
    tool_calls: int = 0
    tool_names_used: List[str] = field(default_factory=list)
    tool_errors: int = 0
    
    # Message flow
    assistant_messages: int = 0
    user_messages: int = 0
    system_messages: int = 0
    
    # Results
    final_result: str = ""
    is_success: bool = False
    error_message: Optional[str] = None
    
    # Event tracking
    total_events: int = 0
    event_types: Dict[str, int] = field(default_factory=dict)
    
    @property
    def total_tokens(self) -> int:
        """Calculate total tokens across all usage categories."""
        return (self.total_input_tokens + 
                self.total_cache_creation_tokens + 
                self.total_cache_read_tokens + 
                self.total_output_tokens)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary for API responses."""
        return {
            "session_id": self.session_id,
            "model": self.model,
            "tools_available": self.tools_available,
            "mcp_servers": self.mcp_servers,
            "total_turns": self.total_turns,
            "total_cost_usd": self.total_cost_usd,
            "duration_ms": self.duration_ms,
            "duration_api_ms": self.duration_api_ms,
            "total_tokens": self.total_tokens,
            "token_breakdown": {
                "input_tokens": self.total_input_tokens,
                "cache_creation_tokens": self.total_cache_creation_tokens,
                "cache_read_tokens": self.total_cache_read_tokens,
                "output_tokens": self.total_output_tokens
            },
            "tool_usage": {
                "tool_calls": self.tool_calls,
                "tool_names_used": self.tool_names_used,
                "tool_errors": self.tool_errors
            },
            "message_flow": {
                "assistant_messages": self.assistant_messages,
                "user_messages": self.user_messages,
                "system_messages": self.system_messages
            },
            "final_result": self.final_result,
            "is_success": self.is_success,
            "error_message": self.error_message,
            "total_events": self.total_events,
            "event_types": self.event_types
        }


class RawStreamProcessor:
    """Processes raw Claude CLI JSON stream to extract comprehensive metrics."""
    
    def __init__(self, max_events: int = 1000, store_raw_events: bool = True):
        """Initialize the stream processor.
        
        Args:
            max_events: Maximum number of raw events to store (default: 1000)
            store_raw_events: Whether to store raw events at all (default: True)
        """
        self.metrics = ClaudeStreamMetrics()
        self.raw_events: deque = deque(maxlen=max_events if store_raw_events else 0)
        self._processing_complete = False
        self._store_raw_events = store_raw_events
        
        # Pre-define event type handlers for faster dispatch
        self._event_handlers = {
            ("system", "init"): self._process_system_init,
            ("assistant", ""): self._process_assistant_message,
            ("user", ""): self._process_user_message,
            ("result", ""): self._process_result,
        }
        
        # Cache for faster string operations
        self._known_tool_names: Set[str] = set()
        
    def process_line(self, line: str) -> Optional[Dict[str, Any]]:
        """
        Process a single line from Claude CLI stream.
        
        Args:
            line: Raw line from Claude CLI stdout
            
        Returns:
            Parsed JSON event or None if not JSON
        """
        line = line.strip()
        if not line:
            return None
            
        try:
            event = json.loads(line)
            self._process_event(event)
            return event
        except json.JSONDecodeError:
            # Log non-JSON lines for debugging
            logger.debug(f"Non-JSON line: {line}")
            return None
    
    def process_event(self, event_data: Dict[str, Any]) -> None:
        """Process a pre-parsed JSON event from Claude CLI stream.
        
        Args:
            event_data: Already parsed JSON event data
        """
        if isinstance(event_data, dict):
            self._process_event(event_data)
    
    def _process_event(self, event: Dict[str, Any]) -> None:
        """Process a parsed JSON event to update metrics."""
        if self._store_raw_events:
            self.raw_events.append(event)
        self.metrics.total_events += 1
        
        event_type = event.get("type", "unknown")
        subtype = event.get("subtype", "")
        full_type = f"{event_type}.{subtype}" if subtype else event_type
        
        # Track event types - use dict.get with default for efficiency
        self.metrics.event_types[full_type] = self.metrics.event_types.get(full_type, 0) + 1
        
        # Use handler dispatch table for faster event processing
        handler_key = (event_type, subtype)
        handler = self._event_handlers.get(handler_key)
        if handler:
            handler(event)
        else:
            # Fallback for unknown event types
            handler_key_generic = (event_type, "")
            handler_generic = self._event_handlers.get(handler_key_generic)
            if handler_generic:
                handler_generic(event)
    
    def _process_system_init(self, event: Dict[str, Any]) -> None:
        """Process system initialization event."""
        self.metrics.system_messages += 1
        self.metrics.session_id = event.get("session_id")
        self.metrics.model = event.get("model")
        self.metrics.tools_available = event.get("tools", [])
        self.metrics.mcp_servers = [server.get("name", "") for server in event.get("mcp_servers", [])]
        
        logger.debug(f"Session initialized: {self.metrics.session_id}")
        logger.debug(f"Tools available: {len(self.metrics.tools_available)}")
        logger.debug(f"MCP servers: {len(self.metrics.mcp_servers)}")
    
    def _process_assistant_message(self, event: Dict[str, Any]) -> None:
        """Process assistant message event."""
        self.metrics.assistant_messages += 1
        
        message = event.get("message", {})
        content = message.get("content", [])
        
        # Process usage data if present
        usage = message.get("usage", {})
        if usage:
            self.metrics.total_input_tokens += usage.get("input_tokens", 0)
            self.metrics.total_cache_creation_tokens += usage.get("cache_creation_input_tokens", 0)
            self.metrics.total_cache_read_tokens += usage.get("cache_read_input_tokens", 0)
            self.metrics.total_output_tokens += usage.get("output_tokens", 0)
        
        # Check for tool usage in content - optimize tool name tracking
        for item in content:
            if item.get("type") == "tool_use":
                self.metrics.tool_calls += 1
                tool_name = item.get("name", "unknown")
                # Use set for O(1) lookups instead of O(n) list searches
                if tool_name not in self._known_tool_names:
                    self._known_tool_names.add(tool_name)
                    self.metrics.tool_names_used.append(tool_name)
                logger.debug(f"Tool call detected: {tool_name}")
    
    def _process_user_message(self, event: Dict[str, Any]) -> None:
        """Process user message event."""
        self.metrics.user_messages += 1
        
        message = event.get("message", {})
        content = message.get("content", [])
        
        # Check for tool result errors
        for item in content:
            if item.get("type") == "tool_result" and item.get("is_error"):
                self.metrics.tool_errors += 1
                logger.debug(f"Tool error detected: {item.get('content', 'Unknown error')}")
    
    def _process_result(self, event: Dict[str, Any]) -> None:
        """Process final result event."""
        self.metrics.total_turns = event.get("num_turns", 0)
        self.metrics.total_cost_usd = event.get("total_cost_usd", 0.0)
        self.metrics.duration_ms = event.get("duration_ms", 0)
        self.metrics.duration_api_ms = event.get("duration_api_ms", 0)
        self.metrics.final_result = event.get("result", "")
        self.metrics.is_success = not event.get("is_error", False)
        
        if event.get("is_error"):
            self.metrics.error_message = event.get("result", "Unknown error")
        
        # Process final usage summary
        usage = event.get("usage", {})
        if usage:
            # These are the final totals, so we update (not add to) our counters
            self.metrics.total_input_tokens = usage.get("input_tokens", 0)
            self.metrics.total_cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)
            self.metrics.total_cache_read_tokens = usage.get("cache_read_input_tokens", 0)
            self.metrics.total_output_tokens = usage.get("output_tokens", 0)
        
        self._processing_complete = True
        logger.info(f"Stream processing complete: {self.metrics.total_turns} turns, ${self.metrics.total_cost_usd:.4f}, {self.metrics.tool_calls} tool calls")
    
    def get_metrics(self) -> ClaudeStreamMetrics:
        """Get comprehensive metrics from processed stream."""
        return self.metrics
    
    def get_raw_events(self) -> List[Dict[str, Any]]:
        """Get all raw events from the stream (up to max_events limit)."""
        return list(self.raw_events)
    
    def is_complete(self) -> bool:
        """Check if stream processing is complete."""
        return self._processing_complete
    
    def get_brief_summary(self) -> str:
        """Get a brief summary of the processed stream."""
        if not self._processing_complete:
            return f"Processing... {self.metrics.total_events} events so far"
        
        return (f"Session {self.metrics.session_id}: "
                f"{self.metrics.total_turns} turns, "
                f"{self.metrics.tool_calls} tool calls, "
                f"${self.metrics.total_cost_usd:.4f}, "
                f"{self.metrics.total_tokens:,} tokens, "
                f"{self.metrics.duration_ms}ms")


def process_raw_stream(stream_lines: List[str]) -> Tuple[ClaudeStreamMetrics, List[Dict[str, Any]]]:
    """
    Process a complete raw stream from Claude CLI.
    
    Args:
        stream_lines: List of raw lines from Claude CLI output
        
    Returns:
        Tuple of (metrics, raw_events)
    """
    processor = RawStreamProcessor()
    
    for line in stream_lines:
        processor.process_line(line)
    
    return processor.get_metrics(), processor.get_raw_events()


def extract_metrics_from_log_file(log_file_path: str) -> ClaudeStreamMetrics:
    """
    Extract metrics from a saved Claude CLI log file.
    
    Args:
        log_file_path: Path to the log file
        
    Returns:
        Extracted metrics
    """
    processor = RawStreamProcessor()
    
    try:
        with open(log_file_path, 'r') as f:
            for line in f:
                # Skip comment lines from our test format
                if line.startswith('#') or line.startswith('## '):
                    continue
                    
                # Look for lines that start with numbers (our raw stream format)
                if line.strip() and not line.startswith('000'):
                    continue
                    
                # Extract the JSON part after the line number
                if ': {' in line:
                    json_part = line.split(': ', 1)[1]
                    processor.process_line(json_part)
    
    except Exception as e:
        logger.error(f"Failed to process log file {log_file_path}: {e}")
    
    return processor.get_metrics()


# Example usage for testing
if __name__ == "__main__":
    # Test with a sample event
    test_event = {
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "duration_ms": 32089,
        "duration_api_ms": 35313,
        "num_turns": 12,
        "result": "Test completed successfully",
        "session_id": "test-session-123",
        "total_cost_usd": 0.0661943,
        "usage": {
            "input_tokens": 32,
            "cache_creation_input_tokens": 2018,
            "cache_read_input_tokens": 127204,
            "output_tokens": 804
        }
    }
    
    processor = RawStreamProcessor()
    processor._process_event(test_event)
    
    metrics = processor.get_metrics()
    print("Test metrics:", metrics.to_dict())