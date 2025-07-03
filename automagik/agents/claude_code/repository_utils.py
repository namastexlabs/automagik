"""Repository utilities for Claude-Code agent.

This module provides utilities for repository operations including
local copying and remote cloning functionality.
"""
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

from .git_utils import get_current_git_branch, find_repo_root, configure_git_user, checkout_branch

logger = logging.getLogger(__name__)




async def setup_repository(
    workspace: Path,
    branch: Optional[str],
    repository_url: Optional[str] = None
) -> Path:
    """Setup repository in workspace - copy local or clone remote.
    
    Args:
        workspace: Target workspace directory
        branch: Git branch to use (defaults to current branch)
        repository_url: Optional remote repository URL
        
    Returns:
        Path to the repository in the workspace
        
    Raises:
        RuntimeError: If repository setup fails
    """
    # Determine branch (use current if not specified)
    if branch is None:
        branch = await get_current_git_branch()
        if branch is None:
            branch = "main"  # Default fallback
    
    if repository_url:
        # Clone from remote URL (existing behavior)
        return await _clone_remote_repository(workspace, branch, repository_url)
    else:
        # Copy from local repository (new default)
        return await _copy_local_repository(workspace, branch)


async def _copy_local_repository(workspace: Path, branch: str) -> Path:
    """Copy current repository to workspace.
    
    Args:
        workspace: Target workspace directory
        branch: Git branch to checkout
        
    Returns:
        Path to the copied repository
        
    Raises:
        RuntimeError: If copy operation fails
    """
    # Get current repository root
    current_repo = await find_repo_root()
    if not current_repo:
        raise RuntimeError("Not in a git repository")
    
    # Get current branch
    current_branch = await get_current_git_branch()
    if current_branch is None:
        current_branch = "main"
    
    # Target path
    repo_name = current_repo.name
    target_path = workspace / repo_name
    
    # Ensure workspace exists
    workspace.mkdir(parents=True, exist_ok=True)
    
    # Simple rsync - copy everything
    rsync_cmd = [
        "rsync", "-av",
        f"{current_repo}/",
        f"{target_path}/"
    ]
    
    logger.info(f"Copying repository from {current_repo} to {target_path}")
    
    process = await asyncio.create_subprocess_exec(
        *rsync_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"Failed to copy repository: {stderr.decode()}")
    
    # If different branch requested, checkout in the copy
    if branch != current_branch:
        logger.info(f"Checking out branch {branch} in copied repository")
        success = await checkout_branch(target_path, branch)
        if not success:
            # Continue with current branch rather than failing
            logger.warning(f"Continuing with current branch {current_branch}")
    
    # Configure git user for commits
    await configure_git_user(target_path)
    
    logger.info(f"Copied repository to {target_path} on branch {branch}")
    return target_path


async def _clone_remote_repository(
    workspace: Path, 
    branch: str, 
    repository_url: str
) -> Path:
    """Clone repository from remote URL.
    
    Args:
        workspace: Target workspace directory
        branch: Git branch to clone
        repository_url: Remote repository URL
        
    Returns:
        Path to the cloned repository
        
    Raises:
        RuntimeError: If clone operation fails
    """
    # Extract repository name from URL
    repo_name = repository_url.rstrip('/').split('/')[-1]
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    
    target_path = workspace / repo_name
    
    # Ensure workspace exists
    workspace.mkdir(parents=True, exist_ok=True)
    
    # Clone repository
    clone_cmd = ["git", "clone", "-b", branch, repository_url, str(target_path)]
    
    logger.info(f"Cloning repository from {repository_url} branch {branch}")
    
    process = await asyncio.create_subprocess_exec(
        *clone_cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        raise RuntimeError(f"Failed to clone repository: {stderr.decode()}")
    
    # Configure git user for commits
    await configure_git_user(target_path)
    
    logger.info(f"Cloned repository to {target_path} on branch {branch}")
    return target_path


