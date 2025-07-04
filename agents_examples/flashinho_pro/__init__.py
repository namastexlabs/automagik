"""Flashinho Pro Agent - Advanced educational assistant for Brazilian students."""

from typing import Dict, Optional
from .agent import FlashinhoProRefactored

def create_agent(config: Optional[Dict[str, str]] = None) -> FlashinhoProRefactored:
    """Factory function to create external Flashinho Pro agent instance."""
    return FlashinhoProRefactored(config or {})

__all__ = ["FlashinhoProRefactored", "create_agent"]