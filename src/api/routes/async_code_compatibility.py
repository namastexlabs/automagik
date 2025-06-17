"""Async-code compatibility API routes.

This module provides compatibility endpoints for async-code UI integration,
mapping to the existing Claude-Code workflow system.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Path, Body, Query
from pydantic import BaseModel, Field

from src.agents.models.agent_factory import AgentFactory
from src.agents.claude_code.stream_parser import StreamParser
from src.db.repository import session as session_repo
from src.db.repository import user as user_repo
from src.db.models.workflow_process import WorkflowProcess
from src.db.core import get_db_session
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Create router for async-code compatibility endpoints
async_code_router = APIRouter(prefix="/api/v1", tags=["Async-Code-Compatibility"])


# Compatibility models for async-code format
class AsyncCodeTaskRequest(BaseModel):
    """Task creation request matching async-code format."""
    
    agent: str = Field(
        default="builder",
        description="Agent type (maps to workflow_name)"
    )
    prompt: str = Field(
        ...,
        description="Task prompt/message"
    )
    repo_url: Optional[str] = Field(
        None,
        description="Repository URL"
    )
    git_branch: Optional[str] = Field(
        None,
        description="Git branch"
    )
    model: Optional[str] = Field(
        None,
        description="Model to use"
    )
    project_id: Optional[str] = Field(
        None,
        description="Project identifier"
    )


class AsyncCodeTaskResponse(BaseModel):
    """Task creation response matching async-code format."""
    
    task_id: str = Field(
        ...,
        description="Unique task identifier"
    )
    status: str = Field(
        default="pending",
        description="Task status"
    )
    created_at: str = Field(
        ...,
        description="Task creation timestamp"
    )


class AsyncCodeTaskStatus(BaseModel):
    """Task status response matching async-code format."""
    
    task_id: str
    status: str
    progress: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    logs_url: Optional[str] = None


class AsyncCodeProject(BaseModel):
    """Project info matching async-code format."""
    
    id: str
    name: str
    description: Optional[str] = None


# Response transformers
class AsyncCodeResponseTransformer:
    """Transforms Claude-Code responses to async-code format."""
    
    @staticmethod
    def workflow_to_task_status(workflow_process: WorkflowProcess, session_data: Optional[Dict] = None) -> AsyncCodeTaskStatus:
        """Convert WorkflowProcess to async-code task status format."""
        
        # Map Claude-Code status to async-code status
        status_mapping = {
            "started": "running",
            "running": "running", 
            "completed": "completed",
            "failed": "failed",
            "error": "failed",
            "stopped": "cancelled",
            "killed": "cancelled"
        }
        
        mapped_status = status_mapping.get(workflow_process.status, workflow_process.status)
        
        # Extract progress from session data if available
        progress = None
        if session_data and "progress" in session_data:
            progress = session_data["progress"].get("completion_percentage", 0.0) / 100.0
        
        # Extract result from session data
        result = None
        if session_data and mapped_status == "completed":
            result = {
                "summary": session_data.get("summary", "Task completed"),
                "metrics": session_data.get("metrics", {}),
                "files_modified": session_data.get("files_modified", [])
            }
        
        # Extract error from session data
        error = None
        if session_data and mapped_status == "failed":
            error = session_data.get("error", "Task failed")
        
        # Generate logs URL pointing to JSONL file
        logs_url = f"/api/v1/tasks/{workflow_process.run_id}/logs"
        
        return AsyncCodeTaskStatus(
            task_id=workflow_process.run_id,
            status=mapped_status,
            progress=progress,
            result=result,
            error=error,
            created_at=workflow_process.created_at.isoformat() if workflow_process.created_at else datetime.utcnow().isoformat(),
            updated_at=workflow_process.updated_at.isoformat() if workflow_process.updated_at else None,
            logs_url=logs_url
        )
    
    @staticmethod
    def create_task_response(run_id: str) -> AsyncCodeTaskResponse:
        """Create async-code task creation response."""
        return AsyncCodeTaskResponse(
            task_id=run_id,
            status="pending",
            created_at=datetime.utcnow().isoformat()
        )


# Endpoints
@async_code_router.get("/tasks", response_model=List[AsyncCodeTaskStatus])
async def list_tasks(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, description="Number of tasks to return")
) -> List[AsyncCodeTaskStatus]:
    """List tasks (maps to workflow runs)."""
    
    try:
        with get_db_session() as db:
            query = db.query(WorkflowProcess)
            
            # Apply status filter if provided
            if status:
                # Map async-code status back to Claude-Code status
                status_mapping = {
                    "running": ["started", "running"],
                    "completed": ["completed"],
                    "failed": ["failed", "error"],
                    "cancelled": ["stopped", "killed"],
                    "pending": ["pending"]
                }
                
                claude_statuses = status_mapping.get(status, [status])
                query = query.filter(WorkflowProcess.status.in_(claude_statuses))
            
            workflow_processes = query.order_by(WorkflowProcess.created_at.desc()).limit(limit).all()
            
            tasks = []
            for wp in workflow_processes:
                # Get session data for additional info
                session_data = None
                if wp.session_id:
                    session_data = session_repo.get_session_metadata(wp.session_id)
                
                task_status = AsyncCodeResponseTransformer.workflow_to_task_status(wp, session_data)
                tasks.append(task_status)
            
            return tasks
            
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@async_code_router.get("/tasks/{task_id}/status", response_model=AsyncCodeTaskStatus)
async def get_task_status(task_id: str = Path(..., description="Task ID")) -> AsyncCodeTaskStatus:
    """Get task status (maps to workflow run status)."""
    
    try:
        with get_db_session() as db:
            workflow_process = db.query(WorkflowProcess).filter(
                WorkflowProcess.run_id == task_id
            ).first()
            
            if not workflow_process:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
            
            # Get session data for additional info
            session_data = None
            if workflow_process.session_id:
                session_data = session_repo.get_session_metadata(workflow_process.session_id)
            
            return AsyncCodeResponseTransformer.workflow_to_task_status(workflow_process, session_data)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


@async_code_router.post("/tasks", response_model=AsyncCodeTaskResponse)
async def start_task(request: AsyncCodeTaskRequest) -> AsyncCodeTaskResponse:
    """Start a new task (maps to workflow run creation)."""
    
    try:
        # Generate unique run ID
        run_id = str(uuid.uuid4())
        
        # Map agent to workflow_name
        workflow_name_mapping = {
            "builder": "builder",
            "genie": "genie", 
            "guardian": "guardian",
            "brain": "brain"
        }
        
        workflow_name = workflow_name_mapping.get(request.agent, request.agent)
        
        # Create workflow request in Claude-Code format
        claude_request = {
            "message": request.prompt,
            "max_turns": 50,
            "session_id": None,
            "continue_session": False,
            "workspace_path": None,
            "repo_url": request.repo_url,
            "git_branch": request.git_branch,
            "model": request.model,
            "project_id": request.project_id
        }
        
        # Use AgentFactory to create and run the workflow
        agent_factory = AgentFactory()
        
        # Start the workflow asynchronously
        await agent_factory.run_workflow_async(
            workflow_name=workflow_name,
            request_data=claude_request,
            run_id=run_id
        )
        
        return AsyncCodeResponseTransformer.create_task_response(run_id)
        
    except Exception as e:
        logger.error(f"Error starting task: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start task: {str(e)}")


@async_code_router.get("/tasks/{task_id}/logs")
async def get_task_logs(task_id: str = Path(..., description="Task ID")):
    """Get task logs (returns JSONL stream file)."""
    
    try:
        # Check if task exists
        with get_db_session() as db:
            workflow_process = db.query(WorkflowProcess).filter(
                WorkflowProcess.run_id == task_id
            ).first()
            
            if not workflow_process:
                raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        # Return the JSONL file path for the UI to read
        jsonl_path = f"./logs/run_{task_id}_stream.jsonl"
        
        # For now, return the path. The UI can read this file directly.
        # In a production system, you might stream the file content.
        return {
            "task_id": task_id,
            "logs_path": jsonl_path,
            "format": "jsonl",
            "description": "Each line is a JSON object with timestamp and event data"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task logs {task_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get task logs: {str(e)}")


@async_code_router.get("/projects", response_model=List[AsyncCodeProject])
async def list_projects() -> List[AsyncCodeProject]:
    """List available projects (basic implementation)."""
    
    # For now, return a simple list of default projects
    # This can be enhanced to read from database or configuration
    default_projects = [
        AsyncCodeProject(
            id="default",
            name="Default Project",
            description="Default project workspace"
        ),
        AsyncCodeProject(
            id="am-agents-labs",
            name="AM Agents Labs",
            description="Main agents laboratory project"
        )
    ]
    
    return default_projects


# Health check endpoint
@async_code_router.get("/health")
async def health_check():
    """Health check for async-code compatibility layer."""
    return {
        "status": "healthy",
        "service": "async-code-compatibility",
        "timestamp": datetime.utcnow().isoformat()
    }