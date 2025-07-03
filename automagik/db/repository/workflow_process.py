"""Repository for workflow process operations."""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from automagik.db.models import WorkflowProcess, WorkflowProcessCreate, WorkflowProcessUpdate
from automagik.db.connection import execute_query, get_db_cursor
from ...utils.timezone import get_timezone_aware_now

logger = logging.getLogger(__name__)


def create_workflow_process(process: WorkflowProcessCreate) -> bool:
    """Create a new workflow process record.
    
    Args:
        process: WorkflowProcess data to create
        
    Returns:
        True if created successfully, False otherwise
    """
    try:
        # Use current timestamp for created_at, started_at, and last_heartbeat
        now = get_timezone_aware_now()
        
        # Convert process_info to JSON string if it's a dict
        process_info_json = process.process_info
        if isinstance(process_info_json, dict):
            import json
            process_info_json = json.dumps(process_info_json)
        
        # Insert workflow process record
        query = """
        INSERT INTO workflow_processes (
            run_id, pid, status, workflow_name, session_id, user_id,
            started_at, workspace_path, last_heartbeat, process_info,
            created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (run_id) DO UPDATE SET
            pid = EXCLUDED.pid,
            status = EXCLUDED.status,
            workflow_name = EXCLUDED.workflow_name,
            session_id = EXCLUDED.session_id,
            user_id = EXCLUDED.user_id,
            workspace_path = EXCLUDED.workspace_path,
            last_heartbeat = EXCLUDED.last_heartbeat,
            process_info = EXCLUDED.process_info,
            updated_at = EXCLUDED.updated_at
        """
        
        execute_query(
            query,
            (
                process.run_id,
                process.pid,
                process.status,
                process.workflow_name,
                process.session_id,
                process.user_id,
                now,  # started_at
                process.workspace_path,
                now,  # last_heartbeat
                process_info_json,
                now,  # created_at
                now   # updated_at
            )
        )
        
        logger.info(f"Created workflow process record for run_id: {process.run_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create workflow process: {e}")
        return False


def get_workflow_process(run_id: str) -> Optional[WorkflowProcess]:
    """Get a workflow process by run_id.
    
    Args:
        run_id: Run ID to look up
        
    Returns:
        WorkflowProcess instance or None if not found
    """
    try:
        query = "SELECT * FROM workflow_processes WHERE run_id = %s"
        results = execute_query(query, (run_id,), fetch=True)
        result = results[0] if results else None
        
        if result:
            return WorkflowProcess.from_db_row(dict(result))
        return None
        
    except Exception as e:
        logger.error(f"Failed to get workflow process {run_id}: {e}")
        return None


def list_workflow_processes(
    status: Optional[str] = None,
    workflow_name: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[WorkflowProcess]:
    """List workflow processes with optional filtering.
    
    Args:
        status: Filter by status
        workflow_name: Filter by workflow name
        user_id: Filter by user ID
        limit: Maximum number of records to return
        offset: Number of records to skip
        
    Returns:
        List of WorkflowProcess instances
    """
    try:
        # Build query with conditional filters
        query = "SELECT * FROM workflow_processes WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = %s"
            params.append(status)
        
        if workflow_name:
            query += " AND workflow_name = %s"
            params.append(workflow_name)
        
        if user_id:
            query += " AND user_id = %s"
            params.append(user_id)
        
        # Add ordering and pagination
        query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        results = execute_query(query, params, fetch=True)
        
        return [WorkflowProcess.from_db_row(dict(row)) for row in results]
        
    except Exception as e:
        logger.error(f"Failed to list workflow processes: {e}")
        return []


def update_workflow_process(run_id: str, update: WorkflowProcessUpdate) -> bool:
    """Update a workflow process.
    
    Args:
        run_id: Run ID of the process to update
        update: Update data
        
    Returns:
        True if updated successfully, False otherwise
    """
    try:
        # Build dynamic update query
        set_clauses = []
        params = []
        
        if update.pid is not None:
            set_clauses.append("pid = %s")
            params.append(update.pid)
        
        if update.status is not None:
            set_clauses.append("status = %s")
            params.append(update.status)
        
        if update.last_heartbeat is not None:
            set_clauses.append("last_heartbeat = %s")
            params.append(update.last_heartbeat)
        
        if update.process_info is not None:
            # Convert dict to JSON string
            process_info_json = update.process_info
            if isinstance(process_info_json, dict):
                import json
                process_info_json = json.dumps(process_info_json)
            set_clauses.append("process_info = %s")
            params.append(process_info_json)
        
        if not set_clauses:
            logger.warning(f"No fields to update for workflow process {run_id}")
            return False
        
        # Always update the updated_at timestamp
        set_clauses.append("updated_at = %s")
        params.append(get_timezone_aware_now())
        
        # Add run_id for WHERE clause
        params.append(run_id)
        
        query = f"UPDATE workflow_processes SET {', '.join(set_clauses)} WHERE run_id = %s"
        
        execute_query(query, params)
        
        logger.info(f"Updated workflow process: {run_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to update workflow process {run_id}: {e}")
        return False


def delete_workflow_process(run_id: str) -> bool:
    """Delete a workflow process.
    
    Args:
        run_id: Run ID of the process to delete
        
    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        query = "DELETE FROM workflow_processes WHERE run_id = %s"
        execute_query(query, (run_id,))
        
        logger.info(f"Deleted workflow process: {run_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete workflow process {run_id}: {e}")
        return False


def update_heartbeat(run_id: str) -> bool:
    """Update the heartbeat timestamp for a workflow process.
    
    Args:
        run_id: Run ID of the process
        
    Returns:
        True if updated successfully, False otherwise
    """
    try:
        now = get_timezone_aware_now()
        update = WorkflowProcessUpdate(last_heartbeat=now)
        return update_workflow_process(run_id, update)
        
    except Exception as e:
        logger.error(f"Failed to update heartbeat for {run_id}: {e}")
        return False


def mark_process_terminated(run_id: str, status: str = "terminated") -> bool:
    """Mark a workflow process as terminated.
    
    Args:
        run_id: Run ID of the process
        status: Termination status (terminated, completed, failed, killed)
        
    Returns:
        True if updated successfully, False otherwise
    """
    try:
        valid_statuses = ["terminated", "completed", "failed", "killed"]
        if status not in valid_statuses:
            status = "terminated"
        
        update = WorkflowProcessUpdate(status=status)
        return update_workflow_process(run_id, update)
        
    except Exception as e:
        logger.error(f"Failed to mark process {run_id} as {status}: {e}")
        return False


def get_running_processes() -> List[WorkflowProcess]:
    """Get all currently running workflow processes.
    
    Returns:
        List of running WorkflowProcess instances
    """
    return list_workflow_processes(status="running")


def get_stale_processes(max_age_minutes: int = 5) -> List[WorkflowProcess]:
    """Get workflow processes that haven't had a heartbeat in the specified time.
    
    Args:
        max_age_minutes: Maximum minutes since last heartbeat to consider stale
        
    Returns:
        List of stale WorkflowProcess instances
    """
    try:
        # Calculate cutoff time
        from datetime import timedelta
        cutoff_time = get_timezone_aware_now() - timedelta(minutes=max_age_minutes)
        
        query = """
        SELECT * FROM workflow_processes 
        WHERE status = 'running' 
        AND (last_heartbeat IS NULL OR last_heartbeat < %s)
        ORDER BY last_heartbeat ASC NULLS FIRST
        """
        
        results = execute_query(query, (cutoff_time,), fetch=True)
        return [WorkflowProcess.from_db_row(dict(row)) for row in results]
        
    except Exception as e:
        logger.error(f"Failed to get stale processes: {e}")
        return []


def cleanup_old_processes(max_age_days: int = 7) -> int:
    """Clean up old completed/terminated workflow processes.
    
    Args:
        max_age_days: Maximum age in days for completed processes to keep
        
    Returns:
        Number of records cleaned up
    """
    try:
        from datetime import timedelta
        cutoff_time = get_timezone_aware_now() - timedelta(days=max_age_days)
        
        query = """
        DELETE FROM workflow_processes 
        WHERE status IN ('completed', 'failed', 'killed', 'terminated')
        AND updated_at < %s
        """
        
        with get_db_cursor() as cursor:
            cursor.execute(query, (cutoff_time,))
            deleted_count = cursor.rowcount
        
        logger.info(f"Cleaned up {deleted_count} old workflow processes")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Failed to cleanup old processes: {e}")
        return 0