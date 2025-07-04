"""Flashinho The First Agent - Advanced multimodal Brazilian educational assistant."""

from typing import Dict, Optional
from .agent import FlashinhoTheFirstRefactored

def create_agent(config: Optional[Dict[str, str]] = None) -> FlashinhoTheFirstRefactored:
    """Factory function to create external Flashinho The First agent instance."""
    return FlashinhoTheFirstRefactored(config or {})

__all__ = ["FlashinhoTheFirstRefactored", "create_agent"]