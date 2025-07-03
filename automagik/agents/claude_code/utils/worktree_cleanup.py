"""Git worktree cleanup utilities for Claude Code workflows.

This module provides automated cleanup functionality for git worktrees
created during workflow execution, including orphaned worktree detection
and periodic cleanup scheduling.
"""

import asyncio
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Set

from automagik.db.repository.workflow_run import (
    get_workflow_run_by_run_id,
    update_workflow_run_by_run_id,
    list_workflow_runs
)
from automagik.db.models import WorkflowRunUpdate

logger = logging.getLogger(__name__)


class WorktreeCleanupService:
    """Service for automated git worktree cleanup."""
    
    def __init__(self, base_repo_path: Path = None):
        """Initialize the cleanup service.
        
        Args:
            base_repo_path: Base repository path (defaults to current working directory)
        """
        self.base_repo_path = base_repo_path or Path.cwd()
        self.worktrees_dir = self.base_repo_path / "worktrees"
        self._cleanup_lock = asyncio.Lock()
        
    async def cleanup_on_workflow_completion(self, run_id: str, force: bool = False) -> bool:
        """Clean up worktree after workflow completion.
        
        This should be called when a workflow completes (successfully or with error).
        
        Args:
            run_id: The workflow run ID
            force: Force cleanup even for persistent workspaces
            
        Returns:
            True if cleanup was successful or not needed, False otherwise
        """
        async with self._cleanup_lock:
            try:
                # Get workflow run info
                workflow_run = get_workflow_run_by_run_id(run_id)
                if not workflow_run:
                    logger.warning(f"No workflow run found for {run_id}")
                    return False
                
                # Skip if already cleaned up
                if workflow_run.workspace_cleaned_up:
                    logger.info(f"Workspace for {run_id} already cleaned up")
                    return True
                
                # Skip persistent workspaces unless forced
                if workflow_run.workspace_persistent and not force:
                    logger.info(f"Skipping cleanup for persistent workspace {run_id}")
                    return True
                
                # Get workspace path
                workspace_path = workflow_run.workspace_path
                if not workspace_path:
                    logger.warning(f"No workspace path recorded for {run_id}")
                    return True  # Nothing to clean up
                
                workspace_path = Path(workspace_path)
                
                # Perform cleanup
                success = await self._cleanup_worktree(workspace_path)
                
                # Update database
                if success:
                    update_data = WorkflowRunUpdate(
                        workspace_cleaned_up=True,
                        updated_at=datetime.utcnow()
                    )
                    update_workflow_run_by_run_id(run_id, update_data)
                    logger.info(f"Successfully cleaned up worktree for {run_id}")
                
                return success
                
            except Exception as e:
                logger.error(f"Error cleaning up worktree for {run_id}: {e}")
                return False
    
    async def cleanup_orphaned_worktrees(self, max_age_hours: int = 48, dry_run: bool = False) -> Dict[str, Any]:
        """Clean up orphaned worktrees that weren't properly cleaned up.
        
        Args:
            max_age_hours: Maximum age in hours before considering a worktree orphaned
            dry_run: If True, only report what would be cleaned up
            
        Returns:
            Dictionary with cleanup results
        """
        results = {
            "total_worktrees": 0,
            "orphaned": [],
            "cleaned_up": [],
            "failed": [],
            "skipped": [],
            "dry_run": dry_run
        }
        
        if not self.worktrees_dir.exists():
            logger.info("No worktrees directory found")
            return results
        
        # Get all worktrees
        worktrees = await self._list_git_worktrees()
        results["total_worktrees"] = len(worktrees)
        
        # Get active workflow runs
        active_runs = await self._get_active_workflow_runs()
        active_paths = {run.workspace_path for run in active_runs if run.workspace_path}
        
        # Check each worktree
        for worktree in worktrees:
            worktree_path = Path(worktree["path"])
            
            # Skip if path doesn't exist
            if not worktree_path.exists():
                logger.debug(f"Worktree path doesn't exist: {worktree_path}")
                continue
            
            # Check if worktree is associated with an active run
            if str(worktree_path) in active_paths:
                results["skipped"].append({
                    "path": str(worktree_path),
                    "reason": "active_workflow"
                })
                continue
            
            # Check age
            age_hours = await self._get_worktree_age_hours(worktree_path)
            if age_hours < max_age_hours:
                results["skipped"].append({
                    "path": str(worktree_path),
                    "reason": f"too_recent ({age_hours:.1f}h < {max_age_hours}h)"
                })
                continue
            
            # Check if persistent
            if await self._is_persistent_worktree(worktree_path):
                results["skipped"].append({
                    "path": str(worktree_path),
                    "reason": "persistent"
                })
                continue
            
            # Mark as orphaned
            results["orphaned"].append({
                "path": str(worktree_path),
                "branch": worktree.get("branch", "unknown"),
                "age_hours": age_hours
            })
            
            # Clean up if not dry run
            if not dry_run:
                success = await self._cleanup_worktree(worktree_path)
                if success:
                    results["cleaned_up"].append(str(worktree_path))
                else:
                    results["failed"].append(str(worktree_path))
        
        # Prune git worktree list to remove stale entries
        if not dry_run and (results["cleaned_up"] or results["failed"]):
            await self._prune_worktree_list()
        
        return results
    
    async def _cleanup_worktree(self, worktree_path: Path) -> bool:
        """Clean up a single worktree.
        
        Args:
            worktree_path: Path to the worktree
            
        Returns:
            True if cleanup successful, False otherwise
        """
        try:
            # First try git worktree remove
            process = await asyncio.create_subprocess_exec(
                "git", "worktree", "remove", str(worktree_path), "--force",
                cwd=str(self.base_repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info(f"Successfully removed worktree: {worktree_path}")
                return True
            else:
                logger.warning(f"Git worktree remove failed: {stderr.decode()}")
                
                # Try manual removal as fallback
                import shutil
                if worktree_path.exists():
                    shutil.rmtree(worktree_path, ignore_errors=True)
                    logger.info(f"Manually removed worktree directory: {worktree_path}")
                
                # Prune to clean up git references
                await self._prune_worktree_list()
                return True
                
        except Exception as e:
            logger.error(f"Error removing worktree {worktree_path}: {e}")
            return False
    
    async def _list_git_worktrees(self) -> List[Dict[str, str]]:
        """List all git worktrees.
        
        Returns:
            List of worktree info dictionaries
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "worktree", "list", "--porcelain",
                cwd=str(self.base_repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                logger.error(f"Failed to list worktrees: {stderr.decode()}")
                return []
            
            # Parse worktree list output
            worktrees = []
            current_worktree = {}
            
            for line in stdout.decode().strip().split('\n'):
                if not line:
                    if current_worktree:
                        worktrees.append(current_worktree)
                        current_worktree = {}
                elif line.startswith("worktree "):
                    current_worktree["path"] = line[9:]
                elif line.startswith("branch "):
                    current_worktree["branch"] = line[7:]
                elif line.startswith("HEAD "):
                    current_worktree["head"] = line[5:]
            
            # Don't forget the last worktree
            if current_worktree:
                worktrees.append(current_worktree)
            
            return worktrees
            
        except Exception as e:
            logger.error(f"Error listing worktrees: {e}")
            return []
    
    async def _prune_worktree_list(self) -> None:
        """Prune the git worktree list to remove stale entries."""
        try:
            process = await asyncio.create_subprocess_exec(
                "git", "worktree", "prune",
                cwd=str(self.base_repo_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                logger.info("Successfully pruned git worktree list")
            else:
                logger.warning(f"Git worktree prune warning: {stderr.decode()}")
                
        except Exception as e:
            logger.error(f"Error pruning worktree list: {e}")
    
    async def _get_active_workflow_runs(self) -> List[Any]:
        """Get all active (running/pending) workflow runs.
        
        Returns:
            List of active workflow runs
        """
        try:
            # Get running workflows
            running_runs, _ = list_workflow_runs(
                filters={"status": "running"},
                page_size=100
            )
            
            # Get pending workflows
            pending_runs, _ = list_workflow_runs(
                filters={"status": "pending"},
                page_size=100
            )
            
            return running_runs + pending_runs
            
        except Exception as e:
            logger.error(f"Error getting active workflow runs: {e}")
            return []
    
    async def _get_worktree_age_hours(self, worktree_path: Path) -> float:
        """Get the age of a worktree in hours.
        
        Args:
            worktree_path: Path to the worktree
            
        Returns:
            Age in hours
        """
        try:
            # Check directory modification time
            if worktree_path.exists():
                mtime = worktree_path.stat().st_mtime
                age_seconds = datetime.now().timestamp() - mtime
                return age_seconds / 3600
            return 0
            
        except Exception as e:
            logger.error(f"Error getting worktree age: {e}")
            return 0
    
    async def _is_persistent_worktree(self, worktree_path: Path) -> bool:
        """Check if a worktree is marked as persistent.
        
        Args:
            worktree_path: Path to the worktree
            
        Returns:
            True if persistent, False otherwise
        """
        # Check for .persistent marker file
        if (worktree_path / ".persistent").exists():
            return True
        
        # Check naming patterns
        name_lower = worktree_path.name.lower()
        persistent_patterns = ["persistent", "main", "permanent", "long-term"]
        
        for pattern in persistent_patterns:
            if pattern in name_lower:
                return True
        
        # Check if it's the main branch worktree
        if "main" in name_lower or "master" in name_lower:
            return True
        
        return False


# Singleton instance
_cleanup_service = None


def get_cleanup_service(base_repo_path: Path = None) -> WorktreeCleanupService:
    """Get the singleton cleanup service instance.
    
    Args:
        base_repo_path: Base repository path
        
    Returns:
        WorktreeCleanupService instance
    """
    global _cleanup_service
    if _cleanup_service is None:
        _cleanup_service = WorktreeCleanupService(base_repo_path)
    return _cleanup_service


async def cleanup_workflow_worktree(run_id: str, force: bool = False) -> bool:
    """Convenience function to clean up a workflow's worktree.
    
    Args:
        run_id: The workflow run ID
        force: Force cleanup even for persistent workspaces
        
    Returns:
        True if cleanup successful, False otherwise
    """
    service = get_cleanup_service()
    return await service.cleanup_on_workflow_completion(run_id, force)


async def cleanup_orphaned_worktrees(max_age_hours: int = 48, dry_run: bool = False) -> Dict[str, Any]:
    """Convenience function to clean up orphaned worktrees.
    
    Args:
        max_age_hours: Maximum age before considering orphaned
        dry_run: If True, only report what would be cleaned
        
    Returns:
        Cleanup results dictionary
    """
    service = get_cleanup_service()
    return await service.cleanup_orphaned_worktrees(max_age_hours, dry_run)