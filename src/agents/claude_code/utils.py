"""Shared utility functions for Claude Code agent.

This module consolidates common utility functions to avoid duplication
across the codebase.
"""

# Re-export git utilities for backward compatibility
from .git_utils import (
    get_current_git_branch,
    get_current_git_branch_sync,
    get_current_git_branch_with_fallback,
    find_repo_root,
    configure_git_user,
    checkout_branch
)

# Re-export stream utilities for backward compatibility  
from .stream_utils import (
    parse_json_safely,
    extract_claude_message_content,
    is_claude_stream_event,
    extract_streaming_content,
    parse_claude_stream_line,
    extract_session_id_from_stream
)