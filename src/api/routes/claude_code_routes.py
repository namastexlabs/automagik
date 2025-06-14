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
from src.agents.claude_code.raw_stream_processor import RawStreamProcessor
from src.agents.claude_code.completion_tracker import CompletionTracker
from src.db.repository import session as session_repo
from src.db.repository import user as user_repo

logger = logging.getLogger(__name__)

# Create router for claude-code endpoints
claude_code_router = APIRouter(prefix="/workflows/claude-code", tags=["Claude-Code"])


async def _analyze_claude_stream_debug_info(
    log_entries: List[Dict], metadata: Dict, assistant_messages: List
) -> Dict[str, Any]:
    """Analyze Claude stream logs to extract debug information.

    Args:
        log_entries: Raw log entries from the log manager
        metadata: Session metadata
        assistant_messages: Assistant messages from the database

    Returns:
        Debug information dictionary with Claude stream analysis
    """
    debug_info = {
        "claude_command": {},
        "stream_analysis": {},
        "tool_usage": {},
        "execution_stats": {},
        "costs": {},
        "raw_streams": [],
        "session_info": {},
    }

    # Extract Claude command information
    claude_command_info = {}
    execution_stats = {
        "total_turns": 0,
        "tool_calls": 0,
        "event_counts": {},
        "cost_usd": 0.0,
        "duration_ms": 0,
    }
    tool_usage = {}
    raw_claude_streams = []

    # Analyze log entries for Claude stream data
    for entry in log_entries:
        event_type = entry.get("event_type", "")
        data = entry.get("data", {})

        # Count event types
        execution_stats["event_counts"][event_type] = (
            execution_stats["event_counts"].get(event_type, 0) + 1
        )

        # Extract Claude command information
        if event_type == "early_execution_start" and isinstance(data, dict):
            if "command" in data:
                claude_command_info.update(
                    {
                        "command": data.get("command"),
                        "args": data.get("args", []),
                        "working_dir": data.get("working_dir"),
                        "timeout": data.get("timeout"),
                    }
                )

        # Extract Claude CLI result information (cost, turns, etc.)
        if event_type == "result_captured" and isinstance(data, dict):
            result_data = data.get("result_data", {})
            if isinstance(result_data, dict):
                execution_stats.update(
                    {
                        "cost_usd": result_data.get("cost_usd", 0.0),
                        "duration_ms": result_data.get("duration_ms", 0),
                        "total_turns": result_data.get("num_turns", 0),
                    }
                )

        # Extract tool usage from Claude stream
        if "claude_stream" in str(data).lower() or event_type == "claude_output":
            try:
                # Try to parse Claude stream JSON
                if isinstance(data, dict) and "message" in data:
                    message = data["message"]
                    if isinstance(message, str) and message.strip().startswith("{"):
                        import json

                        stream_data = json.loads(message)
                        raw_claude_streams.append(stream_data)

                        # Analyze tool usage
                        if stream_data.get("type") == "tool_use":
                            tool_name = stream_data.get("name", "unknown")
                            tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1
                            execution_stats["tool_calls"] += 1

                        # Count assistant messages/turns
                        if stream_data.get("type") == "assistant":
                            execution_stats["total_turns"] += 1

            except (json.JSONDecodeError, AttributeError):
                pass

    # Extract additional session information
    session_info = {
        "workflow_name": metadata.get("workflow_name"),
        "git_branch": metadata.get("git_branch"),
        "container_id": metadata.get("container_id"),
        "run_id": metadata.get("run_id"),
        "claude_session_id": metadata.get("claude_session_id"),
        "max_turns_requested": metadata.get("request", {}).get("max_turns")
        if isinstance(metadata.get("request"), dict)
        else None,
        "timeout_requested": metadata.get("request", {}).get("timeout")
        if isinstance(metadata.get("request"), dict)
        else None,
        "repository_url": metadata.get("request", {}).get("repository_url")
        if isinstance(metadata.get("request"), dict)
        else None,
    }

    # Build comprehensive debug response
    debug_info.update(
        {
            "claude_command": claude_command_info,
            "stream_analysis": {
                "total_stream_entries": len(raw_claude_streams),
                "stream_types": list(
                    set([s.get("type") for s in raw_claude_streams if s.get("type")])
                ),
                "raw_streams": raw_claude_streams[-50:]
                if len(raw_claude_streams) > 50
                else raw_claude_streams,  # Last 50 entries
            },
            "tool_usage": tool_usage,
            "execution_stats": execution_stats,
            "costs": {
                "total_usd": execution_stats.get("cost_usd", 0.0),
                "currency": "USD",
            },
            "session_info": session_info,
            "message_analysis": {
                "total_assistant_messages": len(assistant_messages),
                "last_message_length": len(assistant_messages[-1].text_content)
                if assistant_messages
                else 0,
                "total_content_length": sum(
                    len(msg.text_content or "") for msg in assistant_messages
                ),
            },
        }
    )

    return debug_info


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

    # Real-time tracking fields (populated for running workflows)
    cost: Optional[float] = Field(None, description="Cost in USD")
    tokens: Optional[int] = Field(None, description="Token count")
    turns: Optional[int] = Field(None, description="Conversation turns")
    tool_calls: Optional[int] = Field(None, description="Tool calls made")
    tools_used: Optional[List[str]] = Field(None, description="Tools used")
    claude_session_id: Optional[str] = Field(None, description="Claude CLI session ID")
    progress_indicator: Optional[str] = Field(None, description="Human-readable progress")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    recent_steps: Optional[Dict[str, Any]] = Field(None, description="Recent execution steps")
    elapsed_seconds: Optional[int] = Field(None, description="Elapsed execution time")

    # Debug information (only when debug=true)
    debug_info: Optional[Dict[str, Any]] = Field(
        None, description="Debug information including Claude stream analysis"
    )


class ClaudeCodeRunSummary(BaseModel):
    """Summary of a Claude Code run for listing purposes."""

    run_id: str = Field(..., description="Unique identifier for the run")
    status: str = Field(
        ..., description="Current status: pending, running, completed, failed"
    )
    workflow_name: str = Field(..., description="Workflow that was executed")
    started_at: datetime = Field(..., description="When the run was started")
    completed_at: Optional[datetime] = Field(
        None, description="When the run was completed"
    )
    execution_time: Optional[float] = Field(
        None, description="Total execution time in seconds"
    )
    total_tokens: Optional[int] = Field(None, description="Total tokens used")
    total_cost: Optional[float] = Field(None, description="Total cost in USD")
    turns: Optional[int] = Field(None, description="Number of conversation turns")
    tool_calls: Optional[int] = Field(None, description="Number of tool calls made")
    result: Optional[str] = Field(None, description="Brief result summary")


class ClaudeCodeRunsListResponse(BaseModel):
    """Response for listing Claude Code runs."""

    runs: List[ClaudeCodeRunSummary] = Field(..., description="List of runs")
    total_count: int = Field(..., description="Total number of runs matching filters")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of runs per page")
    has_next: bool = Field(..., description="Whether there are more pages")


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
    
    ## Available Workflows:
    - **architect**: Design system architecture and technical specifications
    - **implement**: Implement features based on architectural designs  
    - **test**: Create comprehensive test suites and validation
    - **review**: Perform code review and quality assessment
    - **fix**: Apply surgical fixes for specific issues
    - **refactor**: Improve code structure and maintainability
    - **document**: Generate comprehensive documentation
    - **pr**: Prepare pull requests for review
    """,
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
        # Ensure logging doesn't interfere with API response
        try:
            result = await agent.execute_until_first_response(
                input_text=request.message,
                workflow_name=workflow_name,
                session_id=str(session_id),
                git_branch=request.git_branch,
                max_turns=request.max_turns,
                timeout=request.timeout,
                repository_url=request.repository_url,
            )
        except Exception as exec_error:
            logger.error(f"Execution error in workflow {workflow_name}: {exec_error}")
            # Return a clean error response without any subprocess output contamination
            result = {
                "run_id": run_id,
                "status": "failed",
                "message": f"Failed to start {workflow_name} workflow: {str(exec_error)}",
                "started_at": datetime.utcnow().isoformat(),
            }

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
            
            # Start completion tracking for background execution
            if result.get("status") == "running":
                await CompletionTracker.track_completion(
                    run_id=result.get("run_id", run_id),
                    session_id=str(session_id),
                    workflow_name=workflow_name,
                    max_wait_time=request.timeout or 7200
                )

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


@claude_code_router.get("/runs", response_model=ClaudeCodeRunsListResponse)
async def list_claude_code_runs(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    workflow_name: Optional[str] = None,
    user_id: Optional[str] = None,
    sort_by: str = "started_at",
    sort_order: str = "desc",
) -> ClaudeCodeRunsListResponse:
    """
    List all Claude Code runs with comprehensive filtering and pagination.

    **Parameters:**
    - `page`: Page number (starts from 1)
    - `page_size`: Number of runs per page (max 100)
    - `status`: Filter by run status (pending, running, completed, failed)
    - `workflow_name`: Filter by workflow name
    - `user_id`: Filter by user ID
    - `sort_by`: Sort field (started_at, completed_at, execution_time, total_cost)
    - `sort_order`: Sort order (asc, desc)

    **Returns:**
    Paginated list of Claude Code runs with summary information including:
    - run_id, status, workflow_name, timestamps
    - execution_time, total_tokens, total_cost, turns, tool_calls
    - Brief result summary

    **Examples:**
    ```bash
    # List all runs
    GET /api/v1/workflows/claude-code/runs

    # Filter by status and workflow
    GET /api/v1/workflows/claude-code/runs?status=completed&workflow_name=architect

    # Paginate and sort by cost
    GET /api/v1/workflows/claude-code/runs?page=2&page_size=10&sort_by=total_cost&sort_order=desc
    ```
    """
    try:
        # Validate parameters
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise HTTPException(
                status_code=400, detail="Page size must be between 1 and 100"
            )
        if sort_by not in [
            "started_at",
            "completed_at",
            "execution_time",
            "total_cost",
        ]:
            raise HTTPException(status_code=400, detail="Invalid sort_by field")
        if sort_order not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400, detail="Sort order must be 'asc' or 'desc'"
            )
        if status and status not in ["pending", "running", "completed", "failed"]:
            raise HTTPException(status_code=400, detail="Invalid status filter")

        # Get all sessions that are Claude Code runs
        sessions = session_repo.list_sessions()
        claude_code_sessions = []

        for session in sessions:
            metadata = session.metadata or {}
            run_id = metadata.get("run_id")
            session_workflow = metadata.get("workflow_name")
            session_status = metadata.get("run_status")

            # Filter for Claude Code sessions only
            if not run_id or metadata.get("agent_type") != "claude-code":
                continue

            # Apply filters
            if status and session_status != status:
                continue
            if workflow_name and session_workflow != workflow_name:
                continue
            if user_id and str(session.user_id) != user_id:
                continue

            claude_code_sessions.append((session, metadata))

        # Process runs and extract metrics
        runs_data = []
        log_manager = get_log_manager()

        for session, metadata in claude_code_sessions:
            run_id = metadata.get("run_id")

            # Get execution metrics from logs using raw stream processor
            log_entries = await log_manager.get_logs(run_id, follow=False)
            
            # Use raw stream processor to extract comprehensive metrics
            processor = RawStreamProcessor()
            
            # Process all claude stream events to extract accurate metrics
            for entry in log_entries:
                event_type = entry.get("event_type", "")
                data = entry.get("data", {})
                
                # Process Claude CLI stream events (use parsed events only to avoid duplication)
                if event_type.startswith("claude_stream_") and event_type not in ["claude_stream_raw"]:
                    if isinstance(data, dict):
                        # Process parsed JSON events only (not raw strings)
                        processor.process_event(data)
                
                # Also try to process claude_output events (legacy format)
                elif event_type == "claude_output":
                    if isinstance(data, dict) and "message" in data:
                        message = data["message"]
                        if isinstance(message, str) and message.strip().startswith("{"):
                            processor.process_line(message.strip())
            
            # Get comprehensive metrics from processor
            metrics = processor.get_metrics()
            
            # Build execution stats from processed metrics
            execution_stats = {
                "total_turns": metrics.total_turns,
                "tool_calls": metrics.tool_calls,
                "cost_usd": metrics.total_cost_usd,  # Using correct field name
                "total_tokens": metrics.total_tokens,  # Comprehensive token sum
                "duration_ms": metrics.duration_ms,
            }

            # Calculate execution time
            execution_time = None
            started_at_str = metadata.get("started_at")
            completed_at_str = metadata.get("completed_at")
            completed_at = None

            if started_at_str and completed_at_str:
                try:
                    start_time = datetime.fromisoformat(
                        started_at_str.replace("Z", "+00:00")
                    )
                    end_time = datetime.fromisoformat(
                        completed_at_str.replace("Z", "+00:00")
                    )
                    execution_time = (end_time - start_time).total_seconds()
                    completed_at = end_time
                except Exception:
                    pass
            elif execution_stats["duration_ms"] > 0:
                execution_time = execution_stats["duration_ms"] / 1000.0

            # Get latest assistant message for result summary
            from src.db.repository import message as message_repo

            messages = message_repo.list_messages(session.id)
            assistant_messages = [msg for msg in messages if msg.role == "assistant"]
            result_summary = None
            if assistant_messages:
                latest = assistant_messages[-1]
                result_text = latest.text_content or ""
                # Extract first sentence or first 200 chars as summary
                result_summary = (
                    result_text.split(".")[0][:200] + "..."
                    if len(result_text) > 200
                    else result_text
                )

            # For running workflows, use current progress data if available
            status = metadata.get("run_status", "unknown")
            if status == "running":
                # Use real-time progress data
                runs_data.append(
                    {
                        "run_id": run_id,
                        "status": status,
                        "workflow_name": metadata.get("workflow_name", "unknown"),
                        "started_at": session.created_at,
                        "completed_at": completed_at,
                        "execution_time": execution_time,
                        "total_tokens": metadata.get("current_tokens") or execution_stats.get("total_tokens") or None,
                        "total_cost": metadata.get("current_cost_usd") or execution_stats.get("cost_usd") or None,
                        "turns": metadata.get("current_turns") or execution_stats.get("total_turns") or None,
                        "tool_calls": metadata.get("current_tool_calls") or execution_stats.get("tool_calls") or None,
                        "result": metadata.get("progress_indicator") or result_summary,
                        # Additional real-time fields
                        "last_updated": metadata.get("last_updated"),
                        "elapsed_seconds": metadata.get("elapsed_seconds"),
                        "recent_activity": metadata.get("recent_steps", {}),
                        "claude_session_id": metadata.get("claude_session_id"),
                        "tools_used_so_far": metadata.get("tools_used_so_far", [])
                    }
                )
            else:
                # Use final completion data
                runs_data.append(
                    {
                        "run_id": run_id,
                        "status": status,
                        "workflow_name": metadata.get("workflow_name", "unknown"),
                        "started_at": session.created_at,
                        "completed_at": completed_at,
                        "execution_time": execution_time,
                        "total_tokens": metadata.get("total_tokens") or execution_stats.get("total_tokens") or None,
                        "total_cost": metadata.get("total_cost_usd") or execution_stats.get("cost_usd") or None,
                        "turns": metadata.get("total_turns") or execution_stats.get("total_turns") or None,
                        "tool_calls": metadata.get("tool_calls") or execution_stats.get("tool_calls") or None,
                        "result": result_summary,
                        # Completion-specific fields
                        "claude_session_id": metadata.get("claude_session_id"),
                        "tool_names_used": metadata.get("tool_names_used", []),
                        "success": metadata.get("success"),
                        "error_message": metadata.get("error_message"),
                        "model_used": metadata.get("model_used")
                    }
                )

        # Sort runs
        reverse_sort = sort_order == "desc"
        if sort_by == "started_at":
            runs_data.sort(
                key=lambda x: x["started_at"] or datetime.min, reverse=reverse_sort
            )
        elif sort_by == "completed_at":
            runs_data.sort(
                key=lambda x: x["completed_at"] or datetime.min, reverse=reverse_sort
            )
        elif sort_by == "execution_time":
            runs_data.sort(key=lambda x: x["execution_time"] or 0, reverse=reverse_sort)
        elif sort_by == "total_cost":
            runs_data.sort(key=lambda x: x["total_cost"] or 0, reverse=reverse_sort)

        # Paginate
        total_count = len(runs_data)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_runs = runs_data[start_idx:end_idx]

        # Convert to response models
        run_summaries = [
            ClaudeCodeRunSummary(**run_data) for run_data in paginated_runs
        ]

        return ClaudeCodeRunsListResponse(
            runs=run_summaries,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=end_idx < total_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing Claude Code runs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list runs: {str(e)}")


@claude_code_router.get("/run/{run_id}/status", response_model=ClaudeCodeStatusResponse)
async def get_claude_code_run_status(
    run_id: str, debug: bool = False
) -> ClaudeCodeStatusResponse:
    """
    Get the status of a Claude-Code run.

    **Status Values:**
    - `pending`: Run is queued but not started
    - `running`: Run is currently executing in container
    - `completed`: Run finished successfully
    - `failed`: Run failed with an error

    **Parameters:**
    - `debug` (optional): If true, includes detailed debug information about Claude stream analysis, tool usage, costs, and command details

    **Examples:**
    ```bash
    # Basic status
    GET /api/v1/workflows/claude-code/run/run_abc123/status

    # With debug information
    GET /api/v1/workflows/claude-code/run/run_abc123/status?debug=true
    ```

    **Returns:**
    Current status and results (if completed). When debug=true, includes comprehensive debugging information.
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
        debug_info = None

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

            # If debug flag is enabled, analyze logs for Claude stream data
            if debug:
                debug_info = await _analyze_claude_stream_debug_info(
                    log_entries, metadata, assistant_messages
                )

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

        # Parse last_activity timestamp
        last_activity = None
        if metadata.get("last_activity"):
            try:
                last_activity = datetime.fromisoformat(
                    metadata["last_activity"].replace("Z", "+00:00")
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
            debug_info=debug_info,
            # Real-time tracking fields
            cost=metadata.get("current_cost_usd"),
            tokens=metadata.get("current_tokens"),
            turns=metadata.get("current_turns"),
            tool_calls=metadata.get("current_tool_calls"),
            tools_used=metadata.get("tools_used_so_far"),
            claude_session_id=metadata.get("claude_session_id"),
            progress_indicator=metadata.get("progress_indicator"),
            last_activity=last_activity,
            recent_steps=metadata.get("recent_steps"),
            elapsed_seconds=metadata.get("elapsed_seconds"),
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
