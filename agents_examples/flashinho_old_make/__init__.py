"""Flashinho Old Make Agent - Basic educational assistant for Brazilian students."""

from typing import Dict, Optional
from .agent import FlashinhoOldMakeAgent

def create_agent(config: Optional[Dict[str, str]] = None) -> FlashinhoOldMakeAgent:
    """Factory function to create external Flashinho Old Make agent instance."""
    return FlashinhoOldMakeAgent(config or {})

__all__ = ["FlashinhoOldMakeAgent", "create_agent"]