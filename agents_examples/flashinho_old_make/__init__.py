"""Flashinho Old Make Agent - Basic educational assistant for Brazilian students."""

from typing import Dict, Optional
from .agent import FlashinhoOldMakeAgentRefactored

def create_agent(config: Optional[Dict[str, str]] = None) -> FlashinhoOldMakeAgentRefactored:
    """Factory function to create external Flashinho Old Make agent instance."""
    return FlashinhoOldMakeAgentRefactored(config or {})

__all__ = ["FlashinhoOldMakeAgentRefactored", "create_agent"]