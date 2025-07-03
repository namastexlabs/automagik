"""Utilities for handling race conditions in workflow creation.

This module provides helper functions to prevent and handle race conditions
that can occur during concurrent workflow creation and execution.
"""

import asyncio
import uuid
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)

# Global locks for critical sections
_workflow_creation_lock = asyncio.Lock()
_worktree_path_lock = asyncio.Lock()


async def generate_unique_run_id(max_retries: int = 5) -> str:
    """Generate a unique run ID with collision detection.
    
    Args:
        max_retries: Maximum number of retries if collision detected
        
    Returns:
        A unique run ID string
        
    Raises:
        RuntimeError: If unable to generate unique ID after max_retries
    """
    from automagik.db.repository.workflow_run import get_workflow_run_by_run_id
    
    for attempt in range(max_retries):
        run_id = str(uuid.uuid4())
        
        # Check if this run_id already exists
        existing = get_workflow_run_by_run_id(run_id)
        if not existing:
            return run_id
        
        logger.warning(f"Run ID collision detected on attempt {attempt + 1}: {run_id}")
        
        # Small delay before retry to reduce collision probability
        await asyncio.sleep(0.01 * (attempt + 1))
    
    raise RuntimeError(f"Failed to generate unique run ID after {max_retries} attempts")


async def create_workflow_with_retry(
    workflow_data: Dict[str, Any],
    max_retries: int = 3
) -> str:
    """Create a workflow run with retry logic for race conditions.
    
    Args:
        workflow_data: Dictionary containing workflow creation data
        max_retries: Maximum number of retries
        
    Returns:
        The workflow run ID
        
    Raises:
        Exception: If creation fails after all retries
    """
    from automagik.db.models import WorkflowRunCreate
    from automagik.db.repository.workflow_run import create_workflow_run, get_workflow_run_by_run_id
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Create the workflow run
            workflow_run = WorkflowRunCreate(**workflow_data)
            workflow_id = create_workflow_run(workflow_run)
            return workflow_id
            
        except ValueError as e:
            error_msg = str(e).lower()
            if "already exists" in error_msg:
                # Check if it's our workflow (race condition)
                existing = get_workflow_run_by_run_id(workflow_data['run_id'])
                if existing and existing.status in ["pending", "running"]:
                    logger.info(f"Workflow {workflow_data['run_id']} already exists (race condition)")
                    return str(existing.id)
                    
                # Generate new run_id and retry
                logger.warning(f"Run ID collision on attempt {attempt + 1}, generating new ID")
                workflow_data['run_id'] = await generate_unique_run_id()
                last_error = e
            else:
                raise
                
        except Exception as e:
            last_error = e
            logger.error(f"Failed to create workflow on attempt {attempt + 1}: {e}")
            
            if attempt < max_retries - 1:
                await asyncio.sleep(0.1 * (attempt + 1))
    
    raise last_error or Exception("Failed to create workflow after all retries")


async def ensure_unique_worktree_path(
    base_path: Path,
    branch_name: str,
    run_id: str,
    persistent: bool = False
) -> Path:
    """Ensure a unique worktree path to prevent concurrent creation conflicts.
    
    Args:
        base_path: Base directory for worktrees
        branch_name: Git branch name
        run_id: Unique run identifier
        persistent: Whether this is a persistent workspace
        
    Returns:
        A unique worktree path
    """
    async with _worktree_path_lock:
        safe_branch_name = branch_name.replace("/", "-")
        
        if persistent:
            # For persistent workspaces, use deterministic naming
            worktree_path = base_path / safe_branch_name
        else:
            # For temporary workspaces, include run_id for uniqueness
            worktree_path = base_path / f"{safe_branch_name}-{run_id[:8]}"
        
        # If path exists and it's not persistent, add timestamp
        if worktree_path.exists() and not persistent:
            import time
            timestamp = int(time.time() * 1000)
            worktree_path = base_path / f"{safe_branch_name}-{run_id[:8]}-{timestamp}"
            logger.warning(f"Worktree path collision detected, using: {worktree_path}")
        
        return worktree_path


def validate_session_id(session_id: Optional[str]) -> Optional[str]:
    """Validate and normalize a session ID.
    
    Args:
        session_id: The session ID to validate
        
    Returns:
        Valid session ID string or None if invalid
    """
    if not session_id:
        return None
    
    try:
        # Try to parse as UUID to validate format
        uuid.UUID(session_id)
        return session_id
    except (ValueError, TypeError):
        logger.warning(f"Invalid session_id format: {session_id}")
        return None


async def cleanup_orphaned_worktrees(
    worktrees_path: Path,
    max_age_hours: int = 24
) -> int:
    """Clean up orphaned worktrees older than specified age.
    
    Args:
        worktrees_path: Path to worktrees directory
        max_age_hours: Maximum age in hours before cleanup
        
    Returns:
        Number of worktrees cleaned up
    """
    import time
    from datetime import datetime, timedelta
    
    if not worktrees_path.exists():
        return 0
    
    cleaned = 0
    cutoff_time = time.time() - (max_age_hours * 3600)
    
    for worktree in worktrees_path.iterdir():
        if not worktree.is_dir():
            continue
        
        # Skip persistent worktrees (don't have run_id suffix)
        if not any(part in worktree.name for part in ["-run_", "_run_"]):
            continue
        
        # Check modification time
        try:
            mtime = worktree.stat().st_mtime
            if mtime < cutoff_time:
                logger.info(f"Cleaning up orphaned worktree: {worktree}")
                
                # Use git worktree remove
                process = await asyncio.create_subprocess_exec(
                    "git", "worktree", "remove", str(worktree), "--force",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                cleaned += 1
                
        except Exception as e:
            logger.error(f"Failed to clean up worktree {worktree}: {e}")
    
    return cleaned