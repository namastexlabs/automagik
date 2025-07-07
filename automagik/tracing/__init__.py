"""Automagik Tracing System.

Provides both observability (detailed traces) and telemetry (anonymous usage) capabilities.
"""

from typing import Optional

# Global tracing manager instance
_tracing_manager: Optional['TracingManager'] = None


def get_tracing_manager() -> 'TracingManager':
    """Get or create the global tracing manager."""
    global _tracing_manager
    
    if _tracing_manager is None:
        import os
        import logging
        logger = logging.getLogger(__name__)
        
        # Check if tracing is enabled
        enabled = os.environ.get('AUTOMAGIK_TRACING_ENABLED', 'true').lower() == 'true'
        logger.info(f"🔍 Tracing initialization - enabled: {enabled}, env: {os.environ.get('AUTOMAGIK_TRACING_ENABLED', 'not set')}")
        
        from .core import TracingManager
        logger.info("🚀 Creating TracingManager instance...")
        _tracing_manager = TracingManager()
        logger.info(f"✅ TracingManager created: {_tracing_manager}")
    
    return _tracing_manager


# Export decorators for convenience
try:
    from .decorators import trace_cli_command, trace_async_cli_command, trace_function
    __all__ = [
        'get_tracing_manager',
        'trace_cli_command',
        'trace_async_cli_command',
        'trace_function'
    ]
except ImportError:
    # If decorators module doesn't exist yet, just export the manager
    __all__ = ['get_tracing_manager']