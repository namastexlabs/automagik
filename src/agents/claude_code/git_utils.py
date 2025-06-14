"""Git utility functions for Claude Code agent.

This module consolidates all git-related operations to avoid duplication.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)


async def get_current_git_branch() -> Optional[str]:
    """Get the current git branch name asynchronously.
    
    Returns:
        Current branch name or None if not in a git repository
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--abbrev-ref", "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return stdout.decode().strip()
        return None
    except Exception as e:
        logger.debug(f"Failed to get current git branch: {e}")
        return None


def get_current_git_branch_sync() -> Optional[str]:
    """Get the current git branch name synchronously.
    
    Returns:
        Current branch name or None if not in a git repository
    """
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        logger.debug(f"Failed to get current git branch: {e}")
        return None


async def get_current_git_branch_with_fallback() -> str:
    """Get the current git branch with fallback to 'main'.
    
    Returns:
        Current git branch name, or 'main' as fallback
    """
    try:
        branch = await get_current_git_branch()
        return branch if branch else "main"
    except Exception as e:
        logger.warning(f"Failed to get current git branch: {e}, defaulting to 'main'")
        return "main"


async def find_repo_root() -> Optional[Path]:
    """Find the root of the current git repository.
    
    Returns:
        Path to repository root or None if not in a git repository
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--show-toplevel",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            return Path(stdout.decode().strip())
        return None
    except Exception:
        return None


async def configure_git_user(repo_path: Path, name: str = "Claude Code Agent", 
                           email: str = "claude@automagik-agents.com") -> bool:
    """Configure git user settings for a repository.
    
    Args:
        repo_path: Path to the git repository
        name: Git user name to set
        email: Git user email to set
        
    Returns:
        True if configuration was successful, False otherwise
    """
    git_config_cmds = [
        ["git", "config", "user.name", name],
        ["git", "config", "user.email", email],
        ["git", "config", "commit.gpgsign", "false"]
    ]
    
    try:
        for cmd in git_config_cmds:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.warning(f"Git config command failed: {' '.join(cmd)}, error: {stderr.decode()}")
                return False
        
        logger.debug(f"Git user configured for {repo_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to configure git user for {repo_path}: {e}")
        return False


async def checkout_branch(repo_path: Path, branch: str) -> bool:
    """Checkout a git branch in the repository.
    
    Args:
        repo_path: Path to the git repository
        branch: Branch name to checkout
        
    Returns:
        True if checkout was successful, False otherwise
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "git", "checkout", branch,
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            logger.debug(f"Checked out branch {branch} in {repo_path}")
            return True
        else:
            logger.warning(f"Failed to checkout branch {branch}: {stderr.decode()}")
            return False
            
    except Exception as e:
        logger.error(f"Error checking out branch {branch}: {e}")
        return False