"""Shared utility functions for Claude Code agent.

This module consolidates common utility functions to avoid duplication
across the codebase.
"""

# Re-export git utilities
from .git_utils import (
    get_current_git_branch,
    get_current_git_branch_sync,
    get_current_git_branch_with_fallback,
    find_repo_root,
    configure_git_user,
    checkout_branch
)

# Re-export stream utilities  
from .stream_utils import (
    parse_json_safely,
    extract_claude_message_content,
    is_claude_stream_event,
    extract_streaming_content,
    parse_claude_stream_line,
    extract_session_id_from_stream,
    StreamProcessingError,
    JSONParsingError
)

# Re-export error handling utilities
from .error_handling import (
    ClaudeCodeError,
    ValidationError,
    ConfigurationError,
    ExecutionError,
    ResourceError,
    handle_exception,
    safe_operation,
    validate_path,
    validate_config,
    log_performance_metrics,
    ensure_cleanup
)