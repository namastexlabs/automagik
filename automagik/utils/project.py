"""Project utilities for path resolution and configuration."""

import os
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory.
    
    Searches up from the current file location for project indicators
    like pyproject.toml or .env files to determine the project root.
    
    Returns:
        Path: The project root directory
    """
    current = Path(__file__).resolve()
    while current.parent != current:
        if (current / "pyproject.toml").exists() or (current / ".env").exists():
            return current
        current = current.parent
    return Path.cwd()


def get_worktrees_dir() -> Path:
    """Get the worktrees directory relative to project root.
    
    Returns:
        Path: The worktrees directory path
    """
    return get_project_root() / "worktrees"


def get_workspace_path(run_id: str, workflow_name: str = "builder", branch: str = "main") -> Path:
    """Generate workspace path for a workflow run.
    
    Args:
        run_id: Unique identifier for the workflow run
        workflow_name: Name of the workflow (default: builder)
        branch: Git branch name (default: main)
        
    Returns:
        Path: The workspace directory path
    """
    worktrees_dir = get_worktrees_dir()
    return worktrees_dir / f"{branch}-{workflow_name}-{run_id[:8]}"


def get_temp_workspace_path(run_id: str, user_id: str = "default") -> Path:
    """Generate temporary workspace path for isolated execution.
    
    Args:
        run_id: Unique identifier for the workflow run
        user_id: User identifier (default: default)
        
    Returns:
        Path: The temporary workspace directory path
    """
    return Path("/tmp") / "claude-code-temp" / user_id / f"workspace_{run_id}"


def resolve_workspace_from_run_id(run_id: str) -> list[Path]:
    """Find all workspace directories that match a run_id.
    
    Searches both worktrees and temp workspaces for directories
    containing the run_id.
    
    Args:
        run_id: Unique identifier for the workflow run
        
    Returns:
        list[Path]: List of workspace paths found
    """
    workspace_candidates = []
    
    # Check worktree workspaces
    worktrees_dir = get_worktrees_dir()
    if worktrees_dir.exists():
        for workspace_dir in worktrees_dir.iterdir():
            if workspace_dir.is_dir() and run_id[:8] in workspace_dir.name:
                workspace_candidates.append(workspace_dir)
    
    # Check temp workspaces
    temp_base = Path("/tmp/claude-code-temp")
    if temp_base.exists():
        # Check direct run_id directories
        direct_temp_workspace = temp_base / run_id
        if direct_temp_workspace.exists():
            workspace_candidates.append(direct_temp_workspace)
        
        # Check nested user directories (legacy pattern)
        for user_dir in temp_base.iterdir():
            if user_dir.is_dir() and user_dir.name != run_id:
                temp_workspace = user_dir / f"workspace_{run_id}"
                if temp_workspace.exists():
                    workspace_candidates.append(temp_workspace)
    
    return workspace_candidates