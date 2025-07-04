"""Flashinho Pro Agent - Advanced educational assistant for Brazilian students."""

from typing import Dict, Optional
from .agent import FlashinhoPro

def create_agent(config: Optional[Dict[str, str]] = None) -> FlashinhoPro:
    """Factory function to create external Flashinho Pro agent instance."""
    return FlashinhoPro(config or {})

__all__ = ["FlashinhoPro", "create_agent"]