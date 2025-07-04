"""Utilities for external agents.

This module provides utility functions and classes for external agents.
"""

from .user_matcher import FlashinhoProUserMatcher
from .memory_manager import (
    initialize_flashinho_pro_memories,
    update_flashinho_pro_memories
)

__all__ = [
    "FlashinhoProUserMatcher",
    "initialize_flashinho_pro_memories",
    "update_flashinho_pro_memories",
]