"""Repository for workflow run database operations."""

import uuid
import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
import pytz

from ..models import WorkflowRun, WorkflowRunCreate, WorkflowRunUpdate
from ..connection import execute_query, safe_uuid

logger = logging.getLogger(__name__)


def create_workflow_run(workflow_run: WorkflowRunCreate) -> str:
    """Create a new workflow run record with race condition protection.
    
    Args:
        workflow_run: WorkflowRunCreate model with workflow data
        
    Returns:
        str: The UUID of the created workflow run
        
    Raises:
        ValueError: If run_id already exists
        DatabaseError: If database operation fails
    """
    # Check if run_id already exists
    existing = get_workflow_run_by_run_id(workflow_run.run_id)
    if existing:
        # For race conditions, if the workflow is still pending, we can return the existing ID
        # This handles the case where multiple requests try to create the same workflow
        if existing.status == "pending":
            logger.warning(f"Workflow run with run_id '{workflow_run.run_id}' already exists in pending state, returning existing ID")
            return str(existing.id)
        raise ValueError(f"Workflow run with run_id '{workflow_run.run_id}' already exists with status {existing.status}")
    
    # Generate UUID for primary key
    workflow_id = uuid.uuid4()
    
    # Convert models to database format with proper None handling
    session_id = None
    if workflow_run.session_id:
        try:
            session_id = safe_uuid(workflow_run.session_id)
        except Exception as e:
            logger.warning(f"Invalid session_id format: {workflow_run.session_id}, error: {e}")
            session_id = None
    
    user_id = None
    if workflow_run.user_id:
        try:
            user_id = safe_uuid(workflow_run.user_id)
        except Exception as e:
            logger.warning(f"Invalid user_id format: {workflow_run.user_id}, error: {e}")
            user_id = None
    
    # Serialize JSONB fields
    git_diff_stats_json = json.dumps(workflow_run.git_diff_stats) if workflow_run.git_diff_stats else '{}'
    metadata_json = json.dumps(workflow_run.metadata) if workflow_run.metadata else '{}'
    
    query = """
        INSERT INTO workflow_runs (
            id, run_id, workflow_name, agent_type, ai_model, task_input,
            session_id, session_name, git_repo, git_branch, initial_commit_hash,
            final_commit_hash, git_diff_added_lines, git_diff_removed_lines,
            git_diff_files_changed, git_diff_stats, status, result, error_message,
            created_at, completed_at, duration_seconds,
            workspace_id, workspace_persistent, workspace_cleaned_up, workspace_path,
            cost_estimate, input_tokens, output_tokens, total_tokens, user_id, metadata,
            updated_at
        ) VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
    """
    
    params = (
        str(workflow_id),
        workflow_run.run_id,
        workflow_run.workflow_name,
        workflow_run.agent_type,
        workflow_run.ai_model,
        workflow_run.task_input,
        str(session_id) if session_id else None,
        workflow_run.session_name,
        workflow_run.git_repo,
        workflow_run.git_branch,
        workflow_run.initial_commit_hash,
        workflow_run.final_commit_hash,
        workflow_run.git_diff_added_lines,
        workflow_run.git_diff_removed_lines,
        workflow_run.git_diff_files_changed,
        git_diff_stats_json,
        workflow_run.status,
        workflow_run.result,
        workflow_run.error_message,
        datetime.utcnow().isoformat(),  # created_at
        workflow_run.completed_at.isoformat() if workflow_run.completed_at else None,  # completed_at
        workflow_run.duration_seconds,  # duration_seconds
        workflow_run.workspace_id,
        workflow_run.workspace_persistent,
        workflow_run.workspace_cleaned_up,
        workflow_run.workspace_path,
        float(workflow_run.cost_estimate) if workflow_run.cost_estimate else None,
        workflow_run.input_tokens,
        workflow_run.output_tokens,
        workflow_run.total_tokens,
        str(user_id) if user_id else None,
        metadata_json,
        datetime.utcnow().isoformat()  # updated_at
    )
    
    try:
        execute_query(query, params)
        return str(workflow_id)
    except Exception as e:
        # Handle unique constraint violations for race conditions
        error_msg = str(e).lower()
        if "unique constraint" in error_msg or "already exists" in error_msg:
            # Try to get the existing workflow run
            existing = get_workflow_run_by_run_id(workflow_run.run_id)
            if existing and existing.status == "pending":
                logger.warning(f"Race condition detected for run_id '{workflow_run.run_id}', returning existing ID")
                return str(existing.id)
        raise


def get_workflow_run(workflow_id: str) -> Optional[WorkflowRun]:
    """Get workflow run by primary key ID.
    
    Args:
        workflow_id: UUID string of the workflow run
        
    Returns:
        WorkflowRun model or None if not found
    """
    workflow_uuid = safe_uuid(workflow_id)
    if not workflow_uuid:
        return None
    
    query = """
        SELECT id, run_id, workflow_name, agent_type, ai_model, task_input,
               session_id, session_name, git_repo, git_branch, initial_commit_hash,
               final_commit_hash, git_diff_added_lines, git_diff_removed_lines,
               git_diff_files_changed, git_diff_stats, status, result, error_message,
               created_at, completed_at, duration_seconds, workspace_id,
               workspace_persistent, workspace_cleaned_up, workspace_path,
               cost_estimate, input_tokens, output_tokens, total_tokens,
               user_id, metadata, updated_at
        FROM workflow_runs 
        WHERE id = ?
    """
    
    result = execute_query(query, (str(workflow_uuid),), fetch=True)
    if not result:
        return None
    
    # SQLite provider already returns dict rows, no need to zip with column names
    return WorkflowRun.from_db_row(result[0])


def get_workflow_run_by_run_id(run_id: str) -> Optional[WorkflowRun]:
    """Get workflow run by Claude SDK run_id.
    
    Args:
        run_id: Claude SDK run identifier
        
    Returns:
        WorkflowRun model or None if not found
    """
    query = """
        SELECT id, run_id, workflow_name, agent_type, ai_model, task_input,
               session_id, session_name, git_repo, git_branch, initial_commit_hash,
               final_commit_hash, git_diff_added_lines, git_diff_removed_lines,
               git_diff_files_changed, git_diff_stats, status, result, error_message,
               created_at, completed_at, duration_seconds, workspace_id,
               workspace_persistent, workspace_cleaned_up, workspace_path,
               cost_estimate, input_tokens, output_tokens, total_tokens,
               user_id, metadata, updated_at
        FROM workflow_runs 
        WHERE run_id = ?
    """
    
    result = execute_query(query, (run_id,), fetch=True)
    if not result:
        return None
    
    # SQLite provider already returns dict rows, no need to zip with column names
    return WorkflowRun.from_db_row(result[0])


def update_workflow_run(workflow_id: str, update_data: WorkflowRunUpdate) -> bool:
    """Update an existing workflow run.
    
    Args:
        workflow_id: UUID string of the workflow run
        update_data: WorkflowRunUpdate model with updated fields
        
    Returns:
        bool: True if update successful, False if workflow not found
    """
    workflow_uuid = safe_uuid(workflow_id)
    if not workflow_uuid:
        return False
    
    # Build dynamic update query
    update_fields = []
    params = []
    
    if update_data.status is not None:
        update_fields.append("status = ?")
        params.append(update_data.status)
        
        # If status is being set to completed/failed/killed, set completed_at
        # Only set automatically if not explicitly provided in update_data
        if update_data.status in {'completed', 'failed', 'killed'} and update_data.completed_at is None:
            update_fields.append("completed_at = ?")
            params.append(datetime.utcnow().isoformat())
    
    if update_data.result is not None:
        update_fields.append("result = ?")
        params.append(update_data.result)
    
    if update_data.error_message is not None:
        update_fields.append("error_message = ?")
        params.append(update_data.error_message)
    
    if update_data.session_id is not None:
        # Validate session_id before converting
        try:
            session_uuid = safe_uuid(update_data.session_id)
            if session_uuid:
                update_fields.append("session_id = ?")
                params.append(str(session_uuid))
            else:
                logger.warning(f"Invalid session_id in update: {update_data.session_id}")
        except Exception as e:
            logger.warning(f"Failed to process session_id in update: {e}")
    
    if update_data.final_commit_hash is not None:
        update_fields.append("final_commit_hash = ?")
        params.append(update_data.final_commit_hash)
    
    if update_data.git_diff_added_lines is not None:
        update_fields.append("git_diff_added_lines = ?")
        params.append(update_data.git_diff_added_lines)
    
    if update_data.git_diff_removed_lines is not None:
        update_fields.append("git_diff_removed_lines = ?")
        params.append(update_data.git_diff_removed_lines)
    
    if update_data.git_diff_files_changed is not None:
        update_fields.append("git_diff_files_changed = ?")
        params.append(update_data.git_diff_files_changed)
    
    if update_data.git_diff_stats is not None:
        update_fields.append("git_diff_stats = ?")
        params.append(json.dumps(update_data.git_diff_stats))
    
    if update_data.workspace_path is not None:
        update_fields.append("workspace_path = ?")
        params.append(update_data.workspace_path)
    
    if update_data.workspace_cleaned_up is not None:
        update_fields.append("workspace_cleaned_up = ?")
        params.append(update_data.workspace_cleaned_up)
    
    if update_data.cost_estimate is not None:
        update_fields.append("cost_estimate = ?")
        params.append(float(update_data.cost_estimate))
    
    if update_data.input_tokens is not None:
        update_fields.append("input_tokens = ?")
        params.append(update_data.input_tokens)
    
    if update_data.output_tokens is not None:
        update_fields.append("output_tokens = ?")
        params.append(update_data.output_tokens)
    
    if update_data.total_tokens is not None:
        update_fields.append("total_tokens = ?")
        params.append(update_data.total_tokens)
    
    if update_data.duration_seconds is not None:
        update_fields.append("duration_seconds = ?")
        params.append(update_data.duration_seconds)
    
    if update_data.completed_at is not None:
        update_fields.append("completed_at = ?")
        # Ensure completed_at is timezone-naive UTC for database consistency
        completed_at = update_data.completed_at
        if isinstance(completed_at, datetime):
            if completed_at.tzinfo is not None:
                completed_at = completed_at.astimezone(pytz.UTC).replace(tzinfo=None)
            params.append(completed_at.isoformat())
        else:
            params.append(completed_at)
    
    if update_data.metadata is not None:
        update_fields.append("metadata = ?")
        params.append(json.dumps(update_data.metadata))
    
    if not update_fields:
        return True  # No fields to update
    
    # Add updated timestamp
    update_fields.append("updated_at = ?")
    params.append(datetime.utcnow().isoformat())
    
    # Add WHERE clause
    params.append(str(workflow_uuid))
    
    query = f"""
        UPDATE workflow_runs 
        SET {', '.join(update_fields)}
        WHERE id = ?
    """
    
    try:
        result = execute_query(query, params, fetch=False, commit=True)
        return True
    except Exception as e:
        logger.error(f"Failed to update workflow_run {workflow_id}: {e}")
        return False


def list_workflow_runs(
    filters: Optional[Dict[str, Any]] = None,
    page: int = 1,
    page_size: int = 20,
    order_by: str = "created_at",
    order_direction: str = "DESC"
) -> Tuple[List[WorkflowRun], int]:
    """List workflow runs with filtering and pagination.
    
    Args:
        filters: Optional dict with filter criteria
        page: Page number (1-indexed)
        page_size: Number of records per page
        order_by: Field to order by
        order_direction: ASC or DESC
        
    Returns:
        Tuple of (workflow_runs_list, total_count)
    """
    # Build WHERE clause from filters
    where_conditions = []
    params = []
    
    if filters:
        if 'status' in filters:
            where_conditions.append("status = ?")
            params.append(filters['status'])
        
        if 'workflow_name' in filters:
            where_conditions.append("workflow_name = ?")
            params.append(filters['workflow_name'])
        
        if 'user_id' in filters:
            user_uuid = safe_uuid(filters['user_id'])
            if user_uuid:
                where_conditions.append("user_id = ?")
                params.append(str(user_uuid))
        
        if 'session_id' in filters:
            session_uuid = safe_uuid(filters['session_id'])
            if session_uuid:
                where_conditions.append("session_id = ?")
                params.append(str(session_uuid))
        
        if 'git_branch' in filters:
            where_conditions.append("git_branch = ?")
            params.append(filters['git_branch'])
        
        if 'created_after' in filters:
            where_conditions.append("created_at >= ?")
            # Handle timezone conversion for created_after
            created_after = filters['created_after']
            if isinstance(created_after, datetime):
                # If it's a datetime object with timezone info, convert to naive UTC
                if created_after.tzinfo is not None:
                    created_after = created_after.astimezone(pytz.UTC).replace(tzinfo=None)
                params.append(created_after.isoformat())
            else:
                # If it's already a string, use as-is
                params.append(created_after)
        
        if 'created_before' in filters:
            where_conditions.append("created_at <= ?")
            # Handle timezone conversion for created_before
            created_before = filters['created_before']
            if isinstance(created_before, datetime):
                # If it's a datetime object with timezone info, convert to naive UTC
                if created_before.tzinfo is not None:
                    created_before = created_before.astimezone(pytz.UTC).replace(tzinfo=None)
                params.append(created_before.isoformat())
            else:
                # If it's already a string, use as-is
                params.append(created_before)
    
    where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
    
    # Validate order_by field
    valid_order_fields = {
        'created_at', 'completed_at', 'duration_seconds', 'workflow_name',
        'status', 'cost_estimate', 'total_tokens', 'git_branch'
    }
    if order_by not in valid_order_fields:
        order_by = 'created_at'
    
    order_direction = order_direction.upper()
    if order_direction not in {'ASC', 'DESC'}:
        order_direction = 'DESC'
    
    # Get total count
    count_query = f"SELECT COUNT(*) FROM workflow_runs {where_clause}"
    count_result = execute_query(count_query, params, fetch=True)
    if count_result and len(count_result) > 0:
        # Handle dict result (SQLite) or tuple result
        first_row = count_result[0]
        if isinstance(first_row, dict):
            total_count = first_row.get('COUNT(*)', 0)
        else:
            total_count = first_row[0]
    else:
        total_count = 0
    
    # Get paginated results
    offset = (page - 1) * page_size
    query = f"""
        SELECT id, run_id, workflow_name, agent_type, ai_model, task_input,
               session_id, session_name, git_repo, git_branch, initial_commit_hash,
               final_commit_hash, git_diff_added_lines, git_diff_removed_lines,
               git_diff_files_changed, git_diff_stats, status, result, error_message,
               created_at, completed_at, duration_seconds, workspace_id,
               workspace_persistent, workspace_cleaned_up, workspace_path,
               cost_estimate, input_tokens, output_tokens, total_tokens,
               user_id, metadata, updated_at
        FROM workflow_runs 
        {where_clause}
        ORDER BY {order_by} {order_direction}
        LIMIT ? OFFSET ?
    """
    
    params.extend([page_size, offset])
    result = execute_query(query, params, fetch=True)
    
    if not result:
        return [], total_count
    
    workflow_runs = []
    for row in result:
        workflow_run = WorkflowRun.from_db_row(row)
        workflow_runs.append(workflow_run)
    
    return workflow_runs, total_count


def delete_workflow_run(workflow_id: str) -> bool:
    """Delete a workflow run by ID.
    
    Args:
        workflow_id: UUID string of the workflow run
        
    Returns:
        bool: True if deletion successful, False if not found
    """
    workflow_uuid = safe_uuid(workflow_id)
    if not workflow_uuid:
        return False
    
    query = "DELETE FROM workflow_runs WHERE id = ?"
    execute_query(query, (str(workflow_uuid),))
    return True


def get_workflow_runs_by_session(session_id: str) -> List[WorkflowRun]:
    """Get all workflow runs for a specific session.
    
    Args:
        session_id: Session UUID string
        
    Returns:
        List of WorkflowRun models
    """
    session_uuid = safe_uuid(session_id)
    if not session_uuid:
        return []
    
    query = """
        SELECT id, run_id, workflow_name, agent_type, ai_model, task_input,
               session_id, session_name, git_repo, git_branch, initial_commit_hash,
               final_commit_hash, git_diff_added_lines, git_diff_removed_lines,
               git_diff_files_changed, git_diff_stats, status, result, error_message,
               created_at, completed_at, duration_seconds, workspace_id,
               workspace_persistent, workspace_cleaned_up, workspace_path,
               cost_estimate, input_tokens, output_tokens, total_tokens,
               user_id, metadata, updated_at
        FROM workflow_runs 
        WHERE session_id = ?
        ORDER BY created_at DESC
    """
    
    result = execute_query(query, (str(session_uuid),), fetch=True)
    if not result:
        return []
    
    workflow_runs = []
    for row in result:
        workflow_run = WorkflowRun.from_db_row(row)
        workflow_runs.append(workflow_run)
    
    return workflow_runs


def get_recent_workflow_runs(limit: int = 10) -> List[WorkflowRun]:
    """Get most recent workflow runs.
    
    Args:
        limit: Maximum number of results
        
    Returns:
        List of WorkflowRun models
    """
    query = """
        SELECT id, run_id, workflow_name, agent_type, ai_model, task_input,
               session_id, session_name, git_repo, git_branch, initial_commit_hash,
               final_commit_hash, git_diff_added_lines, git_diff_removed_lines,
               git_diff_files_changed, git_diff_stats, status, result, error_message,
               created_at, completed_at, duration_seconds, workspace_id,
               workspace_persistent, workspace_cleaned_up, workspace_path,
               cost_estimate, input_tokens, output_tokens, total_tokens,
               user_id, metadata, updated_at
        FROM workflow_runs 
        ORDER BY created_at DESC
        LIMIT ?
    """
    
    result = execute_query(query, (limit,), fetch=True)
    if not result:
        return []
    
    workflow_runs = []
    for row in result:
        workflow_run = WorkflowRun.from_db_row(row)
        workflow_runs.append(workflow_run)
    
    return workflow_runs


def update_workflow_run_by_run_id(run_id: str, update_data: WorkflowRunUpdate) -> bool:
    """Update workflow run by Claude SDK run_id.
    
    Args:
        run_id: Claude SDK run identifier
        update_data: WorkflowRunUpdate model with updated fields
        
    Returns:
        bool: True if update successful, False if workflow not found
    """
    # Get the workflow by run_id first
    workflow = get_workflow_run_by_run_id(run_id)
    if not workflow:
        return False
    
    # Use the primary key update method
    return update_workflow_run(str(workflow.id), update_data)