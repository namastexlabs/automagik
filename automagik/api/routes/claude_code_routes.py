"""Claude-Code specific API routes.

This module provides specialized endpoints for the Claude-Code agent framework,
supporting workflow-based execution and async container management.
"""

import logging
import uuid
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Path, Body, Query, Depends
from pydantic import BaseModel, Field, computed_field

# Import race condition helpers
try:
    from automagik.agents.claude_code.utils.race_condition_helpers import (
        generate_unique_run_id,
        create_workflow_with_retry,
        validate_session_id
    )
except ImportError:
    # Fallback if module not available yet
    async def generate_unique_run_id(max_retries=5):
        return str(uuid.uuid4())
    async def create_workflow_with_retry(data, max_retries=3):
        from automagik.db.models import WorkflowRunCreate
        from automagik.db.repository.workflow_run import create_workflow_run
        return create_workflow_run(WorkflowRunCreate(**data))
    def validate_session_id(session_id):
        return session_id

from automagik.agents.models.agent_factory import AgentFactory
from automagik.agents.claude_code.models import (
    EnhancedStatusResponse,
    DebugStatusResponse,
    ProgressInfo,
    MetricsInfo,
    ResultInfo,
    TokenInfo
)
from automagik.db.repository import user as user_repo
from automagik.db.repository.workflow_run import get_workflow_run_by_run_id
from automagik.auth import verify_api_key

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
    input_format: Optional[str] = Field(
        None,
        description="Input format for the workflow (text or stream-json)",
        example="stream-json",
    )


class ClaudeWorkflowResponse(BaseModel):
    """Claude Code workflow response"""

    run_id: str = Field(description="Unique run identifier")
    status: str = Field(
        description="Execution status: pending, running, completed, failed, killed"
    )
    message: str = Field(description="Human-readable status message")
    session_id: str = Field(description="Session identifier")
    workflow_name: str = Field(description="The executed workflow name")
    started_at: str = Field(description="ISO timestamp when workflow started")
    
    # Git operation results (populated when workflow completes)
    auto_commit_sha: Optional[str] = Field(
        None, description="SHA of the final auto-commit (if any)"
    )




class ClaudeCodeRunSummary(BaseModel):
    """Summary of a Claude Code run for listing purposes."""

    run_id: str = Field(..., description="Unique identifier for the run")
    status: str = Field(
        ..., description="Current status: pending, running, completed, failed, killed"
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
    
    # Enhanced fields from workflow_runs
    input_tokens: Optional[int] = Field(None, description="Input tokens used")
    output_tokens: Optional[int] = Field(None, description="Output tokens used")
    ai_model: Optional[str] = Field(None, description="AI model used")
    session_name: Optional[str] = Field(None, description="Session name")
    git_repo: Optional[str] = Field(None, description="Git repository")
    git_branch: Optional[str] = Field(None, description="Git branch")
    git_diff_summary: Optional[str] = Field(None, description="Git diff summary")
    tools_used: Optional[List[str]] = Field(None, description="Tools used in the workflow")
    workspace_path: Optional[str] = Field(None, description="Workspace path")
    workspace_persistent: Optional[bool] = Field(None, description="Whether workspace is persistent")
    workspace_cleaned_up: Optional[bool] = Field(None, description="Whether workspace was cleaned up")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    final_commit_hash: Optional[str] = Field(None, description="Final git commit hash")
    
    @computed_field
    @property
    def execution_time_seconds(self) -> Optional[float]:
        """Alias for execution_time to maintain compatibility with QA tests."""
        return self.execution_time


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
    
    # New required fields for enhanced workflow metadata
    icon: str = Field(default="Bot", description="Lucide icon name for the workflow")
    mainColour: str = Field(default="#3B82F6", description="Primary color for the workflow UI")
    displayName: str = Field(default="", description="Human-friendly display name")
    category: str = Field(default="general", description="Workflow category")
    capabilities: List[str] = Field(default_factory=list, description="List of workflow capabilities")
    emoji: str = Field(default="🤖", description="Emoji representation of the workflow")
    maxTurns: Optional[int] = Field(None, description="Maximum conversation turns")
    suggestedTurns: Optional[int] = Field(None, description="Suggested conversation turns")


@claude_code_router.post(
    "/run/{workflow_name}",
    response_model=ClaudeWorkflowResponse,
    summary="Execute Claude Code Workflow",
    description="""
    Execute a Claude Code workflow with comprehensive configuration options.
    
    ## Workflow Modes:
    
    ### 1. Default Mode (Current Repository)
    Uses the Automagik agents repository as the working directory.
    ```json
    {
      "message": "Implement user authentication",
      "max_turns": 50,
      "persistent": true
    }
    ```
    
    ### 2. External Repository Mode
    Clones and works with an external Git repository.
    ```json
    {
      "message": "Add dark mode support",
      "repository_url": "https://github.com/org/project.git",
      "git_branch": "feature/dark-mode",
      "max_turns": 30,
      "persistent": false,
      "auto_merge": false
    }
    ```
    
    ### 3. Temporary Workspace Mode
    Creates an isolated, empty workspace for temporary tasks.
    ```json
    {
      "message": "Analyze this screenshot and create a summary",
      "temp_workspace": true,
      "max_turns": 10
    }
    ```
    
    ## Full Parameter List:
    - `message` (required): Task description for Claude
    - `max_turns`: Maximum conversation turns (1-200, unlimited if not specified)
    - `session_id`: Continue a previous session
    - `session_name`: Human-readable session name
    - `user_id`: User identifier for tracking
    - `timeout`: Execution timeout in seconds (60-14400)
    - `persistent`: Keep workspace after completion (default: true, ignored for temp_workspace)
    - `temp_workspace`: Use temporary isolated workspace (default: false)
    - `repository_url`: External repository to clone (incompatible with temp_workspace)
    - `git_branch`: Git branch to work on (incompatible with temp_workspace)
    - `auto_merge`: Auto-merge to main branch (incompatible with temp_workspace)
    
    ## Available Workflows:
    - **architect**: Design system architecture and technical specifications
    - **implement**: Implement features based on architectural designs  
    - **test**: Create comprehensive test suites and validation
    - **review**: Perform code review and quality assessment
    - **fix**: Apply surgical fixes for specific issues
    - **refactor**: Improve code structure and maintainability
    - **document**: Generate comprehensive documentation
    """,
)
async def run_claude_workflow(
    workflow_name: str = Path(
        ..., description="The workflow to execute", example="architect"
    ),
    request: ClaudeWorkflowRequest = Body(...),
    persistent: bool = Query(
        True, description="Keep workspace after completion (true=keep, false=delete)"
    ),
    auto_merge: bool = Query(
        False, description="Automatically merge to main branch (true=auto-merge, false=manual)"
    ),
    temp_workspace: bool = Query(
        False, description="Use temporary isolated workspace without git integration"
    ),
) -> ClaudeWorkflowResponse:
    """Execute Claude Code workflow with comprehensive configuration"""
    try:
        # Validate parameter compatibility
        if temp_workspace:
            incompatible_params = []
            if request.repository_url:
                incompatible_params.append("repository_url")
            if request.git_branch:
                incompatible_params.append("git_branch")
            if auto_merge:
                incompatible_params.append("auto_merge")
            
            if incompatible_params:
                raise HTTPException(
                    status_code=400,
                    detail=f"temp_workspace cannot be used with: {', '.join(incompatible_params)}. "
                           "Temporary workspaces are isolated environments without git integration."
                )
        
        # Validate workflow exists - check database only
        # Get available workflows from database (consistent with /manage endpoint)
        from automagik.db import list_workflows
        db_workflows = list_workflows(active_only=True)
        db_workflow_names = [w.name for w in db_workflows]
        
        # Check if workflow exists in database
        if workflow_name not in db_workflow_names:
            # For development, also check filesystem
            try:
                from pathlib import Path
                workflows_dir = Path(__file__).parent.parent.parent / "agents" / "claude_code" / "workflows"
                filesystem_workflows = []
                if workflows_dir.exists():
                    for workflow_path in workflows_dir.iterdir():
                        if workflow_path.is_dir() and (workflow_path / "prompt.md").exists():
                            filesystem_workflows.append(workflow_path.name)
                
                if workflow_name not in filesystem_workflows:
                    available = db_workflow_names + filesystem_workflows
                    raise HTTPException(
                        status_code=404,
                        detail=f"Workflow '{workflow_name}' not found. Available: {available}",
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.warning(f"Failed to check filesystem workflows: {e}")
                available = db_workflow_names
                raise HTTPException(
                    status_code=404,
                    detail=f"Workflow '{workflow_name}' not found. Available: {available}",
                )

        # Generate unique run ID with collision protection
        try:
            run_id = await generate_unique_run_id()
        except RuntimeError as e:
            logger.error(f"Failed to generate unique run ID: {e}")
            raise HTTPException(
                status_code=503,
                detail="System temporarily unable to generate unique workflow ID. Please try again."
            )

        # Handle user creation if needed
        user_id = request.user_id
        if not user_id:
            # Create anonymous user for the run
            from automagik.db.models import User

            new_user = User(
                email=f"claude-code-{run_id}@automagik-agents.ai",
                phone_number=None,
                user_data={"created_for": "claude-code-run", "run_id": run_id},
            )
            user_id = str(user_repo.create_user(new_user))

        # Session name for tracking
        session_name = request.session_name or f"claude-code-{workflow_name}-{run_id}"

        # Start execution asynchronously without waiting for first response
        # This avoids stream contamination from trying to capture early output
        try:
            # Create workflow execution parameters
            execution_params = {
                "input_text": request.message,
                "workflow_name": workflow_name,
                "session_id": request.session_id,  # Session ID from request (for continuation)
                "git_branch": request.git_branch,
                "max_turns": request.max_turns,
                "timeout": request.timeout,
                "repository_url": request.repository_url,
                "run_id": run_id,
                "persistent": persistent,
                "auto_merge": auto_merge,
                "temp_workspace": temp_workspace,
                "user_id": user_id,  # Pass user_id to agent execution
                "input_format": request.input_format,  # Add input format for stream-json support
            }
            
            # SURGICAL FIX: Create workflow run record in database BEFORE execution starts
            # This ensures the status endpoint can track the workflow immediately
            from automagik.db.models import WorkflowRunCreate
            from automagik.db.repository.workflow_run import create_workflow_run
            
            # Handle session_id properly to avoid UUID errors
            valid_session_id = None
            if request.session_id:
                try:
                    # Validate it's a proper UUID format
                    uuid.UUID(request.session_id)
                    valid_session_id = request.session_id
                except (ValueError, TypeError):
                    logger.warning(f"Invalid session_id format: {request.session_id}, ignoring")
            
            workflow_run_data = WorkflowRunCreate(
                run_id=run_id,
                workflow_name=workflow_name,
                agent_type="claude_code",
                ai_model=request.model if hasattr(request, 'model') else "sonnet",
                task_input=request.message,
                session_id=valid_session_id,  # Use validated session ID
                session_name=session_name,
                git_repo=request.repository_url,
                git_branch=request.git_branch,
                status="pending",
                workspace_persistent=persistent,
                temp_workspace=temp_workspace,  # Include temp_workspace flag
                user_id=user_id,
                metadata={
                    "max_turns": request.max_turns,
                    "timeout": request.timeout,
                    "created_at": datetime.utcnow().isoformat(),
                    "request": request.dict()
                }
            )
            
            try:
                workflow_run_id = create_workflow_run(workflow_run_data)
                logger.info(f"Created workflow run record {workflow_run_id} for run_id {run_id}")
            except ValueError as ve:
                # Handle race condition where another process created the workflow
                if "already exists" in str(ve):
                    logger.warning(f"Workflow run {run_id} already exists (race condition), checking status")
                    existing = get_workflow_run_by_run_id(run_id)
                    if existing and existing.status in ["pending", "running"]:
                        # Return the existing workflow info
                        return ClaudeWorkflowResponse(
                            run_id=run_id,
                            status=existing.status,
                            message=f"Workflow {workflow_name} is already {existing.status}. Use the status endpoint to track progress.",
                            session_id=existing.session_id or str(uuid.uuid4()),
                            workflow_name=workflow_name,
                            started_at=existing.created_at.isoformat() if existing.created_at else datetime.utcnow().isoformat(),
                        )
                    else:
                        # Workflow exists but in a terminal state, generate new ID
                        logger.warning(f"Existing workflow {run_id} is in state {existing.status}, generating new ID")
                        run_id = str(uuid.uuid4())
                        workflow_run_data.run_id = run_id
                        workflow_run_id = create_workflow_run(workflow_run_data)
                else:
                    raise
            except Exception as db_error:
                logger.warning(f"Failed to create workflow run record: {db_error}")
                # Continue anyway - not critical for execution
            
            # Double-check no duplicate workflows after database creation
            # This is redundant but ensures absolute safety
            existing_workflow = get_workflow_run_by_run_id(run_id)
            if not existing_workflow:
                logger.error(f"Failed to find workflow run {run_id} after creation")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to initialize workflow run {run_id}"
                )
            
            # SURGICAL FIX: Use proper background task with asyncio instead of raw threading
            # This ensures proper lifecycle management and error handling
            async def execute_workflow_with_isolation():
                """Execute workflow with proper isolation and error handling."""
                try:
                    # Set isolation flag
                    import os
                    os.environ['BYPASS_TASKGROUP_DETECTION'] = 'true'
                    
                    # Update status to running
                    from automagik.db.models import WorkflowRunUpdate
                    from automagik.db.repository.workflow_run import update_workflow_run_by_run_id
                    
                    update_data = WorkflowRunUpdate(
                        status="running",
                        updated_at=datetime.utcnow()
                    )
                    update_workflow_run_by_run_id(run_id, update_data)
                    
                    # Execute workflow directly using SDK executor
                    # Bypass agent factory to avoid initialization issues
                    from automagik.agents.claude_code.sdk_executor import ClaudeSDKExecutor
                    from automagik.agents.claude_code.cli_environment import CLIEnvironmentManager
                    from automagik.agents.claude_code.models import ClaudeCodeRunRequest
                    
                    env_manager = CLIEnvironmentManager()
                    sdk_executor = ClaudeSDKExecutor(environment_manager=env_manager)
                    
                    # Create proper request object
                    sdk_request = ClaudeCodeRunRequest(
                        message=execution_params.get("input_text"),
                        workflow_name=execution_params.get("workflow_name"),
                        session_id=execution_params.get("session_id"),
                        run_id=execution_params.get("run_id"),
                        max_turns=execution_params.get("max_turns"),
                        timeout=execution_params.get("timeout"),
                        repository_url=execution_params.get("repository_url"),
                        git_branch=execution_params.get("git_branch"),
                        persistent=execution_params.get("persistent"),
                        temp_workspace=execution_params.get("temp_workspace"),
                        input_format=execution_params.get("input_format", "text"),
                        model="sonnet"  # default model
                    )
                    
                    # Create agent context
                    agent_context = {
                        "user_id": execution_params.get("user_id"),
                        "run_id": execution_params.get("run_id"),
                        "session_name": execution_params.get("session_name", f"claude-code-{workflow_name}-{run_id}")
                    }
                    
                    # Execute workflow through SDK executor
                    result = await sdk_executor.execute_claude_task(
                        request=sdk_request,
                        agent_context=agent_context
                    )
                    
                    logger.info(f"Workflow {run_id} completed via direct SDK execution")
                    
                except Exception as e:
                    logger.error(f"Workflow execution failed for {run_id}: {e}")
                    # Update database with failure
                    try:
                        update_data = WorkflowRunUpdate(
                            status="failed",
                            error_message=str(e),
                            completed_at=datetime.utcnow(),
                            updated_at=datetime.utcnow()
                        )
                        update_workflow_run_by_run_id(run_id, update_data)
                    except Exception:
                        pass
                finally:
                    # Cleanup
                    os.environ.pop('BYPASS_TASKGROUP_DETECTION', None)
                    
                    # Remove task from active_tasks when done
                    try:
                        cleanup_agent = AgentFactory.get_agent("claude_code")
                        if cleanup_agent and hasattr(cleanup_agent, 'executor') and hasattr(cleanup_agent.executor, 'active_tasks'):
                            if run_id in cleanup_agent.executor.active_tasks:
                                del cleanup_agent.executor.active_tasks[run_id]
                                logger.info(f"Cleaned up task for run_id {run_id}")
                    except Exception as cleanup_error:
                        logger.warning(f"Failed to cleanup task for {run_id}: {cleanup_error}")
            
            # Create background task and store it for cancellation
            task = asyncio.create_task(execute_workflow_with_isolation())
            
            # Store task in agent for cancellation capabilities
            try:
                agent = AgentFactory.get_agent("claude_code")
            except Exception as agent_error:
                logger.warning(f"Could not get agent for task storage: {agent_error}")
                agent = None
            if agent and hasattr(agent, 'executor'):
                if not hasattr(agent.executor, 'active_tasks'):
                    agent.executor.active_tasks = {}
                
                # Check if task already exists for this run_id
                if run_id in agent.executor.active_tasks:
                    existing_task = agent.executor.active_tasks[run_id]
                    if not existing_task.done():
                        logger.warning(f"Task for run_id {run_id} already exists and is running")
                        task.cancel()  # Cancel the new task
                        raise HTTPException(
                            status_code=409,
                            detail=f"Task for run_id {run_id} is already running"
                        )
                
                agent.executor.active_tasks[run_id] = task
                logger.info(f"Stored task for run_id {run_id} for cancellation support")
            
            # Return immediately with pending status
            result = {
                "run_id": run_id,
                "status": "pending",
                "message": f"Started {workflow_name} workflow. Use the status endpoint to track progress.",
                "started_at": datetime.utcnow().isoformat(),
                "session_id": request.session_id or str(uuid.uuid4()),  # Session ID for continuation
                "git_branch": request.git_branch,
            }
            
        except Exception as exec_error:
            logger.error(f"Execution error in workflow {workflow_name}: {exec_error}")
            result = {
                "run_id": run_id,
                "status": "failed",
                "message": f"Failed to start {workflow_name} workflow: {str(exec_error)}",
                "started_at": datetime.utcnow().isoformat(),
                "session_id": request.session_id or str(uuid.uuid4()),
            }

            

        # Return response with actual Claude message
        return ClaudeWorkflowResponse(
            run_id=result.get("run_id", run_id),
            status=result.get("status", "failed"),
            message=result.get("message", f"Failed to start {workflow_name} workflow"),
            session_id=result.get("session_id") or request.session_id or str(uuid.uuid4()),
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
        from automagik.db.repository.workflow_run import list_workflow_runs
        
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
            
            # Get result summary from workflow_run
            result_summary = workflow_run.result
            if not result_summary:
                # Generate summary from task_input if no result stored
                task_input = workflow_run.task_input or ""
                if task_input:
                    result_summary = f"Processing: {task_input[:100]}..." if len(task_input) > 100 else f"Processing: {task_input}"
                else:
                    result_summary = f"Workflow {workflow_run.status}"
            
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
async def get_claude_code_run_status(run_id: str, debug: bool = False):
    """Get workflow status reading exclusively from workflow_runs table."""
    try:
        from automagik.db.repository.workflow_run import get_workflow_run_by_run_id
        
        workflow_run = get_workflow_run_by_run_id(run_id)
        if not workflow_run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        
        metadata = {}
        if workflow_run.metadata:
            try:
                metadata = json.loads(workflow_run.metadata) if isinstance(workflow_run.metadata, str) else workflow_run.metadata
            except (json.JSONDecodeError, TypeError):
                metadata = {}
        
        max_turns = metadata.get("max_turns")
        turns = metadata.get("total_turns", 0)
        
        response = EnhancedStatusResponse(
            run_id=run_id,
            status=workflow_run.status,
            workflow_name=workflow_run.workflow_name,
            started_at=workflow_run.created_at,
            completed_at=workflow_run.completed_at,
            execution_time_seconds=workflow_run.duration_seconds,
            progress=ProgressInfo(
                turns=turns,
                max_turns=max_turns,
                current_phase="completed" if workflow_run.status == "completed" else "running",
                phases_completed=[],
                is_running=workflow_run.status == "running"
            ),
            metrics=MetricsInfo(
                cost_usd=float(workflow_run.cost_estimate) if workflow_run.cost_estimate else 0.0,
                tokens=TokenInfo(
                    total=workflow_run.total_tokens or 0,
                    input=workflow_run.input_tokens or 0,
                    output=workflow_run.output_tokens or 0,
                    cache_created=0,
                    cache_read=0,
                    cache_efficiency=0.0
                ),
                tools_used=metadata.get("tools_used", []),
                api_duration_ms=0,
                performance_score=85.0 if workflow_run.status == "completed" else 60.0
            ),
            result=ResultInfo(
                success=workflow_run.status == "completed",
                completion_type=workflow_run.status,
                message=workflow_run.result or f"Workflow {workflow_run.status}",
                final_output=workflow_run.result,
                files_created=[],
                git_commits=[],
                files_changed=[]
            )
        )
        
        if debug:
            return DebugStatusResponse(
                **response.model_dump(),
                debug={"workflow_run_id": str(workflow_run.id), "metadata": metadata}
            )
        
        return response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting workflow status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")



@claude_code_router.get("/manage", response_model=List[WorkflowInfo])
async def list_claude_code_workflows() -> List[WorkflowInfo]:
    """
    List all available Claude-Code workflows with enhanced metadata.

    **Returns:**
    List of available workflows with their descriptions, validation status, and UI metadata.

    **Example:**
    ```bash
    GET /api/v1/workflows/claude-code/manage
    ```
    """
    try:
        # Get workflows from database
        from automagik.db import list_workflows
        
        # Get all workflows (both system and custom)
        db_workflows = list_workflows(active_only=True)
        
        # Convert to response format with enhanced metadata
        workflow_list = []
        
        for workflow in db_workflows:
            # Get metadata from config field (stored as JSON in database)
            config = workflow.config or {}
            
            # Build workflow info with all required fields
            workflow_list.append(
                WorkflowInfo(
                    name=workflow.name,
                    description=workflow.description or config.get("description", "No description available"),
                    path=f"/workflows/{workflow.name}",
                    valid=True,  # Database workflows are assumed valid
                    # Enhanced metadata fields from config
                    icon=config.get("icon", "Bot"),
                    mainColour=config.get("mainColour", "#3B82F6"),
                    displayName=config.get("display_name") or workflow.display_name or workflow.name.title(),
                    category=workflow.category or config.get("category", "general"),
                    capabilities=config.get("capabilities", []),
                    emoji=config.get("emoji", "🤖"),
                    maxTurns=config.get("maxTurns"),
                    suggestedTurns=config.get("suggestedTurns", 50)
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
        
        # Find workflow run by run_id
        from automagik.db.repository.workflow_run import get_workflow_run_by_run_id
        
        workflow_run = get_workflow_run_by_run_id(run_id)
        if not workflow_run:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        
        workflow_name = workflow_run.workflow_name
        
        # Get the Claude-Code agent
        agent = AgentFactory.get_agent("claude_code")
        if not agent:
            raise HTTPException(status_code=404, detail="Claude-Code agent not available")
        
        # Perform emergency kill using the local executor
        kill_result = await agent.executor.cancel_execution(run_id)
        
        if not kill_result:
            # Try alternative kill methods if executor didn't find the process
            # Use SDK executor for consistent process management
            from automagik.agents.claude_code.sdk_executor import ClaudeSDKExecutor
            from automagik.agents.claude_code.cli_environment import CLIEnvironmentManager
            
            env_manager = CLIEnvironmentManager()
            sdk_executor = ClaudeSDKExecutor(environment_manager=env_manager)
            kill_result = await sdk_executor.cancel_execution(run_id)
        
        # Update workflow run with kill information
        kill_time = datetime.utcnow()
        kill_duration = time.time() - kill_start_time
        
        from automagik.db.models import WorkflowRunUpdate
        from automagik.db.repository.workflow_run import update_workflow_run_by_run_id
        
        kill_metadata = workflow_run.metadata or {}
        kill_metadata.update({
            "kill_method": "force" if force else "graceful", 
            "kill_duration_ms": int(kill_duration * 1000),
            "kill_successful": kill_result,
            "killed_at": kill_time.isoformat()
        })
        
        update_data = WorkflowRunUpdate(
            status="killed",
            error_message=f"Workflow {'force killed' if force else 'gracefully terminated'}",
            completed_at=kill_time,
            metadata=kill_metadata
        )
        update_workflow_run_by_run_id(run_id, update_data)
        
        # Log kill event for audit trail
        from automagik.agents.claude_code.log_manager import get_log_manager
        try:
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
        except Exception as log_error:
            logger.warning(f"Failed to log kill event: {log_error}")
        
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


@claude_code_router.post("/run/{run_id}/cleanup")
async def cleanup_claude_code_workspace(
    run_id: str,
    force: bool = Query(False, description="Force cleanup even if workflow is still running"),
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Clean up workspace and resources for a completed Claude-Code workflow.
    
    **Purpose:**
    Removes workspace directories, temporary files, and resources created during workflow execution.
    
    **Parameters:**
    - `run_id`: Unique identifier for the workflow run
    - `force`: If true, cleanup workspace even if workflow is still running (use with caution)
    
    **Returns:**
    Cleanup status and details about what was removed.
    
    **Example:**
    ```bash
    # Normal cleanup after completion
    POST /api/v1/workflows/claude-code/run/run_abc123/cleanup
    
    # Force cleanup (emergency)
    POST /api/v1/workflows/claude-code/run/run_abc123/cleanup?force=true
    ```
    """
    try:
        cleanup_start_time = time.time()
        
        # Get workflow run details
        workflow_run = get_workflow_run_by_run_id(run_id)
        if not workflow_run:
            raise HTTPException(
                status_code=404, detail=f"Workflow run not found: {run_id}"
            )
        
        workflow_name = workflow_run.workflow_name
        
        # Check if workflow is still running (unless force cleanup)
        if not force and workflow_run.status in ["pending", "running"]:
            raise HTTPException(
                status_code=400, 
                detail=f"Workflow is still {workflow_run.status}. Use force=true to cleanup anyway."
            )
        
        # Initialize cleanup result
        cleanup_result = {
            "workspace_removed": False,
            "temp_files_removed": False,
            "git_worktree_removed": False,
            "process_cleaned": False,
            "workspace_path": None,
            "errors": []
        }
        
        # Get workspace information from environment manager
        try:
            from automagik.agents.claude_code.cli_environment import CLIEnvironmentManager
            env_manager = CLIEnvironmentManager()
            
            # Try to find workspace based on run_id
            from automagik.utils.project import get_project_root, resolve_workspace_from_run_id
            
            project_root = get_project_root()
            workspace_candidates = resolve_workspace_from_run_id(run_id)
            
            # Clean up found workspaces
            for workspace_path in workspace_candidates:
                try:
                    if workspace_path.exists():
                        cleanup_result["workspace_path"] = str(workspace_path)
                        
                        # If it's a git worktree, remove it properly
                        if (workspace_path.parent.name == "worktrees" and 
                            (workspace_path / ".git").exists()):
                            
                            # Remove git worktree
                            import subprocess
                            try:
                                subprocess.run([
                                    "git", "worktree", "remove", "--force", str(workspace_path)
                                ], cwd=str(project_root), check=True, 
                                capture_output=True)
                                cleanup_result["git_worktree_removed"] = True
                            except subprocess.CalledProcessError:
                                # Fallback to regular directory removal
                                import shutil
                                shutil.rmtree(workspace_path)
                                cleanup_result["workspace_removed"] = True
                        else:
                            # Regular directory cleanup
                            import shutil
                            shutil.rmtree(workspace_path)
                            cleanup_result["workspace_removed"] = True
                            
                        logger.info(f"Cleaned up workspace: {workspace_path}")
                        
                except Exception as e:
                    error_msg = f"Failed to remove workspace {workspace_path}: {str(e)}"
                    cleanup_result["errors"].append(error_msg)
                    logger.warning(error_msg)
            
            # Clean up any orphaned processes
            try:
                agent = AgentFactory.get_agent("claude_code")
                if agent and hasattr(agent, 'executor'):
                    process_manager = getattr(agent.executor, 'process_manager', None)
                    if process_manager and hasattr(process_manager, 'cleanup_process'):
                        cleanup_success = process_manager.cleanup_process(run_id)
                        cleanup_result["process_cleaned"] = cleanup_success
            except Exception as e:
                error_msg = f"Failed to cleanup processes: {str(e)}"
                cleanup_result["errors"].append(error_msg)
        
        except Exception as e:
            error_msg = f"Workspace cleanup failed: {str(e)}"
            cleanup_result["errors"].append(error_msg)
            logger.error(error_msg)
        
        # Update workflow run with cleanup status
        cleanup_time = datetime.utcnow()
        cleanup_duration = time.time() - cleanup_start_time
        
        try:
            from automagik.db.models import WorkflowRunUpdate
            from automagik.db.repository.workflow_run import update_workflow_run_by_run_id
            update_data = WorkflowRunUpdate(
                workspace_cleaned_up=True,
                metadata={
                    **(workflow_run.metadata or {}),
                    "cleanup_performed_at": cleanup_time.isoformat(),
                    "cleanup_duration_ms": int(cleanup_duration * 1000),
                    "cleanup_result": cleanup_result
                }
            )
            update_workflow_run_by_run_id(run_id, update_data)
        except Exception as e:
            logger.warning(f"Failed to update workflow run with cleanup status: {e}")
        
        # Determine overall success
        overall_success = (
            (cleanup_result["workspace_removed"] or cleanup_result["git_worktree_removed"]) and
            len(cleanup_result["errors"]) == 0
        )
        
        return {
            "success": overall_success,
            "run_id": run_id,
            "workflow_name": workflow_name,
            "cleanup_time": cleanup_time.isoformat(),
            "cleanup_duration_ms": int(cleanup_duration * 1000),
            "cleanup_details": cleanup_result,
            "message": f"Workspace cleanup {'completed successfully' if overall_success else 'completed with errors'} in {cleanup_duration:.2f}s"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cleaning up workspace for run {run_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to cleanup workspace: {str(e)}"
        )


@claude_code_router.post("/run/{run_id}/add-message")
async def add_message_to_workflow(
    run_id: str,
    message_type: str = Body(..., description="Message type: 'user' or 'system'"),
    content: str = Body(..., description="Message content"),
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Add a message to a running workflow's queue for injection.
    
    Messages are queued and will be injected in batch when the workflow
    is ready to process them (all queued messages are sent together).
    
    **Parameters:**
    - `run_id`: The workflow run ID
    - `message_type`: Type of message ('user' or 'system')
    - `content`: Message content to add
    
    **Returns:**
    Queue status including current queue size
    
    **Example:**
    ```
    POST /api/v1/workflows/claude-code/run/run_abc123/add-message
    {
        "message_type": "user",
        "content": "Add error handling to the authentication function"
    }
    ```
    """
    try:
        # Validate message type
        if message_type not in ["user", "system"]:
            raise HTTPException(
                status_code=400,
                detail="message_type must be 'user' or 'system'"
            )
        
        # Validate content
        if not content or not content.strip():
            raise HTTPException(
                status_code=400,
                detail="content cannot be empty"
            )
        
        # Check if workflow exists and is running
        workflow_run = get_workflow_run_by_run_id(run_id)
        if not workflow_run:
            raise HTTPException(
                status_code=404,
                detail=f"Workflow run {run_id} not found"
            )
        
        if workflow_run.status not in ["pending", "running"]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot add messages to workflow in {workflow_run.status} state"
            )
        
        # Add message to queue
        from automagik.agents.claude_code.message_queue import message_queue_manager
        
        queue_size = message_queue_manager.add_message(
            run_id=run_id,
            message_type=message_type,
            content=content.strip(),
            metadata={
                "api_key": str(api_key)[:8] + "..." if api_key else "unknown",  # Log partial key for audit
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Added {message_type} message to workflow {run_id}. Queue size: {queue_size}")
        
        # Get queue stats
        stats = message_queue_manager.get_queue_stats(run_id)
        
        return {
            "success": True,
            "message": f"Message added to queue",
            "queue_size": queue_size,
            "run_id": run_id,
            "queue_stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding message to workflow {run_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add message: {str(e)}"
        )


@claude_code_router.get("/run/{run_id}/message-queue")
async def get_message_queue_status(
    run_id: str,
    api_key: str = Depends(verify_api_key)
) -> Dict[str, Any]:
    """
    Get the current message queue status for a workflow.
    
    **Parameters:**
    - `run_id`: The workflow run ID
    
    **Returns:**
    Queue statistics including size and message details
    """
    try:
        from automagik.agents.claude_code.message_queue import message_queue_manager
        
        stats = message_queue_manager.get_queue_stats(run_id)
        if not stats:
            raise HTTPException(
                status_code=404,
                detail=f"No message queue found for workflow {run_id}"
            )
        
        return {
            "success": True,
            "run_id": run_id,
            "queue_stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting queue status for {run_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get queue status: {str(e)}"
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
            from automagik.agents.claude_code.sdk_executor import ClaudeSDKExecutor
            from automagik.agents.claude_code.cli_environment import CLIEnvironmentManager
            
            # Test SDK executor availability
            env_manager = CLIEnvironmentManager()
            ClaudeSDKExecutor(environment_manager=env_manager)  # Test instantiation
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

                # Check workflows (consistent with /manage and /run endpoints)
                from automagik.db import list_workflows
                db_workflows = list_workflows(active_only=True)
                health_status["workflows"] = {
                    w.name: True for w in db_workflows  # DB workflows are considered valid
                }
                
                # Also include filesystem-only workflows for development visibility
                fs_workflows = await agent.get_available_workflows()
                for name, info in fs_workflows.items():
                    if name not in health_status["workflows"]:
                        health_status["workflows"][name] = info.get("valid", False)

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


# Simple Workflow Management Endpoints (following agent pattern)
class WorkflowManageRequest(BaseModel):
    """Request model for workflow management operations."""
    name: str = Field(..., description="Workflow name")
    display_name: Optional[str] = Field(None, description="Human-readable display name")
    description: Optional[str] = Field(None, description="Workflow description")
    category: str = Field(default="custom", description="Workflow category")
    prompt_template: str = Field(..., description="Main workflow prompt template")
    allowed_tools: List[str] = Field(default_factory=list, description="List of allowed tool names")
    mcp_config: Dict[str, Any] = Field(default_factory=dict, description="MCP server configuration")
    active: bool = Field(default=True, description="Whether workflow is active")
    
    # Enhanced metadata fields
    icon: Optional[str] = Field(default="Bot", description="Lucide icon name")
    mainColour: Optional[str] = Field(default="#3B82F6", description="Primary color hex code")
    emoji: Optional[str] = Field(default="🤖", description="Emoji representation")
    capabilities: Optional[List[str]] = Field(default_factory=list, description="List of capabilities")
    maxTurns: Optional[int] = Field(None, description="Maximum conversation turns")
    suggestedTurns: Optional[int] = Field(default=50, description="Suggested conversation turns")
    config: Dict[str, Any] = Field(default_factory=dict, description="Additional configuration")


class WorkflowManageResponse(BaseModel):
    """Response model for workflow management operations."""
    success: bool = Field(..., description="Whether operation succeeded")
    message: str = Field(..., description="Response message")
    workflow: Optional[Dict[str, Any]] = Field(None, description="Workflow data")


@claude_code_router.post("/manage", response_model=WorkflowManageResponse)
async def create_workflow(request: WorkflowManageRequest) -> WorkflowManageResponse:
    """
    Create a new custom workflow.
    
    **Example:**
    ```bash
    POST /api/v1/workflows/claude-code/manage
    {
        "name": "my-custom-workflow",
        "display_name": "My Custom Workflow",
        "description": "A custom workflow for my specific needs",
        "category": "custom",
        "prompt_template": "You are a custom workflow agent...",
        "allowed_tools": ["git", "sqlite"],
        "mcp_config": {},
        "active": true
    }
    ```
    """
    try:
        from automagik.db import create_workflow, WorkflowCreate
        
        # No category validation - allow any category
        
        # Prepare enhanced config with metadata
        enhanced_config = request.config.copy()
        enhanced_config.update({
            "icon": request.icon,
            "mainColour": request.mainColour,
            "emoji": request.emoji,
            "capabilities": request.capabilities,
            "maxTurns": request.maxTurns,
            "suggestedTurns": request.suggestedTurns
        })
        
        # Create workflow
        workflow_create = WorkflowCreate(
            name=request.name,
            display_name=request.display_name,
            description=request.description,
            category=request.category,
            prompt_template=request.prompt_template,
            allowed_tools=request.allowed_tools,
            mcp_config=request.mcp_config,
            active=request.active,
            is_system_workflow=False,  # Custom workflows are never system workflows
            config=enhanced_config
        )
        
        workflow_id = create_workflow(workflow_create)
        
        if workflow_id:
            # Get the created workflow
            from automagik.db import get_workflow
            workflow = get_workflow(workflow_id)
            
            # Include enhanced metadata in response
            config = workflow.config or {}
            return WorkflowManageResponse(
                success=True,
                message=f"Workflow '{request.name}' created successfully",
                workflow={
                    "id": workflow.id,
                    "name": workflow.name,
                    "display_name": workflow.display_name,
                    "description": workflow.description,
                    "category": workflow.category,
                    "active": workflow.active,
                    "is_system_workflow": workflow.is_system_workflow,
                    "created_at": workflow.created_at.isoformat() if hasattr(workflow.created_at, 'isoformat') else str(workflow.created_at),
                    # Enhanced metadata
                    "icon": config.get("icon", "Bot"),
                    "mainColour": config.get("mainColour", "#3B82F6"),
                    "emoji": config.get("emoji", "🤖"),
                    "capabilities": config.get("capabilities", []),
                    "maxTurns": config.get("maxTurns"),
                    "suggestedTurns": config.get("suggestedTurns", 50)
                }
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to create workflow")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@claude_code_router.put("/manage", response_model=WorkflowManageResponse)
async def update_workflow(request: WorkflowManageRequest) -> WorkflowManageResponse:
    """
    Update an existing custom workflow.
    
    **Example:**
    ```bash
    PUT /api/v1/workflows/claude-code/manage
    {
        "name": "my-custom-workflow",
        "display_name": "Updated Custom Workflow",
        "description": "Updated description",
        "prompt_template": "Updated prompt...",
        "allowed_tools": ["git", "sqlite", "linear"]
    }
    ```
    """
    try:
        from automagik.db import get_workflow_by_name, update_workflow, WorkflowUpdate
        
        # Check if workflow exists
        existing_workflow = get_workflow_by_name(request.name)
        if not existing_workflow:
            raise HTTPException(status_code=404, detail=f"Workflow '{request.name}' not found")
        
        # Prevent updating system workflows
        if existing_workflow.is_system_workflow:
            raise HTTPException(status_code=400, detail="Cannot update system workflows")
        
        # No category validation - allow any category
        
        # Prepare enhanced config with metadata
        enhanced_config = request.config.copy()
        enhanced_config.update({
            "icon": request.icon,
            "mainColour": request.mainColour,
            "emoji": request.emoji,
            "capabilities": request.capabilities,
            "maxTurns": request.maxTurns,
            "suggestedTurns": request.suggestedTurns
        })
        
        # Update workflow
        workflow_update = WorkflowUpdate(
            display_name=request.display_name,
            description=request.description,
            category=request.category,
            prompt_template=request.prompt_template,
            allowed_tools=request.allowed_tools,
            mcp_config=request.mcp_config,
            active=request.active,
            config=enhanced_config
        )
        
        success = update_workflow(existing_workflow.id, workflow_update)
        
        if success:
            # Get the updated workflow
            from automagik.db import get_workflow
            workflow = get_workflow(existing_workflow.id)
            
            # Include enhanced metadata in response
            config = workflow.config or {}
            return WorkflowManageResponse(
                success=True,
                message=f"Workflow '{request.name}' updated successfully",
                workflow={
                    "id": workflow.id,
                    "name": workflow.name,
                    "display_name": workflow.display_name,
                    "description": workflow.description,
                    "category": workflow.category,
                    "active": workflow.active,
                    "is_system_workflow": workflow.is_system_workflow,
                    "updated_at": workflow.updated_at.isoformat() if hasattr(workflow.updated_at, 'isoformat') else str(workflow.updated_at),
                    # Enhanced metadata
                    "icon": config.get("icon", "Bot"),
                    "mainColour": config.get("mainColour", "#3B82F6"),
                    "emoji": config.get("emoji", "🤖"),
                    "capabilities": config.get("capabilities", []),
                    "maxTurns": config.get("maxTurns"),
                    "suggestedTurns": config.get("suggestedTurns", 50)
                }
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to update workflow")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workflow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@claude_code_router.delete("/manage")
async def delete_workflow(name: str = Query(..., description="Workflow name to delete")) -> WorkflowManageResponse:
    """
    Delete a custom workflow.
    
    **Example:**
    ```bash
    DELETE /api/v1/workflows/claude-code/manage?name=my-custom-workflow
    ```
    """
    try:
        from automagik.db import get_workflow_by_name, delete_workflow
        
        # Check if workflow exists
        workflow = get_workflow_by_name(name)
        if not workflow:
            raise HTTPException(status_code=404, detail=f"Workflow '{name}' not found")
        
        # Prevent deleting system workflows
        if workflow.is_system_workflow:
            raise HTTPException(status_code=400, detail="Cannot delete system workflows")
        
        # Delete workflow
        success = delete_workflow(workflow.id)
        
        if success:
            return WorkflowManageResponse(
                success=True,
                message=f"Workflow '{name}' deleted successfully"
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to delete workflow")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting workflow: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
