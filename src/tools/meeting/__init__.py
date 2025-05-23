"""Meeting AI assistant tools for joining meetings and providing transcription.

This module provides tools for deploying AI assistants that can automatically
join online meetings and provide real-time transcription services.
"""

from .tool import join_meeting_with_url

__all__ = [
    "join_meeting_with_url",
] 