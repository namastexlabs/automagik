"""Core tracing manager that coordinates all tracing systems."""

import logging
from typing import Optional, TYPE_CHECKING

from .config import TracingConfig

if TYPE_CHECKING:
    from .observability import ObservabilityManager
    from .telemetry import TelemetryCollector

logger = logging.getLogger(__name__)


class TracingManager:
    """Central manager for all tracing systems.
    
    This manager coordinates between:
    - Observability providers (LangWatch, Langfuse, etc.) for detailed traces
    - Telemetry collection for anonymous usage analytics
    """
    
    def __init__(self):
        """Initialize the tracing manager with lazy loading."""
        self.config = TracingConfig.from_env()
        self._observability: Optional['ObservabilityManager'] = None
        self._telemetry: Optional['TelemetryCollector'] = None
        self._initialized = False
        
        # Log configuration on startup
        self._log_startup_status()
    
    def _log_startup_status(self):
        """Log tracing configuration at startup."""
        if self.config.disable_all_tracing:
            logger.info("📊 Tracing is DISABLED")
            return
            
        if self.config.observability_enabled:
            providers = self.config.observability_providers
            if providers:
                logger.info(f"🔭 Observability enabled with providers: {', '.join(providers)}")
            else:
                logger.info("🔭 Observability enabled but no providers configured")
                
        if self.config.telemetry_enabled:
            logger.info("📈 Usage telemetry enabled (anonymous analytics)")
    
    @property
    def observability(self) -> Optional['ObservabilityManager']:
        """Get observability manager (lazy loaded)."""
        if self._observability is None:
            logger.info(f"🔍 Observability check - enabled: {self.config.observability_enabled}, providers: {self.config.observability_providers}")
            if self.config.observability_enabled and self.config.observability_providers:
                try:
                    from .observability import ObservabilityManager
                    logger.info("📊 Creating ObservabilityManager...")
                    self._observability = ObservabilityManager(self.config)
                    logger.info(f"✅ Observability manager initialized with providers: {list(self._observability.providers.keys()) if self._observability else 'None'}")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize observability: {e}", exc_info=True)
                    self._observability = None
        return self._observability
    
    @property
    def telemetry(self) -> Optional['TelemetryCollector']:
        """Get telemetry collector (lazy loaded)."""
        if self._telemetry is None:
            if self.config.telemetry_enabled:
                try:
                    from .telemetry import TelemetryCollector
                    self._telemetry = TelemetryCollector(self.config)
                    logger.info(f"📊 Telemetry collector initialized - endpoint: {self.config.telemetry_endpoint}")
                except Exception as e:
                    logger.warning(f"Failed to initialize telemetry: {e}")
                    self._telemetry = None
        return self._telemetry
    
    def shutdown(self):
        """Shutdown all tracing systems gracefully."""
        if self._observability:
            try:
                self._observability.shutdown()
                logger.debug("Observability manager shutdown")
            except Exception as e:
                logger.warning(f"Error during observability shutdown: {e}")
                
        if self._telemetry:
            try:
                self._telemetry.shutdown()
                logger.debug("Telemetry collector shutdown")
            except Exception as e:
                logger.warning(f"Error during telemetry shutdown: {e}")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure cleanup."""
        self.shutdown()
        return False