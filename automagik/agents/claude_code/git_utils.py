"""Git utility functions for Claude Code agent.

This module consolidates all git-related operations to avoid duplication.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, List, Union

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Base exception for git-related errors."""
    pass


class GitCommandError(GitError):
    """Exception raised when git commands fail."""
    
    def __init__(self, message: str, command: List[str], returncode: int, stderr: str = ""):
        self.command = command
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(f"{message}: {' '.join(command)} (exit {returncode})")


class GitRepositoryError(GitError):
    """Exception raised when repository operations fail."""
    pass


async def get_current_git_branch() -> Optional[str]:
    """Get the current git branch name asynchronously.
    
    Returns:
        Current branch name or None if not in a git repository
        
    Raises:
        GitCommandError: If git command fails unexpectedly
    """
    try:
        process = await asyncio.create_subprocess_exec(
            "git", "rev-parse", "--abbrev-ref", "HEAD",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0:
            branch = stdout.decode().strip()
            return branch if branch else None
        return None
    except OSError as e:
        logger.debug(f"Git not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error getting git branch: {e}")
        raise GitCommandError("Failed to get current git branch", ["git", "rev-parse", "--abbrev-ref", "HEAD"], -1, str(e))


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


async def get_git_file_changes(repo_path: Path, base_commit: str = "HEAD~1") -> List[dict]:
    """Get file changes with diffs from git.
    
    Args:
        repo_path: Path to the git repository
        base_commit: Base commit to compare against (default: HEAD~1)
        
    Returns:
        List of file change dictionaries with diff data
    """
    try:
        # First get the list of changed files with stats
        process = await asyncio.create_subprocess_exec(
            "git", "diff", "--name-status", "--numstat", base_commit, "HEAD",
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            logger.warning(f"Failed to get git file changes: {stderr.decode()}")
            return []
        
        # Parse the output to get file statuses
        file_changes = []
        lines = stdout.decode().strip().split('\n')
        
        if not lines or lines == ['']:
            return []
        
        # Get file stats (additions/deletions)
        stats_process = await asyncio.create_subprocess_exec(
            "git", "diff", "--numstat", base_commit, "HEAD",
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stats_stdout, _ = await stats_process.communicate()
        stats_lines = stats_stdout.decode().strip().split('\n')
        
        # Parse stats
        file_stats = {}
        for line in stats_lines:
            if line and '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 3:
                    additions = int(parts[0]) if parts[0] != '-' else 0
                    deletions = int(parts[1]) if parts[1] != '-' else 0
                    filename = parts[2]
                    file_stats[filename] = {'additions': additions, 'deletions': deletions}
        
        # Get status changes
        status_process = await asyncio.create_subprocess_exec(
            "git", "diff", "--name-status", base_commit, "HEAD",
            cwd=str(repo_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        status_stdout, _ = await status_process.communicate()
        status_lines = status_stdout.decode().strip().split('\n')
        
        for line in status_lines:
            if line and '\t' in line:
                parts = line.split('\t')
                if len(parts) >= 2:
                    status_code = parts[0]
                    filename = parts[1]
                    
                    # Map git status codes to our format
                    if status_code == 'A':
                        status = 'added'
                    elif status_code == 'D':
                        status = 'deleted'
                    elif status_code == 'M':
                        status = 'modified'
                    else:
                        status = 'modified'  # default for other codes
                    
                    stats = file_stats.get(filename, {'additions': 0, 'deletions': 0})
                    
                    # Get the actual diff for this file
                    diff_process = await asyncio.create_subprocess_exec(
                        "git", "diff", base_commit, "HEAD", "--", filename,
                        cwd=str(repo_path),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    diff_stdout, _ = await diff_process.communicate()
                    file_diff = diff_stdout.decode()
                    
                    # Get before and after content
                    before_content = ""
                    after_content = ""
                    
                    if status != 'added':
                        # Get file content from base commit
                        before_process = await asyncio.create_subprocess_exec(
                            "git", "show", f"{base_commit}:{filename}",
                            cwd=str(repo_path),
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        before_stdout, before_stderr = await before_process.communicate()
                        if before_process.returncode == 0:
                            before_content = before_stdout.decode()
                    
                    if status != 'deleted':
                        # Get current file content
                        try:
                            with open(repo_path / filename, 'r', encoding='utf-8') as f:
                                after_content = f.read()
                        except Exception as e:
                            logger.warning(f"Could not read current file {filename}: {e}")
                    
                    file_changes.append({
                        'filename': filename,
                        'path': filename,
                        'status': status,
                        'additions': stats['additions'],
                        'deletions': stats['deletions'],
                        'diff': file_diff,
                        'before': before_content,
                        'after': after_content
                    })
        
        return file_changes
        
    except Exception as e:
        logger.error(f"Error getting git file changes: {e}")
        return []