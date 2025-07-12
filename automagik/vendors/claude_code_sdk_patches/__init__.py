"""
Claude Code SDK patches for production safety.

This module applies minimal monkey patches to the official claude-code-sdk
to fix critical issues not yet addressed upstream.

Current patches:
1. Stderr memory limit - Prevents unbounded memory consumption from stderr
"""

from .stderr_memory_patch import apply_stderr_memory_patch

# Apply patches on import
apply_stderr_memory_patch()

__all__ = ["apply_stderr_memory_patch"]