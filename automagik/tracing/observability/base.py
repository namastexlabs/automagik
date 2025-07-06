"""Base interface for observability providers."""

from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, ContextManager, Dict, List, Optional


@dataclass
class TraceContext:
    """Context for a trace span."""
    trace_id: str
    span_id: str
    attributes: Dict[str, Any]
    sampled: bool = True


class ObservabilityProvider(ABC):
    """Base class for observability providers.
    
    Providers implement this interface to send detailed traces
    to external services like LangWatch, Langfuse, etc.
    """
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the provider with configuration.
        
        Args:
            config: Provider-specific configuration
        """
        pass
    
    @abstractmethod
    @contextmanager
    def start_trace(
        self,
        name: str,
        kind: str,
        attributes: Dict[str, Any]
    ) -> ContextManager[TraceContext]:
        """Start a new trace span.
        
        Args:
            name: Span name
            kind: Span kind (agent_run, tool_call, etc.)
            attributes: Span attributes
            
        Yields:
            TraceContext for the span
        """
        pass
    
    @abstractmethod
    def log_llm_call(
        self,
        model: str,
        messages: List[Dict[str, str]],
        response: Any,
        usage: Dict[str, Any]
    ) -> None:
        """Log LLM interaction with full details.
        
        Args:
            model: Model name
            messages: Input messages
            response: Model response
            usage: Token usage and cost information
        """
        pass
    
    @abstractmethod
    def log_tool_call(
        self,
        tool_name: str,
        args: Dict[str, Any],
        result: Any
    ) -> None:
        """Log tool/function execution.
        
        Args:
            tool_name: Name of the tool
            args: Tool arguments
            result: Tool execution result
        """
        pass
    
    @abstractmethod
    def log_error(
        self,
        error: Exception,
        context: Dict[str, Any]
    ) -> None:
        """Log an error with context.
        
        Args:
            error: The exception
            context: Additional context
        """
        pass
    
    @abstractmethod
    def flush(self) -> None:
        """Flush any pending traces."""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """Cleanup provider resources."""
        pass