"""Claude-Code specific API routes.

This module provides specialized endpoints for the Claude-Code agent framework,
supporting workflow-based execution and async container management.
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Path, Body
from pydantic import BaseModel, Field

from src.agents.models.agent_factory import AgentFactory
from src.agents.claude_code.log_manager import get_log_manager
from src.db.repository import session as session_repo
from src.db.repository import user as user_repo

logger = logging.getLogger(__name__)

# Create router for claude-code endpoints
claude_code_router = APIRouter(prefix="/workflows/claude-code", tags=["Claude-Code"])


class ClaudeWorkflowRequest(BaseModel):
    """Claude Code workflow execution request (based on real implementation)"""

    message: str = Field(
        ...,
        description="The main task description or prompt for Claude",
        example="Implement user authentication system with JWT tokens",
    )
    max_turns: int = Field(
        default=30,
        ge=1,
        le=100,
        description="Maximum conversation turns for the workflow",
        example=50,
    )

    # Real parameters from current ClaudeCodeRunRequest
    session_id: Optional[str] = Field(
        None,
        description="Continue previous session (UUID format)",
        example="550e8400-e29b-41d4-a716-446655440000",
    )
    session_name: Optional[str] = Field(
        None,
        description="Human-readable session name",
        example="auth-system-implementation",
    )
    user_id: Optional[str] = Field(
        None, description="User identifier for tracking", example="user-123"
    )
    git_branch: Optional[str] = Field(
        None, description="Git branch to work on", example="feature/jwt-auth"
    )
    repository_url: Optional[str] = Field(
        None,
        description="External repository URL to clone",
        example="https://github.com/org/my-project.git",
    )
    timeout: int = Field(
        default=7200,
        ge=60,
        le=14400,
        description="Execution timeout in seconds (1-4 hours)",
        example=10800,
    )


class ClaudeWorkflowResponse(BaseModel):
    """Claude Code workflow response"""

    run_id: str = Field(description="Unique run identifier")
    status: str = Field(
        description="Execution status: pending, running, completed, failed"
    )
    message: str = Field(description="Human-readable status message")
    session_id: str = Field(description="Session identifier")
    workflow_name: str = Field(description="The executed workflow name")
    started_at: str = Field(description="ISO timestamp when workflow started")


class ClaudeCodeStatusResponse(BaseModel):
    """Response for Claude-Code run status."""

    run_id: str = Field(..., description="Unique identifier for the run")
    status: str = Field(
        ..., description="Current status: pending, running, completed, failed"
    )
    session_id: str = Field(..., description="Session ID for the run")
    workflow_name: str = Field(..., description="Workflow being executed")
    started_at: datetime = Field(..., description="When the run was started")
    updated_at: Optional[datetime] = Field(
        None, description="When the run was last updated"
    )
    container_id: Optional[str] = Field(None, description="Docker container ID")
    execution_time: Optional[float] = Field(
        None, description="Execution time in seconds"
    )

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


@claude_code_router.post(
    "/run/{workflow_name}",
    response_model=ClaudeWorkflowResponse,
    summary="Execute Claude Code Workflow",
    description="""
    Execute a Claude Code workflow with comprehensive configuration options.
    
    ## Available Workflows (REAL):
    - **architect**: Design system architecture and technical specifications
    - **implement**: Implement features based on architectural designs  
    - **test**: Create comprehensive test suites and validation
    - **review**: Perform code review and quality assessment
    - **fix**: Apply surgical fixes for specific issues
    - **refactor**: Improve code structure and maintainability
    - **document**: Generate comprehensive documentation
    - **pr**: Prepare pull requests for review
    - **genie**: Orchestrate complex multi-agent workflows (meta-workflow)
    - **bug-fixer**: Specialized bug identification and resolution (note: hyphen)
    """,
    tags=["Claude Code Workflows"],
)
async def run_claude_workflow(
    workflow_name: str = Path(
        ..., description="The workflow to execute", example="architect"
    ),
    request: ClaudeWorkflowRequest = Body(...),
) -> ClaudeWorkflowResponse:
    """Execute Claude Code workflow with comprehensive configuration"""
    try:
        # Validate workflow exists
        agent = AgentFactory.get_agent("claude_code")
        if not agent:
            raise HTTPException(
                status_code=404, detail="Claude-Code agent not available"
            )

        # Get available workflows
        workflows = await agent.get_available_workflows()
        if workflow_name not in workflows:
            available = list(workflows.keys())
            raise HTTPException(
                status_code=404,
                detail=f"Workflow '{workflow_name}' not found. Available: {available}",
            )

        # Validate workflow is valid
        workflow_info = workflows[workflow_name]
        if not workflow_info.get("valid", False):
            raise HTTPException(
                status_code=400,
                detail=f"Workflow '{workflow_name}' is not valid: {workflow_info.get('description', 'Unknown error')}",
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
                user_data={"created_for": "claude-code-run", "run_id": run_id},
            )
            user_id = str(user_repo.create_user(new_user))

        # Create session for the run
        from src.db.models import Session

        session = Session(
            agent_id=None,  # Will be set when agent is loaded
            name=request.session_name or f"claude-code-{workflow_name}-{run_id}",
            platform="claude-code-api",
            user_id=uuid.UUID(user_id) if user_id else None,
            metadata={
                "run_id": run_id,
                "run_status": "pending",
                "workflow_name": workflow_name,
                "created_at": datetime.utcnow().isoformat(),
                "request": request.dict(),
                "agent_type": "claude-code",
            },
        )
        session_id = session_repo.create_session(session)

        # Execute synchronously until first response
        result = await agent.execute_until_first_response(
            input_text=request.message,
            workflow_name=workflow_name,
            session_id=str(session_id),
            git_branch=request.git_branch,
            max_turns=request.max_turns,
            timeout=request.timeout,
            repository_url=request.repository_url,
        )

        # Update session metadata with execution results
        if session:
            metadata = session.metadata or {}
            metadata.update(
                {
                    "run_id": result.get("run_id"),
                    "run_status": result.get("status"),
                    "started_at": result.get("started_at"),
                    "workflow_name": workflow_name,
                    "claude_session_id": result.get("claude_session_id"),
                    "git_branch": result.get("git_branch"),
                }
            )
            session.metadata = metadata
            session_repo.update_session(session)

        # Return response with actual Claude message
        return ClaudeWorkflowResponse(
            run_id=result.get("run_id", run_id),
            status=result.get("status", "failed"),
            message=result.get("message", f"Failed to start {workflow_name} workflow"),
            session_id=str(session_id),
            workflow_name=workflow_name,
            started_at=result.get("started_at", datetime.utcnow().isoformat()),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting Claude-Code workflow {workflow_name}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to start workflow: {str(e)}"
        )


@claude_code_router.get("/run/{run_id}/status", response_model=ClaudeCodeStatusResponse)
async def get_claude_code_run_status(run_id: str) -> ClaudeCodeStatusResponse:
    """
    Get the status of a Claude-Code run.

    **Status Values:**
    - `pending`: Run is queued but not started
    - `running`: Run is currently executing in container
    - `completed`: Run finished successfully
    - `failed`: Run failed with an error

    **Example:**
    ```bash
    GET /api/v1/workflows/claude-code/run/run_abc123/status
    ```

    **Returns:**
    Current status and results (if completed).
    """
    try:
        # Find session by run_id
        sessions = session_repo.list_sessions()

        target_session = None
        for session in sessions:
            if session.metadata and session.metadata.get("run_id") == run_id:
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
        assistant_messages = [msg for msg in messages if msg.role == "assistant"]
        if assistant_messages:
            latest = assistant_messages[-1]
            latest_result = latest.text_content

        # Extract execution details from metadata
        execution_time = None
        container_id = metadata.get("container_id")
        git_commits = metadata.get("git_commits", [])
        exit_code = metadata.get("exit_code")

        # Get live logs from log manager
        log_manager = get_log_manager()
        log_entries = await log_manager.get_logs(run_id, follow=False)  # Get all logs

        # Convert log entries to text format for API response
        logs = ""
        if log_entries:
            log_lines = []
            for entry in log_entries[
                -1000:
            ]:  # Last 1000 entries to avoid huge responses
                timestamp = entry.get("timestamp", "")
                event_type = entry.get("event_type", "log")
                data = entry.get("data", {})

                # Extract message from data
                if isinstance(data, dict):
                    message = data.get("message", str(data))
                else:
                    message = str(data)

                log_lines.append(f"{timestamp} [{event_type}] {message}")

            logs = "\n".join(log_lines)

        # Get log summary for additional metadata
        log_summary = await log_manager.get_log_summary(run_id)

        # Calculate execution time if we have start/end times
        started_at_str = metadata.get("started_at")
        completed_at_str = metadata.get("completed_at")
        if started_at_str and completed_at_str:
            try:
                start_time = datetime.fromisoformat(
                    started_at_str.replace("Z", "+00:00")
                )
                end_time = datetime.fromisoformat(
                    completed_at_str.replace("Z", "+00:00")
                )
                execution_time = (end_time - start_time).total_seconds()
            except Exception:
                pass
        elif log_summary.get("start_time") and log_summary.get("end_time"):
            # Fallback to log timestamps
            try:
                start_time = datetime.fromisoformat(
                    log_summary["start_time"].replace("Z", "+00:00")
                )
                end_time = datetime.fromisoformat(
                    log_summary["end_time"].replace("Z", "+00:00")
                )
                execution_time = (end_time - start_time).total_seconds()
            except Exception:
                pass

        # Determine updated_at time
        updated_at = None
        if completed_at_str:
            try:
                updated_at = datetime.fromisoformat(
                    completed_at_str.replace("Z", "+00:00")
                )
            except Exception:
                pass
        elif started_at_str:
            try:
                updated_at = datetime.fromisoformat(
                    started_at_str.replace("Z", "+00:00")
                )
            except Exception:
                pass

        return ClaudeCodeStatusResponse(
            run_id=run_id,
            status=metadata.get("run_status", "unknown"),
            session_id=str(target_session.id),
            workflow_name=metadata.get("workflow_name", "unknown"),
            started_at=target_session.created_at,
            updated_at=updated_at,
            container_id=container_id,
            execution_time=execution_time,
            result=latest_result,
            exit_code=exit_code,
            git_commits=git_commits if isinstance(git_commits, list) else [],
            error=metadata.get("error"),
            logs=logs,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Claude-Code run status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get run status: {str(e)}"
        )


@claude_code_router.get("/workflows", response_model=List[WorkflowInfo])
async def list_claude_code_workflows() -> List[WorkflowInfo]:
    """
    List all available Claude-Code workflows.

    **Returns:**
    List of available workflows with their descriptions and validation status.

    **Example:**
    ```bash
    GET /api/v1/workflows/claude-code/workflows
    ```
    """
    try:
        # Get the claude-code agent
        agent = AgentFactory.get_agent("claude_code")
        if not agent:
            raise HTTPException(
                status_code=404, detail="Claude-Code agent not available"
            )

        # Get available workflows
        workflows = await agent.get_available_workflows()

        # Convert to response format
        workflow_list = []
        for name, info in workflows.items():
            workflow_list.append(
                WorkflowInfo(
                    name=name,
                    description=info.get("description", "No description available"),
                    path=info.get("path", ""),
                    valid=info.get("valid", False),
                )
            )

        return workflow_list

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing Claude-Code workflows: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list workflows: {str(e)}"
        )


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
            "feature_enabled": False,
        }

        # Check if claude CLI is available
        from src.agents.claude_code.cli_executor import (
            is_claude_available,
            get_claude_path,
        )

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
            health_status["message"] = (
                f"Claude CLI found at {claude_path} but no credentials at {claude_credentials}"
            )

        # Check agent availability
        try:
            agent = AgentFactory.get_agent("claude_code")
            if agent:
                health_status["agent_available"] = True

                # Check workflows
                workflows = await agent.get_available_workflows()
                health_status["workflows"] = {
                    name: info.get("valid", False) for name, info in workflows.items()
                }

                # Check container manager
                if hasattr(agent, "container_manager"):
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
            "error": str(e),
        }
