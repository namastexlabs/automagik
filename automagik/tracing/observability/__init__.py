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
                    from .providers.langwatch import LangWatchProvider
                    provider = LangWatchProvider()
                    provider.initialize({})
                    self.providers[provider_name] = provider
                    logger.info(f"Initialized LangWatch provider")
                    
                elif provider_name == "langfuse":
                    from .providers.langfuse import LangfuseProvider
                    provider = LangfuseProvider()
                    provider.initialize({})
                    self.providers[provider_name] = provider
                    logger.info(f"Initialized Langfuse provider")
                    
                # Add more providers as needed
                
            except Exception as e:
                logger.warning(f"Failed to initialize {provider_name} provider: {e}")
    
    def get_active_providers(self) -> List[str]:
        """Get list of active provider names."""
        return list(self.providers.keys())
    
    def trace_agent_run(self, agent_name: str, session_id: str, message_preview: str):
        """Start tracing an agent run."""
        # Implementation would create spans with all providers
        pass
    
    def shutdown(self):
        """Shutdown all providers gracefully."""
        for name, provider in self.providers.items():
            try:
                provider.shutdown()
                logger.debug(f"Shutdown {name} provider")
            except Exception as e:
                logger.warning(f"Error shutting down {name} provider: {e}")


__all__ = ['ObservabilityManager']