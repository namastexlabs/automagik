"""External Flashinho Pro agent factory."""

from typing import Dict, Optional
from .agent import FlashinhoProExternalRefactored

def create_agent(config: Optional[Dict[str, str]] = None) -> FlashinhoProExternalRefactored:
    """Factory function to create external Flashinho Pro agent instance."""
    return FlashinhoProExternalRefactored(config or {})