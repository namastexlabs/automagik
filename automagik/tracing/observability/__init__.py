"""Observability layer for detailed tracing with external providers."""

from typing import Dict, List, Optional, TYPE_CHECKING
import logging

from ..config import TracingConfig
from ..performance import AdaptiveSampler, SamplingDecision

if TYPE_CHECKING:
    from .base import ObservabilityProvider

logger = logging.getLogger(__name__)


class ObservabilityManager:
    """Manager for observability providers (LangWatch, Langfuse, etc.)."""
    
    def __init__(self, config: TracingConfig):
        """Initialize observability manager.
        
        Args:
            config: Tracing configuration
        """
        self.config = config
        self.providers: Dict[str, 'ObservabilityProvider'] = {}
        self.sampler = AdaptiveSampler(
            base_rate=config.default_sampling_rate,
            error_rate=config.error_sampling_rate,
            slow_threshold_ms=config.slow_threshold_ms
        )
        
        # Initialize configured providers
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize enabled providers based on configuration."""
        for provider_name in self.config.observability_providers:
            try:
                if provider_name == "langwatch":
                    try:
                        from .providers.langwatch import LangWatchProvider
                        provider = LangWatchProvider()
                        provider.initialize({})
                        self.providers[provider_name] = provider
                        logger.info(f"Initialized LangWatch provider")
                    except ImportError:
                        logger.warning("LangWatch provider module not found")
                    
                elif provider_name == "langfuse":
                    try:
                        from .providers.langfuse import LangfuseProvider
                        provider = LangfuseProvider()
                        provider.initialize({})
                        self.providers[provider_name] = provider
                        logger.info(f"Initialized Langfuse provider")
                    except ImportError:
                        logger.warning("Langfuse provider module not found")
                    
                # Add more providers as needed
                
            except Exception as e:
                logger.warning(f"Failed to initialize {provider_name} provider: {e}")
    
    def get_active_providers(self) -> List[str]:
        """Get list of active provider names."""
        return list(self.providers.keys())
    
    def trace_agent_run(self, agent_name: str, session_id: str, message_preview: str):
        """Start tracing an agent run.
        
        Args:
            agent_name: Name of the agent
            session_id: Session ID
            message_preview: Preview of the message
            
        Returns:
            Trace context that can be used with context manager
        """
        from contextlib import contextmanager
        
        @contextmanager
        def trace_context():
            # Start trace with all providers
            contexts = {}
            for name, provider in self.providers.items():
                try:
                    ctx = provider.start_trace(
                        name=f"agent.{agent_name}",
                        kind="agent_run",
                        attributes={
                            "agent.name": agent_name,
                            "session.id": session_id,
                            "message.preview": message_preview[:100] if message_preview else ""
                        }
                    )
                    contexts[name] = ctx.__enter__()
                except Exception as e:
                    logger.debug(f"Failed to start trace with {name}: {e}")
            
            # Yield combined context
            yield contexts
            
            # Clean up all contexts
            for name, ctx in contexts.items():
                try:
                    ctx.__exit__(None, None, None)
                except Exception as e:
                    logger.debug(f"Failed to close trace with {name}: {e}")
        
        return trace_context()
    
    def trace_http_request(self, method: str, path: str, headers: dict = None):
        """Start tracing an HTTP request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: Request path
            headers: Request headers (optional)
            
        Returns:
            Context manager for the trace
        """
        from contextlib import contextmanager
        
        @contextmanager
        def dummy_context():
            # For now, return a simple context that does nothing
            # This will be enhanced when providers are properly integrated
            yield None
            
        return dummy_context()
    
    def shutdown(self):
        """Shutdown all providers gracefully."""
        for name, provider in self.providers.items():
            try:
                provider.shutdown()
                logger.debug(f"Shutdown {name} provider")
            except Exception as e:
                logger.warning(f"Error shutting down {name} provider: {e}")


__all__ = ['ObservabilityManager']