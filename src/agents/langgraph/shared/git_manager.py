"""Git Management and Rollback System for LangGraph orchestration.

This module provides git snapshot and rollback functionality for workspace management,
including destructive rollbacks to "unfuck" hallucinations and track rollback history.
"""

import asyncio
import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger(__name__)

class GitOperationError(Exception):
    """Exception raised when git operations fail."""
    pass

class GitManager:
    """Git snapshot and rollback system for workspace management."""
    
    def __init__(self):
        """Initialize git manager."""
        pass
    
    async def snapshot_workspace(self, workspace_path: str, message: str = None) -> str:
        """Create a git snapshot of the workspace.
        
        Args:
            workspace_path: Path to the workspace
            message: Optional commit message
            
        Returns:
            Commit SHA of the snapshot
            
        Raises:
            GitOperationError: If snapshot creation fails
        """
        try:
            workspace_path = Path(workspace_path)
            
            # Ensure it's a git repository
            if not (workspace_path / '.git').exists():
                await self._init_repository(workspace_path)
            
            # Check if there are changes to commit
            has_changes = await self._has_uncommitted_changes(workspace_path)
            
            if not has_changes:
                # No changes, return current HEAD
                return await self._get_current_sha(workspace_path)
            
            # Add all changes
            await self._run_git_command(
                ["add", "-A"],
                workspace_path
            )
            
            # Create commit with timestamp
            if not message:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = f"Orchestration snapshot - {timestamp}"
            
            await self._run_git_command(
                ["commit", "-m", message],
                workspace_path
            )
            
            # Get the new commit SHA
            sha = await self._get_current_sha(workspace_path)
            logger.info(f"Created workspace snapshot {sha} in {workspace_path}")
            
            return sha
            
        except Exception as e:
            logger.error(f"Failed to create workspace snapshot: {str(e)}")
            raise GitOperationError(f"Snapshot creation failed: {str(e)}")
    
    async def rollback_workspace(
        self, 
        workspace_path: str, 
        target_sha: str, 
        reason: str
    ) -> bool:
        """Perform destructive rollback to target commit.
        
        Args:
            workspace_path: Path to the workspace
            target_sha: Target commit SHA to rollback to
            reason: Reason for the rollback
            
        Returns:
            True if rollback successful, False otherwise
            
        Raises:
            GitOperationError: If rollback fails
        """
        try:
            workspace_path = Path(workspace_path)
            
            # Verify target SHA exists
            if not await self._commit_exists(workspace_path, target_sha):
                raise GitOperationError(f"Target commit {target_sha} does not exist")
            
            # Get current SHA for logging
            current_sha = await self._get_current_sha(workspace_path)
            
            logger.warning(
                f"Performing DESTRUCTIVE rollback in {workspace_path}\n"
                f"From: {current_sha}\n"
                f"To: {target_sha}\n"
                f"Reason: {reason}"
            )
            
            # Perform hard reset
            await self._run_git_command(
                ["reset", "--hard", target_sha],
                workspace_path
            )
            
            # Clean untracked files
            await self._run_git_command(
                ["clean", "-fd"],
                workspace_path
            )
            
            logger.info(f"Rollback completed successfully to {target_sha}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed: {str(e)}")
            raise GitOperationError(f"Rollback operation failed: {str(e)}")
    
    async def get_commit_diff(
        self, 
        workspace_path: str, 
        from_sha: str, 
        to_sha: str
    ) -> str:
        """Get diff between two commits.
        
        Args:
            workspace_path: Path to the workspace
            from_sha: Source commit SHA
            to_sha: Target commit SHA
            
        Returns:
            Diff output as string
        """
        try:
            result = await self._run_git_command(
                ["diff", from_sha, to_sha],
                workspace_path
            )
            return result
            
        except Exception as e:
            logger.error(f"Failed to get commit diff: {str(e)}")
            return f"Error getting diff: {str(e)}"
    
    def prepare_rollback_context(self, commit_sha: str, reason: str) -> str:
        """Prepare rollback context message for agent prompts.
        
        Args:
            commit_sha: Commit that was rolled back
            reason: Reason for rollback
            
        Returns:
            Formatted context message
        """
        return f"""
🔄 ROLLBACK PERFORMED

The following commit {commit_sha} has been reverted by the user.
Reason: {reason}

Analyze what happened in that commit to avoid repeating the same mistakes.
Previous attempt failed due to: {reason}

Continue with the original task, but implement it differently.
Consider the following:
1. What went wrong in the previous approach?
2. How can you avoid the same issue?
3. What alternative approach should be taken?

Please acknowledge the rollback and proceed with a corrected approach.
"""
    
    async def list_uncommitted_changes(self, workspace_path: str) -> List[str]:
        """List uncommitted changes in the workspace.
        
        Args:
            workspace_path: Path to the workspace
            
        Returns:
            List of changed files
        """
        try:
            # Get status output
            status_output = await self._run_git_command(
                ["status", "--porcelain"],
                workspace_path
            )
            
            if not status_output.strip():
                return []
            
            changes = []
            for line in status_output.strip().split('\n'):
                if line.strip():
                    # Parse git status format: "XY filename"
                    status = line[:2]
                    filename = line[3:]
                    changes.append(f"{status} {filename}")
            
            return changes
            
        except Exception as e:
            logger.error(f"Failed to list uncommitted changes: {str(e)}")
            return [f"Error: {str(e)}"]
    
    async def get_recent_commits(self, workspace_path: str, count: int = 10) -> List[Dict[str, str]]:
        """Get recent commits for the workspace.
        
        Args:
            workspace_path: Path to the workspace
            count: Number of commits to retrieve
            
        Returns:
            List of commit info dictionaries
        """
        try:
            # Get commit log with format
            log_output = await self._run_git_command(
                ["log", f"-{count}", "--pretty=format:%H|%an|%ad|%s", "--date=short"],
                workspace_path
            )
            
            commits = []
            for line in log_output.strip().split('\n'):
                if line.strip():
                    parts = line.split('|', 3)
                    if len(parts) == 4:
                        commits.append({
                            "sha": parts[0],
                            "author": parts[1],
                            "date": parts[2],
                            "message": parts[3]
                        })
            
            return commits
            
        except Exception as e:
            logger.error(f"Failed to get recent commits: {str(e)}")
            return []
    
    async def create_branch(self, workspace_path: str, branch_name: str) -> bool:
        """Create a new git branch.
        
        Args:
            workspace_path: Path to the workspace
            branch_name: Name of the new branch
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._run_git_command(
                ["checkout", "-b", branch_name],
                workspace_path
            )
            logger.info(f"Created branch {branch_name} in {workspace_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create branch {branch_name}: {str(e)}")
            return False
    
    async def checkout_branch(self, workspace_path: str, branch_name: str) -> bool:
        """Checkout an existing git branch.
        
        Args:
            workspace_path: Path to the workspace
            branch_name: Name of the branch to checkout
            
        Returns:
            True if successful, False otherwise
        """
        try:
            await self._run_git_command(
                ["checkout", branch_name],
                workspace_path
            )
            logger.info(f"Checked out branch {branch_name} in {workspace_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to checkout branch {branch_name}: {str(e)}")
            return False
    
    # Private helper methods
    
    async def _init_repository(self, workspace_path: Path) -> None:
        """Initialize git repository if it doesn't exist.
        
        Args:
            workspace_path: Path to initialize
        """
        await self._run_git_command(["init"], workspace_path)
        
        # Configure user if not set
        try:
            await self._run_git_command(
                ["config", "user.email", "orchestration@automagik-agents.local"],
                workspace_path
            )
            await self._run_git_command(
                ["config", "user.name", "LangGraph Orchestrator"],
                workspace_path
            )
        except:
            # Ignore config errors, might already be set globally
            pass
        
        logger.info(f"Initialized git repository in {workspace_path}")
    
    async def _has_uncommitted_changes(self, workspace_path: Path) -> bool:
        """Check if workspace has uncommitted changes.
        
        Args:
            workspace_path: Path to check
            
        Returns:
            True if there are uncommitted changes
        """
        try:
            result = await self._run_git_command(
                ["status", "--porcelain"],
                workspace_path
            )
            return bool(result.strip())
            
        except Exception:
            # If status fails, assume there are changes
            return True
    
    async def _get_current_sha(self, workspace_path: Path) -> str:
        """Get current HEAD commit SHA.
        
        Args:
            workspace_path: Path to workspace
            
        Returns:
            Current commit SHA
        """
        result = await self._run_git_command(
            ["rev-parse", "HEAD"],
            workspace_path
        )
        return result.strip()
    
    async def _commit_exists(self, workspace_path: Path, sha: str) -> bool:
        """Check if a commit SHA exists in the repository.
        
        Args:
            workspace_path: Path to workspace
            sha: Commit SHA to check
            
        Returns:
            True if commit exists
        """
        try:
            await self._run_git_command(
                ["cat-file", "-e", sha],
                workspace_path
            )
            return True
        except:
            return False
    
    async def _run_git_command(
        self, 
        args: List[str], 
        workspace_path: Path
    ) -> str:
        """Run a git command in the workspace.
        
        Args:
            args: Git command arguments
            workspace_path: Working directory
            
        Returns:
            Command output
            
        Raises:
            GitOperationError: If command fails
        """
        try:
            cmd = ["git"] + args
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(workspace_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=os.environ.copy()
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='replace').strip()
                raise GitOperationError(f"Git command failed: {' '.join(cmd)}\nError: {error_msg}")
            
            return stdout.decode('utf-8', errors='replace')
            
        except GitOperationError:
            raise
        except Exception as e:
            raise GitOperationError(f"Failed to execute git command: {str(e)}") 