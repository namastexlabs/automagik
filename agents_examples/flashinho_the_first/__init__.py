"""Flashinho The First Agent - Advanced multimodal Brazilian educational assistant."""

from typing import Dict, Optional
from .agent import FlashinhoTheFirst

def create_agent(config: Optional[Dict[str, str]] = None) -> FlashinhoTheFirst:
    """Factory function to create external Flashinho The First agent instance."""
    return FlashinhoTheFirst(config or {})

__all__ = ["FlashinhoTheFirst", "create_agent"]