"""Claude-Code specific API routes.

This module provides specialized endpoints for the Claude-Code agent framework,
supporting workflow-based execution and async container management.
"""
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.agents.models.agent_factory import AgentFactory
from src.agents.claude_code.log_manager import get_log_manager
from src.db.repository import session as session_repo
from src.db.repository import user as user_repo

logger = logging.getLogger(__name__)

# Create router for claude-code endpoints
claude_code_router = APIRouter(prefix="/agent/claude-code", tags=["Claude-Code"])


class ClaudeCodeRunRequest(BaseModel):
    """Request for Claude-Code agent execution."""
    workflow_name: str = Field(..., description="Workflow to execute (e.g., 'architect', 'implement', 'test')")
    message: str = Field(..., description="Task description for Claude to execute")
    session_id: Optional[str] = Field(None, description="Optional session ID for continuation")
    max_turns: int = Field(default=30, ge=1, le=100, description="Maximum number of turns")
    git_branch: str = Field(default="NMSTX-187-langgraph-orchestrator-migration", description="Git branch to work on")
    timeout: Optional[int] = Field(default=7200, ge=60, le=14400, description="Execution timeout in seconds")
    user_id: Optional[str] = Field(None, description="User ID for the request")
    session_name: Optional[str] = Field(None, description="Optional session name")
    repository_url: Optional[str] = Field(None, description="Git repository URL to clone (defaults to current repository if not specified)")


class ClaudeCodeRunResponse(BaseModel):
    """Response for Claude-Code run initiation."""
    run_id: str = Field(..., description="Unique identifier for the run")
    status: str = Field(..., description="Current status: pending, running, completed, failed")
    message: str = Field(..., description="Status message")
    session_id: str = Field(..., description="Session ID for the run")
    workflow_name: str = Field(..., description="Workflow being executed")
    started_at: datetime = Field(..., description="When the run was started")


class ClaudeCodeStatusResponse(BaseModel):
    """Response for Claude-Code run status."""
    run_id: str = Field(..., description="Unique identifier for the run")
    status: str = Field(..., description="Current status: pending, running, completed, failed")
    session_id: str = Field(..., description="Session ID for the run")
    workflow_name: str = Field(..., description="Workflow being executed")
    started_at: datetime = Field(..., description="When the run was started")
    updated_at: Optional[datetime] = Field(None, description="When the run was last updated")
    container_id: Optional[str] = Field(None, description="Docker container ID")
    execution_time: Optional[float] = Field(None, description="Execution time in seconds")
    
    # Only populated when status is "completed" or "failed"
    result: Optional[str] = Field(None, description="Execution result")
    exit_code: Optional[int] = Field(None, description="Exit code")
    git_commits: List[str] = Field(default_factory=list, description="Git commit SHAs")
    error: Optional[str] = Field(None, description="Error message if failed")
    logs: Optional[str] = Field(None, description="Container logs")


class WorkflowInfo(BaseModel):
    """Information about an available workflow."""
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    path: str = Field(..., description="Path to workflow configuration")
    valid: bool = Field(..., description="Whether the workflow is valid")


async def execute_claude_code_async(
    run_id: str,
    request: ClaudeCodeRunRequest,
    session_id: str
) -> None:
    """Execute Claude-Code agent in background."""
    try:
        logger.info(f"Starting async Claude-Code execution for run {run_id}")
        
        # Get the claude-code agent
        agent = AgentFactory.get_agent("claude_code")
        if not agent:
            raise HTTPException(status_code=404, detail="Claude-Code agent not found")
        
        # Update session metadata to mark as running
        session = session_repo.get_session(uuid.UUID(session_id))
        if session:
            metadata = session.metadata or {}
            metadata.update({
                "run_id": run_id,
                "run_status": "running",
                "started_at": datetime.utcnow().isoformat(),
                "workflow_name": request.workflow_name,
                "container_id": None  # Will be updated by agent
            })
            session.metadata = metadata
            session_repo.update_session(session)
        
        # Set workflow context for the agent
        agent.context["workflow_name"] = request.workflow_name
        agent.context["session_id"] = session_id
        agent.context["run_id"] = run_id  # Pass run_id for log management
        if request.repository_url:
            agent.context["repository_url"] = request.repository_url
        
        # Execute the Claude-Code agent
        result = await agent.run(
            input_text=request.message,
            message_history_obj=None  # Agent handles its own message storage
        )
        
        # Update session with completion status
        if session:
            metadata = session.metadata or {}
            metadata.update({
                "run_id": run_id,
                "run_status": "completed" if result.success else "failed",
                "completed_at": datetime.utcnow().isoformat(),
                "result": result.text if result.success else None,
                "error": result.error_message if not result.success else None
            })
            session.metadata = metadata
            session_repo.update_session(session)
        
        logger.info(f"Claude-Code execution completed for run {run_id}, success: {result.success}")
        
    except Exception as e:
        logger.error(f"Claude-Code async execution failed for run {run_id}: {e}")
        
        # Update session with error status
        try:
            session = session_repo.get_session(uuid.UUID(session_id))
            if session:
                metadata = session.metadata or {}
                metadata.update({
                    "run_id": run_id,
                    "run_status": "failed",
                    "completed_at": datetime.utcnow().isoformat(),
                    "error": str(e)
                })
                session.metadata = metadata
                session_repo.update_session(session)
        except Exception as update_error:
            logger.error(f"Failed to update session after error: {update_error}")


@claude_code_router.post("/run", response_model=ClaudeCodeRunResponse)
async def run_claude_code_workflow(
    request: ClaudeCodeRunRequest,
    background_tasks: BackgroundTasks
) -> ClaudeCodeRunResponse:
    """
    Start a Claude-Code workflow execution asynchronously.
    
    This endpoint starts a containerized Claude CLI execution for the specified workflow
    and returns immediately with a run_id for status tracking.
    
    **Supported Workflows:**
    - `architect`: Design system architecture
    - `implement`: Implement features from architecture
    - `test`: Write and run tests
    - `review`: Review code changes
    - `fix`: Fix bugs and issues
    - `refactor`: Refactor code
    - `document`: Create documentation
    - `pr`: Prepare pull requests
    
    **Example:**
    ```bash
    POST /api/v1/agent/claude-code/run
    {
        "workflow_name": "fix",
        "message": "Fix the session timeout issue in agent controller",
        "git_branch": "fix/session-timeout",
        "max_turns": 50,
        "repository_url": "https://github.com/myorg/myrepo.git"
    }
    ```
    
    **Returns:**
    Immediate response with run_id for status polling.
    """
    try:
        # Validate workflow exists
        agent = AgentFactory.get_agent("claude_code")
        if not agent:
            raise HTTPException(status_code=404, detail="Claude-Code agent not available")
        
        # Get available workflows
        workflows = await agent.get_available_workflows()
        if request.workflow_name not in workflows:
            available = list(workflows.keys())
            raise HTTPException(
                status_code=404, 
                detail=f"Workflow '{request.workflow_name}' not found. Available: {available}"
            )
        
        # Validate workflow is valid
        workflow_info = workflows[request.workflow_name]
        if not workflow_info.get("valid", False):
            raise HTTPException(
                status_code=400,
                detail=f"Workflow '{request.workflow_name}' is not valid: {workflow_info.get('description', 'Unknown error')}"
            )
        
        # Generate run ID
        run_id = f"run_{uuid.uuid4().hex[:12]}"
        
        # Handle user creation if needed
        user_id = request.user_id
        if not user_id:
            # Create anonymous user for the run
            from src.db.models import User
            new_user = User(
                email=f"claude-code-{run_id}@automagik-agents.ai",
                phone_number=None,
                user_data={"created_for": "claude-code-run", "run_id": run_id}
            )
            user_id = str(user_repo.create_user(new_user))
        
        # Create session for the run
        from src.db.models import Session
        session = Session(
            agent_id=None,  # Will be set when agent is loaded
            name=request.session_name or f"claude-code-{request.workflow_name}-{run_id}",
            platform="claude-code-api",
            user_id=uuid.UUID(user_id) if user_id else None,
            metadata={
                "run_id": run_id,
                "run_status": "pending",
                "workflow_name": request.workflow_name,
                "created_at": datetime.utcnow().isoformat(),
                "request": request.dict(),
                "agent_type": "claude-code"
            }
        )
        session_id = session_repo.create_session(session)
        
        # Start background execution
        background_tasks.add_task(
            execute_claude_code_async,
            run_id,
            request,
            str(session_id)
        )
        
        return ClaudeCodeRunResponse(
            run_id=run_id,
            status="pending",
            message=f"Claude-Code {request.workflow_name} workflow started",
            session_id=str(session_id),
            workflow_name=request.workflow_name,
            started_at=datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting Claude-Code workflow {request.workflow_name}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start workflow: {str(e)}")


@claude_code_router.get("/run/{run_id}/status", response_model=ClaudeCodeStatusResponse)
async def get_claude_code_run_status(
    run_id: str
) -> ClaudeCodeStatusResponse:
    """
    Get the status of a Claude-Code run.
    
    **Status Values:**
    - `pending`: Run is queued but not started
    - `running`: Run is currently executing in container
    - `completed`: Run finished successfully
    - `failed`: Run failed with an error
    
    **Example:**
    ```bash
    GET /api/v1/agent/claude-code/run/run_abc123/status
    ```
    
    **Returns:**
    Current status and results (if completed).
    """
    try:
        # Find session by run_id
        sessions = session_repo.list_sessions()
        
        target_session = None
        for session in sessions:
            if session.metadata and session.metadata.get('run_id') == run_id:
                target_session = session
                break
        
        if not target_session:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        
        metadata = target_session.metadata or {}
        
        # Get messages for additional context
        from src.db.repository import message as message_repo
        messages = message_repo.list_messages(target_session.id)
        
        # Find the latest assistant message for results
        latest_result = None
        assistant_messages = [msg for msg in messages if msg.role == 'assistant']
        if assistant_messages:
            latest = assistant_messages[-1]
            latest_result = latest.text_content
        
        # Extract execution details from metadata
        execution_time = None
        container_id = metadata.get('container_id')
        git_commits = metadata.get('git_commits', [])
        exit_code = metadata.get('exit_code')
        
        # Get live logs from log manager
        log_manager = get_log_manager()
        log_entries = await log_manager.get_logs(run_id, follow=False)  # Get all logs
        
        # Convert log entries to text format for API response
        logs = ""
        if log_entries:
            log_lines = []
            for entry in log_entries[-1000:]:  # Last 1000 entries to avoid huge responses
                timestamp = entry.get('timestamp', '')
                event_type = entry.get('event_type', 'log')
                data = entry.get('data', {})
                
                # Extract message from data
                if isinstance(data, dict):
                    message = data.get('message', str(data))
                else:
                    message = str(data)
                
                log_lines.append(f"{timestamp} [{event_type}] {message}")
            
            logs = "\n".join(log_lines)
        
        # Get log summary for additional metadata
        log_summary = await log_manager.get_log_summary(run_id)
        
        # Calculate execution time if we have start/end times
        started_at_str = metadata.get('started_at')
        completed_at_str = metadata.get('completed_at')
        if started_at_str and completed_at_str:
            try:
                start_time = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(completed_at_str.replace('Z', '+00:00'))
                execution_time = (end_time - start_time).total_seconds()
            except Exception:
                pass
        elif log_summary.get("start_time") and log_summary.get("end_time"):
            # Fallback to log timestamps
            try:
                start_time = datetime.fromisoformat(log_summary["start_time"].replace('Z', '+00:00'))
                end_time = datetime.fromisoformat(log_summary["end_time"].replace('Z', '+00:00'))
                execution_time = (end_time - start_time).total_seconds()
            except Exception:
                pass
        
        # Determine updated_at time
        updated_at = None
        if completed_at_str:
            try:
                updated_at = datetime.fromisoformat(completed_at_str.replace('Z', '+00:00'))
            except Exception:
                pass
        elif started_at_str:
            try:
                updated_at = datetime.fromisoformat(started_at_str.replace('Z', '+00:00'))
            except Exception:
                pass
        
        return ClaudeCodeStatusResponse(
            run_id=run_id,
            status=metadata.get('run_status', 'unknown'),
            session_id=str(target_session.id),
            workflow_name=metadata.get('workflow_name', 'unknown'),
            started_at=target_session.created_at,
            updated_at=updated_at,
            container_id=container_id,
            execution_time=execution_time,
            result=latest_result,
            exit_code=exit_code,
            git_commits=git_commits if isinstance(git_commits, list) else [],
            error=metadata.get('error'),
            logs=logs
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Claude-Code run status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get run status: {str(e)}")


@claude_code_router.get("/workflows", response_model=List[WorkflowInfo])
async def list_claude_code_workflows() -> List[WorkflowInfo]:
    """
    List all available Claude-Code workflows.
    
    **Returns:**
    List of available workflows with their descriptions and validation status.
    
    **Example:**
    ```bash
    GET /api/v1/agent/claude-code/workflows
    ```
    """
    try:
        # Get the claude-code agent
        agent = AgentFactory.get_agent("claude_code")
        if not agent:
            raise HTTPException(status_code=404, detail="Claude-Code agent not available")
        
        # Get available workflows
        workflows = await agent.get_available_workflows()
        
        # Convert to response format
        workflow_list = []
        for name, info in workflows.items():
            workflow_list.append(WorkflowInfo(
                name=name,
                description=info.get("description", "No description available"),
                path=info.get("path", ""),
                valid=info.get("valid", False)
            ))
        
        return workflow_list
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing Claude-Code workflows: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list workflows: {str(e)}")


@claude_code_router.get("/health")
async def claude_code_health() -> Dict[str, Any]:
    """
    Check Claude-Code agent health and status.
    
    **Returns:**
    Health status including agent availability, container status, and workflow validation.
    """
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "agent_available": False,
            "workflows": {},
            "container_manager": False,
            "feature_enabled": False
        }
        
        # Check if claude CLI is available
        from src.agents.claude_code.cli_executor import is_claude_available, get_claude_path
        claude_available = is_claude_available()
        claude_path = get_claude_path()
        
        health_status["feature_enabled"] = claude_available
        health_status["claude_cli_path"] = claude_path
        
        if not claude_available:
            health_status["status"] = "disabled"
            health_status["message"] = (
                "Claude CLI not found. Please install it with: npm install -g @anthropic-ai/claude-cli\n"
                "Make sure Node.js is installed and the claude command is in your PATH."
            )
            return health_status
        
        # Also check for credentials
        from pathlib import Path
        claude_credentials = Path.home() / ".claude" / ".credentials.json"
        if not claude_credentials.exists():
            health_status["status"] = "warning"
            health_status["message"] = f"Claude CLI found at {claude_path} but no credentials at {claude_credentials}"
        
        # Check agent availability
        try:
            agent = AgentFactory.get_agent("claude_code")
            if agent:
                health_status["agent_available"] = True
                
                # Check workflows
                workflows = await agent.get_available_workflows()
                health_status["workflows"] = {
                    name: info.get("valid", False) 
                    for name, info in workflows.items()
                }
                
                # Check container manager
                if hasattr(agent, 'container_manager'):
                    health_status["container_manager"] = True
        except Exception as e:
            health_status["status"] = "error"
            health_status["error"] = f"Agent error: {str(e)}"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error checking Claude-Code health: {e}")
        return {
            "status": "error",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


