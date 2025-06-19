"""Claude-Code specific API routes.

This module provides specialized endpoints for the Claude-Code agent framework,
supporting workflow-based execution and async container management.
"""

import logging
import uuid
import asyncio
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Path, Body, Query
from pydantic import BaseModel, Field

from src.agents.models.agent_factory import AgentFactory
from src.agents.claude_code.log_manager import get_log_manager
from src.agents.claude_code.raw_stream_processor import RawStreamProcessor
from src.agents.claude_code.completion_tracker import CompletionTracker
from src.agents.claude_code.result_extractor import ResultExtractor
from src.agents.claude_code.progress_tracker import ProgressTracker
from src.agents.claude_code.debug_builder import DebugBuilder
from src.agents.claude_code.stream_parser import StreamParser
from src.agents.claude_code.git_utils import get_git_file_changes, find_repo_root
from src.agents.claude_code.models import (
    EnhancedStatusResponse,
    DebugStatusResponse,
    ProgressInfo,
    MetricsInfo,
    ResultInfo,
    TokenInfo
)
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
    max_turns: Optional[int] = Field(
        None,
        ge=1,
        le=200,
        description="Maximum conversation turns for the workflow (unlimited if not specified)",
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
    
    # PR creation options (UI-driven)
    create_pr_on_success: bool = Field(
        default=False,
        description="Create a Pull Request when workflow completes successfully (UI option)",
        example=False,
    )
    pr_title: Optional[str] = Field(
        None,
        description="Custom title for the PR (defaults to workflow name and run ID)",
        example="feat: Implement JWT authentication system",
    )
    pr_body: Optional[str] = Field(
        None,
        description="Custom body for the PR (defaults to auto-generated summary)",
        example="## Summary\nImplements JWT authentication with secure token handling\n\n## Changes\n- Added JWT middleware\n- Created auth endpoints\n- Updated user model",
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
    
    # Git operation results (populated when workflow completes)
    auto_commit_sha: Optional[str] = Field(
        None, description="SHA of the final auto-commit (if any)"
    )
    pr_url: Optional[str] = Field(
        None, description="URL of the created Pull Request (if any)"
    )
    merge_sha: Optional[str] = Field(
        None, description="SHA of the merge commit to main (if any)"
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
    persistent: bool = Query(
        True, description="Use persistent workspace (default: true, set false for temporary workspace)"
    ),
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

        # Generate run ID - use standard UUID format for MCP server compatibility
        run_id = str(uuid.uuid4())

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

        # Handle session creation or continuation
        session_id = None
        session = None
        
        # Check for session continuation by session_id or session_name
        if request.session_id:
            # Continue existing session by database session_id
            session_id = uuid.UUID(request.session_id)
            session = session_repo.get_session(session_id)
            if not session:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Session {request.session_id} not found"
                )
        elif request.session_name:
            # Try to find existing session by name for continuation
            from src.db import get_session_by_name
            session = get_session_by_name(request.session_name)
            if session:
                session_id = session.id
            
        if not session_id:
            # Create new session
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

        # Start execution asynchronously without waiting for first response
        # This avoids stream contamination from trying to capture early output
        try:
            # Create workflow execution parameters
            execution_params = {
                "input_text": request.message,
                "workflow_name": workflow_name,
                "session_id": str(session_id),
                "git_branch": request.git_branch,
                "max_turns": request.max_turns,
                "timeout": request.timeout,
                "repository_url": request.repository_url,
                "run_id": run_id,
                "persistent": persistent,
            }
            
            # Start workflow execution in background using thread pool to avoid TaskGroup conflicts
            # This prevents Claude SDK's internal TaskGroups from conflicting with FastAPI's event loop
            loop = asyncio.get_event_loop()
            
            def run_workflow_sync():
                """Run workflow in separate thread with isolated event loop."""
                # Create new event loop for this thread
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    # Set flag to bypass TaskGroup conflict detection
                    import os
                    os.environ['BYPASS_TASKGROUP_DETECTION'] = 'true'
                    
                    # Run workflow in isolated event loop
                    return new_loop.run_until_complete(
                        agent.execute_workflow_background(**execution_params)
                    )
                finally:
                    # Clean up environment variable
                    os.environ.pop('BYPASS_TASKGROUP_DETECTION', None)
                    new_loop.close()
            
            # Execute in thread pool to completely isolate from main event loop
            # Use a background thread without asyncio.create_task to avoid TaskGroup conflicts
            import threading
            
            def start_workflow_thread():
                """Start workflow in separate thread immediately."""
                run_workflow_sync()
            
            # Start thread directly - no asyncio.create_task needed
            workflow_thread = threading.Thread(target=start_workflow_thread, daemon=True)
            workflow_thread.start()
            
            # Return immediately with pending status
            result = {
                "run_id": run_id,
                "status": "pending",
                "message": f"Started {workflow_name} workflow. Use the status endpoint to track progress.",
                "started_at": datetime.utcnow().isoformat(),
                "claude_session_id": None,  # Will be available in status endpoint
                "git_branch": request.git_branch,
            }
            
        except Exception as exec_error:
            logger.error(f"Execution error in workflow {workflow_name}: {exec_error}")
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
        # Import workflow_runs repository for enhanced data
        from src.db.repository.workflow_run import list_workflow_runs, get_workflow_runs_by_session
        
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
        if status and status not in ["pending", "running", "completed", "failed", "timeout"]:
            raise HTTPException(status_code=400, detail="Invalid status filter")

        # Use workflow_runs table as primary data source for enhanced performance and accuracy
        workflow_filters = {}
        if status:
            # Map timeout status to failed for workflow_runs table
            workflow_filters['status'] = 'failed' if status == 'timeout' else status
        if workflow_name:
            workflow_filters['workflow_name'] = workflow_name
        if user_id:
            workflow_filters['user_id'] = user_id
        
        # Map sort fields for workflow_runs table
        workflow_sort_map = {
            'started_at': 'created_at',
            'completed_at': 'completed_at', 
            'execution_time': 'duration_seconds',
            'total_cost': 'cost_estimate'
        }
        workflow_sort_by = workflow_sort_map.get(sort_by, 'created_at')
        
        # Get workflow runs with comprehensive data
        workflow_runs, total_count = list_workflow_runs(
            filters=workflow_filters,
            page=page,
            page_size=page_size,
            order_by=workflow_sort_by,
            order_direction=sort_order.upper()
        )

        # Process workflow runs with comprehensive database data
        runs_data = []
        
        for workflow_run in workflow_runs:
            # Calculate execution time if not stored
            execution_time = workflow_run.duration_seconds
            if not execution_time and workflow_run.completed_at and workflow_run.created_at:
                delta = workflow_run.completed_at - workflow_run.created_at
                execution_time = int(delta.total_seconds())
            
            # Extract metadata for additional context
            metadata = workflow_run.metadata or {}
            tools_used = metadata.get('tools_used', [])
            
            # Get result summary from workflow_run or metadata
            result_summary = workflow_run.result
            if not result_summary and workflow_run.session_id:
                # Fallback: get latest message for session if no result stored
                try:
                    from src.db.repository import message as message_repo
                    messages = message_repo.list_messages(workflow_run.session_id)
                    assistant_messages = [msg for msg in messages if msg.role == "assistant"]
                    if assistant_messages:
                        latest = assistant_messages[-1]
                        result_text = latest.text_content or ""
                        result_summary = (
                            result_text.split(".")[0][:200] + "..."
                            if len(result_text) > 200
                            else result_text
                        )
                except Exception:
                    result_summary = None
            
            # Build comprehensive run data from workflow_runs table
            run_data = {
                "run_id": workflow_run.run_id,
                "status": workflow_run.status,
                "workflow_name": workflow_run.workflow_name,
                "started_at": workflow_run.created_at,
                "completed_at": workflow_run.completed_at,
                "execution_time": execution_time,
                "total_tokens": workflow_run.total_tokens,
                "total_cost": float(workflow_run.cost_estimate) if workflow_run.cost_estimate else None,
                "turns": metadata.get("total_turns"),
                "tool_calls": len(tools_used) if tools_used else None,
                "result": result_summary,
                # Enhanced fields from workflow_runs
                "input_tokens": workflow_run.input_tokens,
                "output_tokens": workflow_run.output_tokens,
                "ai_model": workflow_run.ai_model,
                "session_name": workflow_run.session_name,
                "git_repo": workflow_run.git_repo,
                "git_branch": workflow_run.git_branch,
                "git_diff_summary": workflow_run.get_git_diff_summary(),
                "tools_used": tools_used,
                "workspace_path": workflow_run.workspace_path,
                "workspace_persistent": workflow_run.workspace_persistent,
                "workspace_cleaned_up": workflow_run.workspace_cleaned_up,
                "error_message": workflow_run.error_message,
                "final_commit_hash": workflow_run.final_commit_hash
            }
            
            runs_data.append(run_data)

        # Convert to response models (workflow_runs already handled sorting and pagination)
        run_summaries = [
            ClaudeCodeRunSummary(**run_data) for run_data in runs_data
        ]

        return ClaudeCodeRunsListResponse(
            runs=run_summaries,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing Claude Code runs: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list runs: {str(e)}")


@claude_code_router.get("/run/{run_id}/status")
async def get_claude_code_run_status(
    run_id: str, 
    debug: bool = False,
    detailed: bool = False
):
    """
    Get enhanced status of a Claude-Code run with simplified structure.

    **Enhanced Features:**
    - Simplified response structure with meaningful data
    - Smart result extraction from workflow execution
    - Intelligent progress tracking with phase detection
    - Comprehensive token usage and cost analysis
    - Tool usage patterns and workflow insights

    **Status Values:**
    - `pending`: Run is queued but not started
    - `running`: Run is currently executing
    - `completed`: Run finished successfully
    - `failed`: Run failed with an error

    **Parameters:**
    - `debug` (optional): If true, includes detailed debug information in 12 structured sections
    - `detailed` (optional): If true, includes enhanced rich information (unified with debug)

    **Examples:**
    ```bash
    # Basic enhanced status
    GET /api/v1/workflows/claude-code/run/run_abc123/status

    # With comprehensive debug information
    GET /api/v1/workflows/claude-code/run/run_abc123/status?debug=true
    ```

    **Returns:**
    Enhanced status with progress, metrics, results, and optional debug information.
    """
    try:
        # Get workflow run data first (primary data source)
        from src.db.repository.workflow_run import get_workflow_run_by_run_id
        
        workflow_run = get_workflow_run_by_run_id(run_id)
        if not workflow_run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        
        # Find session for additional context (if available)
        target_session = None
        if workflow_run.session_id:
            try:
                from src.db import get_session
                target_session = get_session(workflow_run.session_id)
            except Exception:
                pass
        
        # Fallback: find session by run_id in metadata
        if not target_session:
            sessions = session_repo.list_sessions()
            for session in sessions:
                if session.metadata and session.metadata.get("run_id") == run_id:
                    target_session = session
                    break
        
        metadata = target_session.metadata or {} if target_session else {}

        # Try to get real-time data from SDK executor first
        sdk_status_data = None
        try:
            from src.agents.models.agent_factory import AgentFactory
            agent = AgentFactory.create_agent("claude-code", {})
            if hasattr(agent, 'executor') and hasattr(agent.executor, 'get_execution_status'):
                sdk_status_data = agent.executor.get_execution_status(run_id)
                logger.debug(f"SDK status data retrieved for {run_id}: {bool(sdk_status_data)}")
        except Exception as e:
            logger.debug(f"Could not get SDK status data: {e}")
        
        # Parse JSON stream file as fallback source (only if SDK data not available)
        stream_events = []
        stream_status = None
        stream_result = {}
        stream_metrics = {}
        stream_progress = {}
        stream_session = {}
        
        if not sdk_status_data:
            # Only try to parse legacy stream files if SDK data is not available
            try:
                # Don't warn about missing files when using SDK (they won't exist)
                stream_events = StreamParser.parse_stream_file(run_id, warn_if_missing=False)
                stream_status = StreamParser.get_current_status(stream_events)
                stream_result = StreamParser.extract_result(stream_events)
                stream_metrics = StreamParser.extract_metrics(stream_events)
                stream_progress = StreamParser.get_progress_info(stream_events, metadata.get("max_turns"))
                stream_session = StreamParser.extract_session_info(stream_events)
            except Exception as e:
                logger.debug(f"Could not parse legacy stream file for {run_id}: {e}")
                # Use empty defaults
        
        # Get messages for additional context
        from src.db.repository import message as message_repo
        messages = message_repo.list_messages(target_session.id)
        assistant_messages = [msg for msg in messages if msg.role == "assistant"]

        # Get live logs from log manager (for fallback/supplementary info)
        log_manager = get_log_manager()
        log_entries = await log_manager.get_logs(run_id, follow=False)

        # Initialize enhanced components
        result_extractor = ResultExtractor()
        progress_tracker = ProgressTracker()
        debug_builder = DebugBuilder()

        # Extract meaningful final result
        result_info = result_extractor.extract_final_result(
            log_entries, assistant_messages, metadata
        )

        # Calculate enhanced progress
        progress_info = progress_tracker.calculate_progress(
            metadata, log_entries, assistant_messages
        )

        # SURGICAL FIX: Prioritize workflow_runs database data over session metadata
        # The database now contains the accurate, final data from SDK execution persistence
        execution_results = metadata.get("execution_results", {})
        token_details = execution_results.get("token_details", {})
        
        # Primary metrics from workflow_runs table (most reliable after surgical fix)
        real_cost = workflow_run.cost_estimate if workflow_run and workflow_run.cost_estimate is not None else metadata.get("total_cost_usd", 0.0)
        real_total_tokens = workflow_run.total_tokens if workflow_run and workflow_run.total_tokens is not None else metadata.get("total_tokens", 0)
        real_input_tokens = workflow_run.input_tokens if workflow_run and workflow_run.input_tokens is not None else metadata.get("input_tokens", token_details.get("input_tokens", 0))
        real_output_tokens = workflow_run.output_tokens if workflow_run and workflow_run.output_tokens is not None else metadata.get("output_tokens", token_details.get("output_tokens", 0))
        
        # Turns and cache data still from metadata (not stored in workflow_runs yet)
        real_turns = metadata.get("total_turns", 0)
        real_cache_created = metadata.get("cache_created", token_details.get("cache_created", 0))
        real_cache_read = metadata.get("cache_read", token_details.get("cache_read", 0))
        
        # Calculate execution time from metadata if available
        execution_time_from_metadata = 0
        if execution_results.get("execution_time"):
            execution_time_from_metadata = int(execution_results.get("execution_time", 0) * 1000)  # Convert to ms
        elif metadata.get("duration_ms"):
            execution_time_from_metadata = metadata.get("duration_ms", 0)
        
        # Build comprehensive metrics using session metadata as primary source
        stream_metrics = {
            "cost_usd": real_cost,
            "total_tokens": real_total_tokens,
            "input_tokens": real_input_tokens,
            "output_tokens": real_output_tokens,
            "cache_created": real_cache_created,
            "cache_read": real_cache_read,
            "duration_ms": execution_time_from_metadata,
            "num_turns": real_turns
        }
        
        logger.info(f"Status endpoint for {run_id}: Using session metadata - "
                   f"Cost: ${real_cost:.4f}, Tokens: {real_total_tokens}, Turns: {real_turns}, "
                   f"Tools: {len(metadata.get('tools_used', []))}")

        # Calculate cache efficiency
        cache_created = stream_metrics.get("cache_created", 0)
        cache_read = stream_metrics.get("cache_read", 0)
        cache_efficiency = 0.0
        if cache_created + cache_read > 0:
            cache_efficiency = (cache_read / (cache_created + cache_read)) * 100

        # Build token info
        token_info = TokenInfo(
            total=stream_metrics.get("total_tokens", metadata.get("current_tokens", 0)),
            input=stream_metrics.get("input_tokens", 0),
            output=stream_metrics.get("output_tokens", 0),
            cache_created=cache_created,
            cache_read=cache_read,
            cache_efficiency=round(cache_efficiency, 1)
        )

        # Extract tools used from session metadata (primary source)
        tools_used = metadata.get("tools_used", metadata.get("tool_names_used", []))
        
        # Get tool usage count from metadata or calculated from tools list
        tool_calls_count = metadata.get("tool_calls", len(tools_used) if tools_used else 0)
        
        logger.debug(f"Tools used for {run_id}: {tools_used} (count: {tool_calls_count})")

        # Build metrics info using session metadata as primary source
        metrics_info = MetricsInfo(
            cost_usd=stream_metrics.get("cost_usd", 0.0),
            tokens=token_info,
            tools_used=tools_used[:10],  # Limit to first 10 tools
            api_duration_ms=stream_metrics.get("duration_ms", 0),
            performance_score=85.0 if metadata.get("success", False) else 60.0  # Simple scoring
        )

        # Build progress info - prioritize StreamParser, but detect workflow completion
        stream_completion = stream_progress.get("completion_percentage", 0)
        tracker_completion = progress_info["completion_percentage"]
        
        # If workflow is complete (success/failure), force 100% completion
        if result_info.get("success") is not None:  # Workflow has finished (success or failure)
            final_completion = 100
        elif stream_completion > 0:  # StreamParser has valid progress
            final_completion = stream_completion
        else:  # Fall back to ProgressTracker only if workflow is still running
            final_completion = tracker_completion
        
        # Determine if workflow is still running
        if result_info.get("success") is not None:  # Workflow has finished
            final_is_running = False
        else:
            final_is_running = stream_progress.get("is_running", progress_info["is_running"])
        
        # Get real turn count from metadata (primary source)
        real_turns = metadata.get("total_turns", metadata.get("current_turns", 0))
        max_turns = metadata.get("max_turns")
        
        # If no turns in metadata and we have execution_results, try to get from there
        if real_turns == 0 and execution_results:
            real_turns = execution_results.get("total_turns", 0)
        
        logger.debug(f"Turns for {run_id}: {real_turns}/{max_turns or 'unlimited'}")
        
        # Determine current phase based on progress and status
        if result_info.get("success") is not None:
            current_phase = "completed" if result_info.get("success") else "failed"
        elif final_completion > 80:
            current_phase = "finalizing"
        elif final_completion > 50:
            current_phase = "implementation"
        elif final_completion > 20:
            current_phase = "analysis"
        else:
            current_phase = "initializing"
            
        progress_info_obj = ProgressInfo(
            turns=real_turns,
            max_turns=max_turns,
            completion_percentage=final_completion,
            current_phase=current_phase,
            phases_completed=["initializing"] if final_completion > 20 else [],
            is_running=final_is_running,
            estimated_completion=progress_info["estimated_completion"]
        )

        # Calculate times and determine correct status
        started_at = target_session.created_at
        completed_at = None
        execution_time_seconds = None
        
        # Use proper status priority: session metadata > SDK > stream status
        workflow_status = metadata.get("run_status", "unknown")
        if workflow_status == "unknown" and sdk_status_data and sdk_status_data.get("status"):
            workflow_status = sdk_status_data.get("status")
        elif workflow_status == "unknown" and stream_status:
            workflow_status = stream_status
        
        # Get completion time from metadata (primary source)
        completed_at_str = metadata.get("completed_at")
        if completed_at_str:
            try:
                completed_at = datetime.fromisoformat(completed_at_str.replace("Z", "+00:00"))
                execution_time_seconds = (completed_at - started_at).total_seconds()
            except Exception as e:
                logger.debug(f"Could not parse completed_at from metadata: {e}")
        
        # Try execution_results if no direct execution time
        if execution_time_seconds is None and execution_results.get("execution_time"):
            execution_time_seconds = execution_results.get("execution_time")
        
        # Ensure status consistency with completion data
        if metadata.get("success") is not None:
            if metadata.get("success"):
                workflow_status = "completed"
            else:
                workflow_status = "failed"
        
        logger.debug(f"Status for {run_id}: {workflow_status}, execution_time: {execution_time_seconds}s")

        # Extract files created
        files_created = result_extractor.extract_files_created(log_entries)
        
        # Get git file changes if workflow is completed and we have git commits
        git_file_changes = []
        if workflow_status in ["completed", "failed"] and metadata.get("git_commits"):
            try:
                # Find the repository root (could be worktree or main repo)
                repo_path = await find_repo_root()
                if repo_path:
                    # Get file changes from the latest commit
                    git_file_changes = await get_git_file_changes(repo_path, "HEAD~1")
                    logger.debug(f"Retrieved {len(git_file_changes)} git file changes for {run_id}")
            except Exception as e:
                logger.warning(f"Could not retrieve git file changes for {run_id}: {e}")

        # Build result info
        result_info_obj = ResultInfo(
            success=result_info["success"],
            completion_type=result_info["completion_type"],
            message=result_info["message"],
            final_output=result_info["final_output"],
            files_created=files_created,
            git_commits=metadata.get("git_commits", []),
            files_changed=git_file_changes
        )

        # Build enhanced response - prioritize session metadata for completed workflows
        # For completed workflows, session metadata is the most accurate source
        if workflow_status in ["completed", "failed"] or metadata.get("success") is not None:
            # Use session metadata as primary source for completed workflows
            logger.info(f"Using session metadata for completed workflow {run_id}")
            enhanced_response = EnhancedStatusResponse(
                run_id=run_id,
                status=workflow_status,
                workflow_name=metadata.get("workflow_name", "unknown"),
                started_at=started_at,
                completed_at=completed_at,
                execution_time_seconds=execution_time_seconds,
                progress=progress_info_obj,
                metrics=metrics_info,
                result=result_info_obj
            )
        elif sdk_status_data:
            # Use SDK stream processor data for running workflows
            logger.info(f"Using real-time SDK status data for running workflow {run_id}")
            enhanced_response = EnhancedStatusResponse(
                run_id=run_id,
                status=sdk_status_data.get("status", workflow_status),
                workflow_name=sdk_status_data.get("workflow_name", metadata.get("workflow_name", "unknown")),
                started_at=datetime.fromisoformat(sdk_status_data["started_at"]) if sdk_status_data.get("started_at") else started_at,
                completed_at=datetime.fromisoformat(sdk_status_data["completed_at"]) if sdk_status_data.get("completed_at") else completed_at,
                execution_time_seconds=sdk_status_data.get("execution_time_seconds", execution_time_seconds),
                progress=ProgressInfo(**sdk_status_data["progress"]),
                metrics=MetricsInfo(**sdk_status_data["metrics"]),
                result=ResultInfo(**sdk_status_data["result"])
            )
        else:
            # Fallback to session metadata for all other cases
            logger.debug(f"Using session metadata fallback for run {run_id}")
            enhanced_response = EnhancedStatusResponse(
                run_id=run_id,
                status=workflow_status,
                workflow_name=metadata.get("workflow_name", "unknown"),
                started_at=started_at,
                completed_at=completed_at,
                execution_time_seconds=execution_time_seconds,
                progress=progress_info_obj,
                metrics=metrics_info,
                result=result_info_obj
            )

        # Add debug information if requested (unified debug/detailed behavior)
        if debug or detailed:
            debug_info = debug_builder.build_debug_response(
                metadata, log_entries, assistant_messages, stream_metrics
            )
            
            return DebugStatusResponse(
                **enhanced_response.model_dump(),
                debug=debug_info
            )
        else:
            return enhanced_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting enhanced Claude-Code run status: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get enhanced run status: {str(e)}"
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


@claude_code_router.post("/run/{run_id}/kill")
async def kill_claude_code_run(
    run_id: str = Path(..., description="Run ID to terminate"),
    force: bool = False
) -> Dict[str, Any]:
    """
    Emergency termination of a running Claude-Code workflow.
    
    **Kill Phases:**
    1. **Graceful shutdown** (5s timeout) - Send SIGTERM, allow cleanup
    2. **Forced termination** (10s timeout) - Send SIGKILL if graceful fails  
    3. **System cleanup** - Resource cleanup and audit logging
    
    **Parameters:**
    - `run_id`: The run ID to terminate
    - `force`: If true, skip graceful shutdown and kill immediately
    
    **Returns:**
    Kill confirmation with cleanup status and audit information.
    
    **Examples:**
    ```bash
    # Graceful termination (recommended)
    POST /api/v1/workflows/claude-code/run/run_abc123/kill
    
    # Force kill (emergency only)
    POST /api/v1/workflows/claude-code/run/run_abc123/kill?force=true
    ```
    """
    try:
        import time
        kill_start_time = time.time()
        
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
        workflow_name = metadata.get("workflow_name", "unknown")
        
        # Get the Claude-Code agent
        agent = AgentFactory.get_agent("claude_code")
        if not agent:
            raise HTTPException(status_code=404, detail="Claude-Code agent not available")
        
        # Perform emergency kill using the local executor
        kill_result = await agent.executor.cancel_execution(run_id)
        
        if not kill_result:
            # Try alternative kill methods if executor didn't find the process
            # Use SDK executor for consistent process management
            from src.agents.claude_code.sdk_executor import ClaudeSDKExecutor
            from src.agents.claude_code.cli_environment import CLIEnvironmentManager
            
            env_manager = CLIEnvironmentManager()
            sdk_executor = ClaudeSDKExecutor(environment_manager=env_manager)
            kill_result = await sdk_executor.cancel_execution(run_id)
        
        # Update session metadata with kill information
        kill_time = datetime.utcnow()
        kill_duration = time.time() - kill_start_time
        
        metadata.update({
            "run_status": "killed",
            "killed_at": kill_time.isoformat(),
            "kill_method": "force" if force else "graceful", 
            "kill_duration_ms": int(kill_duration * 1000),
            "kill_successful": kill_result,
            "completed_at": kill_time.isoformat()
        })
        target_session.metadata = metadata
        session_repo.update_session(target_session)
        
        # Log kill event for audit trail
        log_manager = get_log_manager()
        async with log_manager.get_log_writer(run_id) as log_writer:
            await log_writer(
                f"Emergency kill executed for workflow {workflow_name}",
                "workflow_killed",
                {
                    "run_id": run_id,
                    "workflow_name": workflow_name,
                    "kill_method": "force" if force else "graceful",
                    "kill_successful": kill_result,
                    "kill_duration_ms": int(kill_duration * 1000),
                    "killed_at": kill_time.isoformat(),
                    "kill_reason": "emergency_termination"
                }
            )
        
        return {
            "success": kill_result,
            "run_id": run_id,
            "workflow_name": workflow_name,
            "killed_at": kill_time.isoformat(),
            "kill_method": "force" if force else "graceful",
            "kill_duration_ms": int(kill_duration * 1000),
            "cleanup_status": {
                "session_updated": True,
                "audit_logged": True,
                "process_terminated": kill_result
            },
            "message": f"Workflow {workflow_name} ({'force killed' if force else 'gracefully terminated'}) in {kill_duration:.2f}s"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error killing Claude-Code run {run_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to kill run: {str(e)}"
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

        # Check if SDK executor is available
        try:
            from src.agents.claude_code.sdk_executor import ClaudeSDKExecutor
            from src.agents.claude_code.cli_environment import CLIEnvironmentManager
            
            # Test SDK executor availability
            env_manager = CLIEnvironmentManager()
            sdk_executor = ClaudeSDKExecutor(environment_manager=env_manager)
            claude_available = True
            claude_path = "SDK Executor (Post-Migration)"
        except Exception as e:
            claude_available = False
            claude_path = f"SDK Executor unavailable: {str(e)}"

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


# GUARDIAN Monitoring Endpoints


@claude_code_router.get("/monitoring/status")
async def get_workflow_monitoring_status():
    """Get GUARDIAN workflow monitoring status."""
    try:
        from src.mcp.workflow_monitor import get_workflow_monitor
        
        monitor = get_workflow_monitor()
        status = monitor.get_monitoring_status()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "monitoring": status
        }
        
    except Exception as e:
        logger.error(f"Error getting monitoring status: {e}")
        raise HTTPException(status_code=500, detail=f"Monitoring status error: {str(e)}")


@claude_code_router.get("/monitoring/health")
async def get_workflow_health_status():
    """Get health status for all running workflows."""
    try:
        from src.mcp.workflow_monitor import get_workflow_monitor
        
        monitor = get_workflow_monitor()
        health_statuses = await monitor.get_workflow_health_status()
        
        # Convert to serializable format
        health_data = []
        for health in health_statuses:
            health_data.append({
                "run_id": health.run_id,
                "workflow_name": health.workflow_name,
                "status": health.status,
                "elapsed_minutes": health.elapsed_minutes,
                "timeout_limit_minutes": health.timeout_limit_minutes,
                "warning_threshold_minutes": health.warning_threshold_minutes,
                "is_warning": health.is_warning,
                "is_timeout": health.is_timeout,
                "is_stale": health.is_stale,
                "last_heartbeat": health.last_heartbeat.isoformat() if health.last_heartbeat else None
            })
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "workflow_health": health_data,
            "total_workflows": len(health_data),
            "warning_count": len([h for h in health_data if h["is_warning"]]),
            "timeout_count": len([h for h in health_data if h["is_timeout"]]),
            "stale_count": len([h for h in health_data if h["is_stale"]])
        }
        
    except Exception as e:
        logger.error(f"Error getting workflow health: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow health error: {str(e)}")


@claude_code_router.post("/monitoring/start")
async def start_workflow_monitoring():
    """Start GUARDIAN workflow monitoring."""
    try:
        from src.mcp.workflow_monitor import get_workflow_monitor
        
        monitor = get_workflow_monitor()
        await monitor.start_monitoring()
        
        return {
            "status": "success",
            "message": "🛡️ GUARDIAN workflow monitoring started",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error starting monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Start monitoring error: {str(e)}")


@claude_code_router.post("/monitoring/stop")
async def stop_workflow_monitoring():
    """Stop GUARDIAN workflow monitoring."""
    try:
        from src.mcp.workflow_monitor import get_workflow_monitor
        
        monitor = get_workflow_monitor()
        await monitor.stop_monitoring()
        
        return {
            "status": "success",
            "message": "🛡️ GUARDIAN workflow monitoring stopped",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error stopping monitoring: {e}")
        raise HTTPException(status_code=500, detail=f"Stop monitoring error: {str(e)}")


@claude_code_router.get("/monitoring/safety-triggers")
async def get_safety_trigger_status():
    """Get safety trigger system status."""
    try:
        from src.mcp.workflow_monitor import get_workflow_monitor
        
        monitor = get_workflow_monitor()
        trigger_summary = monitor.safety_triggers.get_trigger_summary()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "safety_triggers": trigger_summary
        }
        
    except Exception as e:
        logger.error(f"Error getting safety triggers: {e}")
        raise HTTPException(status_code=500, detail=f"Safety triggers error: {str(e)}")


class WorkflowRegistrationRequest(BaseModel):
    """Request to register workflow for monitoring."""
    run_id: str = Field(..., description="Workflow run ID")
    workflow_name: str = Field(..., description="Workflow name")


@claude_code_router.post("/monitoring/register")
async def register_workflow_for_monitoring(request: WorkflowRegistrationRequest):
    """Register a workflow for GUARDIAN monitoring."""
    try:
        from src.mcp.workflow_monitor import register_workflow_for_monitoring
        
        await register_workflow_for_monitoring(request.run_id, request.workflow_name)
        
        return {
            "status": "success",
            "message": f"🛡️ GUARDIAN registered {request.workflow_name} for monitoring",
            "run_id": request.run_id,
            "workflow_name": request.workflow_name,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error registering workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Workflow registration error: {str(e)}")


class HeartbeatRequest(BaseModel):
    """Request to update workflow heartbeat."""
    run_id: str = Field(..., description="Workflow run ID")


@claude_code_router.post("/monitoring/heartbeat")
async def update_workflow_heartbeat(request: HeartbeatRequest):
    """Update heartbeat for a workflow."""
    try:
        from src.mcp.workflow_monitor import update_workflow_heartbeat
        
        await update_workflow_heartbeat(request.run_id)
        
        return {
            "status": "success",
            "message": "💓 Heartbeat updated",
            "run_id": request.run_id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error updating heartbeat: {e}")
        raise HTTPException(status_code=500, detail=f"Heartbeat update error: {str(e)}")


class EmergencyKillRequest(BaseModel):
    """Request for emergency workflow kill."""
    reason: str = Field(..., description="Reason for emergency kill")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


@claude_code_router.post("/monitoring/emergency-rollback")
async def execute_emergency_rollback(request: EmergencyKillRequest):
    """Execute emergency rollback via GUARDIAN safety triggers."""
    try:
        from src.mcp.workflow_monitor import get_workflow_monitor
        
        monitor = get_workflow_monitor()
        success = await monitor.safety_triggers.execute_emergency_rollback(
            request.reason, 
            request.context
        )
        
        return {
            "status": "success" if success else "error",
            "message": f"🚨 Emergency rollback {'completed' if success else 'failed'}",
            "reason": request.reason,
            "rollback_success": success,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error executing emergency rollback: {e}")
        raise HTTPException(status_code=500, detail=f"Emergency rollback error: {str(e)}")


@claude_code_router.get("/monitoring/timeout-configs")
async def get_timeout_configurations():
    """Get workflow timeout configurations."""
    try:
        from src.mcp.workflow_monitor import get_workflow_monitor
        
        monitor = get_workflow_monitor()
        status = monitor.get_monitoring_status()
        
        return {
            "status": "success",
            "timestamp": datetime.utcnow().isoformat(),
            "timeout_configs": status.get("timeout_configs", {}),
            "monitor_interval_seconds": status.get("monitor_interval_seconds", 60)
        }
        
    except Exception as e:
        logger.error(f"Error getting timeout configs: {e}")
        raise HTTPException(status_code=500, detail=f"Timeout config error: {str(e)}")


# Legacy endpoint compatibility
@claude_code_router.get("/guardian/status")
async def get_guardian_status():
    """Legacy endpoint for GUARDIAN status (redirects to monitoring/status)."""
    return await get_workflow_monitoring_status()
