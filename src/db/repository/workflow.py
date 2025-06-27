"""Repository for workflow database operations (simple single-table design like agents)."""

import json
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any

from ..models import Workflow, WorkflowCreate, WorkflowUpdate
from ..connection import execute_query

logger = logging.getLogger(__name__)


def create_workflow(workflow: WorkflowCreate) -> int:
    """Create a new workflow (upsert behavior like agents).
    
    Args:
        workflow: WorkflowCreate model with workflow data
        
    Returns:
        int: The ID of the created/updated workflow
        
    Raises:
        DatabaseError: If database operation fails
    """
    # Check if workflow with this name already exists
    existing = get_workflow_by_name(workflow.name)
    if existing:
        # Update existing workflow
        update_data = WorkflowUpdate(
            display_name=workflow.display_name,
            description=workflow.description,
            category=workflow.category,
            prompt_template=workflow.prompt_template,
            allowed_tools=workflow.allowed_tools,
            mcp_config=workflow.mcp_config,
            active=workflow.active,
            config=workflow.config
        )
        if update_workflow(existing.id, update_data):
            return existing.id
        else:
            raise RuntimeError(f"Failed to update existing workflow: {workflow.name}")
    
    # Insert new workflow
    query = """
        INSERT INTO workflows (
            name, display_name, description, category, prompt_template,
            allowed_tools, mcp_config, active, is_system_workflow, config,
            created_at, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    
    params = (
        workflow.name,
        workflow.display_name,
        workflow.description,
        workflow.category,
        workflow.prompt_template,
        json.dumps(workflow.allowed_tools),
        json.dumps(workflow.mcp_config),
        workflow.active,
        workflow.is_system_workflow,
        json.dumps(workflow.config),
        datetime.utcnow().isoformat(),
        datetime.utcnow().isoformat()
    )
    
    # Execute and get the ID
    result = execute_query(query, params, fetch=True, commit=True)
    
    # Get the newly created workflow ID
    created_workflow = get_workflow_by_name(workflow.name)
    return created_workflow.id if created_workflow else None


def get_workflow(workflow_id: int) -> Optional[Workflow]:
    """Get workflow by ID.
    
    Args:
        workflow_id: Workflow ID
        
    Returns:
        Workflow model or None if not found
    """
    query = """
        SELECT id, name, display_name, description, category, prompt_template,
               allowed_tools, mcp_config, active, is_system_workflow, config,
               created_at, updated_at
        FROM workflows 
        WHERE id = %s
    """
    
    result = execute_query(query, (workflow_id,), fetch=True)
    if not result:
        return None
    
    return Workflow.from_db_row(result[0])


def get_workflow_by_name(name: str) -> Optional[Workflow]:
    """Get workflow by name.
    
    Args:
        name: Workflow name
        
    Returns:
        Workflow model or None if not found
    """
    query = """
        SELECT id, name, display_name, description, category, prompt_template,
               allowed_tools, mcp_config, active, is_system_workflow, config,
               created_at, updated_at
        FROM workflows 
        WHERE name = %s
    """
    
    result = execute_query(query, (name,), fetch=True)
    if not result:
        return None
    
    return Workflow.from_db_row(result[0])


def list_workflows(
    active_only: bool = False,
    category: Optional[str] = None,
    is_system_workflow: Optional[bool] = None
) -> List[Workflow]:
    """List workflows with optional filtering (like agents).
    
    Args:
        active_only: Only return active workflows
        category: Filter by category
        is_system_workflow: Filter by system workflow status
        
    Returns:
        List of Workflow models
    """
    where_conditions = []
    params = []
    
    if active_only:
        where_conditions.append("active = %s")
        params.append(True)
    
    if category:
        where_conditions.append("category = %s")
        params.append(category)
    
    if is_system_workflow is not None:
        where_conditions.append("is_system_workflow = %s")
        params.append(is_system_workflow)
    
    where_clause = f"WHERE {' AND '.join(where_conditions)}" if where_conditions else ""
    
    query = f"""
        SELECT id, name, display_name, description, category, prompt_template,
               allowed_tools, mcp_config, active, is_system_workflow, config,
               created_at, updated_at
        FROM workflows 
        {where_clause}
        ORDER BY is_system_workflow DESC, category, name
    """
    
    result = execute_query(query, params, fetch=True)
    if not result:
        return []
    
    workflows = []
    for row in result:
        workflow = Workflow.from_db_row(row)
        if workflow:
            workflows.append(workflow)
    
    return workflows


def update_workflow(workflow_id: int, update_data: WorkflowUpdate) -> bool:
    """Update an existing workflow.
    
    Args:
        workflow_id: Workflow ID
        update_data: WorkflowUpdate model with updated fields
        
    Returns:
        bool: True if update successful, False if workflow not found
    """
    # Build dynamic update query
    update_fields = []
    params = []
    
    if update_data.display_name is not None:
        update_fields.append("display_name = %s")
        params.append(update_data.display_name)
    
    if update_data.description is not None:
        update_fields.append("description = %s")
        params.append(update_data.description)
    
    if update_data.category is not None:
        update_fields.append("category = %s")
        params.append(update_data.category)
    
    if update_data.prompt_template is not None:
        update_fields.append("prompt_template = %s")
        params.append(update_data.prompt_template)
    
    if update_data.allowed_tools is not None:
        update_fields.append("allowed_tools = %s")
        params.append(json.dumps(update_data.allowed_tools))
    
    if update_data.mcp_config is not None:
        update_fields.append("mcp_config = %s")
        params.append(json.dumps(update_data.mcp_config))
    
    if update_data.active is not None:
        update_fields.append("active = %s")
        params.append(update_data.active)
    
    if update_data.config is not None:
        update_fields.append("config = %s")
        params.append(json.dumps(update_data.config))
    
    if not update_fields:
        return True  # No fields to update
    
    # Add updated timestamp
    update_fields.append("updated_at = %s")
    params.append(datetime.utcnow().isoformat())
    
    # Add WHERE clause
    params.append(workflow_id)
    
    query = f"""
        UPDATE workflows 
        SET {', '.join(update_fields)}
        WHERE id = %s
    """
    
    try:
        execute_query(query, params, fetch=False, commit=True)
        return True
    except Exception as e:
        logger.error(f"Failed to update workflow {workflow_id}: {e}")
        return False


def delete_workflow(workflow_id: int) -> bool:
    """Delete a workflow by ID.
    
    Args:
        workflow_id: Workflow ID
        
    Returns:
        bool: True if deletion successful, False if not found
    """
    # Check if workflow exists and prevent deletion of system workflows
    workflow = get_workflow(workflow_id)
    if not workflow:
        return False
    
    if workflow.is_system_workflow:
        logger.warning(f"Attempted to delete system workflow: {workflow.name}")
        return False
    
    query = "DELETE FROM workflows WHERE id = %s"
    try:
        execute_query(query, (workflow_id,), commit=True)
        return True
    except Exception as e:
        logger.error(f"Failed to delete workflow {workflow_id}: {e}")
        return False


def register_workflow(workflow_data: Dict[str, Any]) -> Optional[int]:
    """Register a workflow discovered from filesystem (like agent registration).
    
    Args:
        workflow_data: Dictionary containing workflow information from filesystem
        
    Returns:
        int: Workflow ID if successful, None if failed
    """
    try:
        workflow = WorkflowCreate(
            name=workflow_data["name"],
            display_name=workflow_data.get("display_name"),
            description=workflow_data.get("description"),
            category=workflow_data.get("category", "custom"),
            prompt_template=workflow_data["prompt_template"],
            allowed_tools=workflow_data.get("allowed_tools", []),
            mcp_config=workflow_data.get("mcp_config", {}),
            active=workflow_data.get("active", True),
            is_system_workflow=workflow_data.get("is_system_workflow", False),
            config=workflow_data.get("config", {})
        )
        
        return create_workflow(workflow)
    except Exception as e:
        logger.error(f"Failed to register workflow {workflow_data.get('name', 'unknown')}: {e}")
        return None