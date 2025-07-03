"""Workspace management service for workflow run lifecycle tracking.

This service provides utilities for workspace lifecycle management, cleanup,
and integration with the workflow_runs tracking system.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


@dataclass
class WorkspaceInfo:
    """Workspace information and status."""
    path: Path
    workspace_id: str
    age_hours: float
    size_mb: float = 0.0
    is_persistent: bool = False
    last_run_id: Optional[str] = None
    status: str = "unknown"  # active, completed, abandoned


class WorkspaceService:
    """Service for workspace lifecycle management."""
    
    def __init__(self, worktrees_base: Path = None):
        """Initialize workspace service.
        
        Args:
            worktrees_base: Base directory for worktrees (default: ./worktrees)
        """
        self.worktrees_base = worktrees_base or Path.cwd() / "worktrees"
        
    def get_workspace_info(self, workspace_path: Path) -> WorkspaceInfo:
        """Get comprehensive workspace information.
        
        Args:
            workspace_path: Path to the workspace
            
        Returns:
            WorkspaceInfo object with workspace details
        """
        if not workspace_path.exists():
            return WorkspaceInfo(
                path=workspace_path,
                workspace_id=workspace_path.name,
                age_hours=0,
                status="missing"
            )
        
        # Calculate age
        mtime = os.path.getmtime(workspace_path)
        age_hours = (datetime.now().timestamp() - mtime) / 3600
        
        # Calculate size
        size_mb = self._calculate_directory_size(workspace_path) / (1024 * 1024)
        
        # Determine if persistent (check for .persistent marker or naming pattern)
        is_persistent = self._is_persistent_workspace(workspace_path)
        
        # Find associated run_id from workflow_runs table
        last_run_id = self._find_associated_run_id(workspace_path)
        
        # Determine status
        status = self._determine_workspace_status(workspace_path, age_hours, last_run_id)
        
        return WorkspaceInfo(
            path=workspace_path,
            workspace_id=workspace_path.name,
            age_hours=age_hours,
            size_mb=size_mb,
            is_persistent=is_persistent,
            last_run_id=last_run_id,
            status=status
        )
    
    def list_workspaces(self) -> List[WorkspaceInfo]:
        """List all workspaces with their information.
        
        Returns:
            List of WorkspaceInfo objects
        """
        if not self.worktrees_base.exists():
            return []
        
        workspaces = []
        for workspace_path in self.worktrees_base.iterdir():
            if workspace_path.is_dir():
                info = self.get_workspace_info(workspace_path)
                workspaces.append(info)
        
        return workspaces
    
    def find_cleanup_candidates(self, 
                              max_age_hours: float = 48,
                              exclude_persistent: bool = True,
                              min_size_mb: float = 0) -> List[WorkspaceInfo]:
        """Find workspaces that are candidates for cleanup.
        
        Args:
            max_age_hours: Maximum age in hours before considering for cleanup
            exclude_persistent: Whether to exclude persistent workspaces
            min_size_mb: Minimum size in MB to consider for cleanup
            
        Returns:
            List of WorkspaceInfo objects that are candidates for cleanup
        """
        workspaces = self.list_workspaces()
        candidates = []
        
        for workspace in workspaces:
            # Skip if persistent and exclusion is enabled
            if exclude_persistent and workspace.is_persistent:
                continue
            
            # Skip if too new
            if workspace.age_hours < max_age_hours:
                continue
                
            # Skip if too small
            if workspace.size_mb < min_size_mb:
                continue
            
            # Skip if workspace is still active (has running workflow)
            if workspace.status == "active":
                continue
            
            candidates.append(workspace)
        
        return candidates
    
    def cleanup_workspace(self, workspace_path: Path, force: bool = False) -> bool:
        """Clean up a workspace directory.
        
        Args:
            workspace_path: Path to the workspace to clean up
            force: Whether to force cleanup even if workspace appears active
            
        Returns:
            True if cleanup successful, False otherwise
        """
        if not workspace_path.exists():
            return True
        
        workspace_info = self.get_workspace_info(workspace_path)
        
        # Safety checks
        if not force:
            if workspace_info.is_persistent:
                logger.warning(f"Refusing to cleanup persistent workspace: {workspace_path}")
                return False
            
            if workspace_info.status == "active":
                logger.warning(f"Refusing to cleanup active workspace: {workspace_path}")
                return False
            
            if workspace_info.age_hours < 1:
                logger.warning(f"Refusing to cleanup very recent workspace: {workspace_path}")
                return False
        
        try:
            # Update workflow_runs table if associated run exists
            if workspace_info.last_run_id:
                self._update_workflow_run_cleanup_status(workspace_info.last_run_id, True)
            
            # Remove the workspace directory
            shutil.rmtree(workspace_path)
            logger.info(f"Cleaned up workspace: {workspace_path} ({workspace_info.size_mb:.1f} MB freed)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup workspace {workspace_path}: {e}")
            return False
    
    def cleanup_old_workspaces(self, 
                              max_age_hours: float = 48,
                              exclude_persistent: bool = True,
                              dry_run: bool = False) -> Dict[str, Any]:
        """Clean up old workspaces automatically.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
            exclude_persistent: Whether to exclude persistent workspaces
            dry_run: If True, only report what would be cleaned up
            
        Returns:
            Dict with cleanup results
        """
        candidates = self.find_cleanup_candidates(max_age_hours, exclude_persistent)
        
        results = {
            "total_candidates": len(candidates),
            "cleaned_up": [],
            "failed": [],
            "total_size_freed_mb": 0,
            "dry_run": dry_run
        }
        
        for workspace in candidates:
            if dry_run:
                results["cleaned_up"].append({
                    "path": str(workspace.path),
                    "size_mb": workspace.size_mb,
                    "age_hours": workspace.age_hours,
                    "run_id": workspace.last_run_id
                })
                results["total_size_freed_mb"] += workspace.size_mb
            else:
                if self.cleanup_workspace(workspace.path):
                    results["cleaned_up"].append({
                        "path": str(workspace.path),
                        "size_mb": workspace.size_mb,
                        "age_hours": workspace.age_hours,
                        "run_id": workspace.last_run_id
                    })
                    results["total_size_freed_mb"] += workspace.size_mb
                else:
                    results["failed"].append({
                        "path": str(workspace.path),
                        "reason": "cleanup_failed"
                    })
        
        return results
    
    def _calculate_directory_size(self, path: Path) -> int:
        """Calculate total size of directory in bytes."""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(filepath)
                    except (OSError, FileNotFoundError):
                        pass  # Skip files that can't be accessed
        except Exception:
            pass  # Return 0 if any error occurs
        
        return total_size
    
    def _is_persistent_workspace(self, workspace_path: Path) -> bool:
        """Determine if a workspace is persistent."""
        # Check for .persistent marker file
        if (workspace_path / ".persistent").exists():
            return True
        
        # Check for naming patterns that indicate persistence
        workspace_name = workspace_path.name.lower()
        persistent_patterns = ["main", "persistent", "long-term", "permanent"]
        
        for pattern in persistent_patterns:
            if pattern in workspace_name:
                return True
        
        return False
    
    def _find_associated_run_id(self, workspace_path: Path) -> Optional[str]:
        """Find the run_id associated with this workspace from workflow_runs table."""
        try:
            from automagik.db.repository.workflow_run import list_workflow_runs
            
            # Search for workflow runs with this workspace path
            runs, _ = list_workflow_runs(
                filters={},
                page=1,
                page_size=100,
                order_by='created_at',
                order_direction='DESC'
            )
            
            workspace_str = str(workspace_path)
            for run in runs:
                if run.workspace_path and run.workspace_path in workspace_str:
                    return run.run_id
                
                # Also check if workspace name matches run_id pattern
                if run.run_id in workspace_path.name:
                    return run.run_id
            
        except Exception as e:
            logger.debug(f"Could not find associated run_id for {workspace_path}: {e}")
        
        return None
    
    def _determine_workspace_status(self, workspace_path: Path, 
                                  age_hours: float, 
                                  last_run_id: Optional[str]) -> str:
        """Determine the current status of a workspace."""
        # Check if there's an active workflow using this workspace
        if last_run_id:
            try:
                from automagik.db.repository.workflow_run import get_workflow_run_by_run_id
                
                run = get_workflow_run_by_run_id(last_run_id)
                if run and run.status in ['pending', 'running']:
                    return "active"
                elif run and run.status in ['completed', 'failed', 'killed']:
                    return "completed"
                
            except Exception:
                pass
        
        # Fallback status determination based on age
        if age_hours < 1:
            return "active"
        elif age_hours < 24:
            return "recent"
        else:
            return "abandoned"
    
    def _update_workflow_run_cleanup_status(self, run_id: str, cleaned_up: bool):
        """Update the workspace_cleaned_up status in workflow_runs table."""
        try:
            from automagik.db.models import WorkflowRunUpdate
            from automagik.db.repository.workflow_run import update_workflow_run_by_run_id
            
            update = WorkflowRunUpdate(workspace_cleaned_up=cleaned_up)
            update_workflow_run_by_run_id(run_id, update)
            
        except Exception as e:
            logger.warning(f"Could not update cleanup status for run {run_id}: {e}")


# Singleton service instance
_workspace_service = None


def get_workspace_service() -> WorkspaceService:
    """Get the singleton workspace service instance."""
    global _workspace_service
    if _workspace_service is None:
        _workspace_service = WorkspaceService()
    return _workspace_service


def cleanup_old_workspaces(max_age_hours: float = 48, dry_run: bool = False) -> Dict[str, Any]:
    """Convenience function to cleanup old workspaces.
    
    Args:
        max_age_hours: Maximum age in hours before cleanup
        dry_run: If True, only report what would be cleaned up
        
    Returns:
        Dict with cleanup results
    """
    service = get_workspace_service()
    return service.cleanup_old_workspaces(max_age_hours=max_age_hours, dry_run=dry_run)


def get_workspace_summary() -> Dict[str, Any]:
    """Get a summary of current workspace status.
    
    Returns:
        Dict with workspace summary information
    """
    service = get_workspace_service()
    workspaces = service.list_workspaces()
    
    total_count = len(workspaces)
    total_size_mb = sum(w.size_mb for w in workspaces)
    persistent_count = sum(1 for w in workspaces if w.is_persistent)
    active_count = sum(1 for w in workspaces if w.status == "active")
    old_count = sum(1 for w in workspaces if w.age_hours > 48)
    
    return {
        "total_workspaces": total_count,
        "total_size_mb": total_size_mb,
        "persistent_workspaces": persistent_count,
        "active_workspaces": active_count,
        "old_workspaces": old_count,
        "cleanup_candidates": len(service.find_cleanup_candidates())
    }