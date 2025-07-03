"""External Flashinho Pro agent factory."""

from typing import Dict, Optional
from .agent import FlashinhoProExternal

def create_agent(config: Optional[Dict[str, str]] = None) -> FlashinhoProExternal:
    """Factory function to create external Flashinho Pro agent instance."""
    return FlashinhoProExternal(config or {})