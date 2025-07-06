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
        from .core import TracingManager
        _tracing_manager = TracingManager()
    
    return _tracing_manager


__all__ = ['get_tracing_manager']