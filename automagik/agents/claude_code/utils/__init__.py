"""Utilities for Claude Code agent."""

from .race_condition_helpers import (
    generate_unique_run_id,
    create_workflow_with_retry,
    ensure_unique_worktree_path,
    validate_session_id,
    cleanup_orphaned_worktrees
)

from .worktree_cleanup import (
    WorktreeCleanupService,
    get_cleanup_service,
    cleanup_workflow_worktree,
    cleanup_orphaned_worktrees as cleanup_orphaned_worktrees_new
)

# Import from parent directory git_utils
from ..git_utils import get_current_git_branch_with_fallback

__all__ = [
    'generate_unique_run_id',
    'create_workflow_with_retry', 
    'ensure_unique_worktree_path',
    'validate_session_id',
    'cleanup_orphaned_worktrees',
    'WorktreeCleanupService',
    'get_cleanup_service',
    'cleanup_workflow_worktree',
    'cleanup_orphaned_worktrees_new',
    'get_current_git_branch_with_fallback'
]