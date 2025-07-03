"""Data models for Claude-Code agent.

This module defines Pydantic models for request/response handling,
configuration validation, and local execution management.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator, ConfigDict
from uuid import UUID, uuid4

class ClaudeCodeRunRequest(BaseModel):
    """Request model for Claude CLI execution."""
    
    message: str = Field(..., description="The task message for Claude to execute")
    session_id: Optional[str] = Field(None, description="Optional session ID for continuity")
    run_id: Optional[str] = Field(None, description="Unique run identifier for database tracking and persistence")
    workflow_name: str = Field("surgeon", description="Name of the workflow to execute")
    max_turns: Optional[int] = Field(None, ge=1, le=200, description="Maximum number of Claude turns (optional, unlimited if not specified)")
    git_branch: Optional[str] = Field(
        None, 
        description="Git branch to work on (defaults to current branch)"
    )
    model: Optional[str] = Field(
        default="sonnet",
        description="Claude model to use"
    )
    max_thinking_tokens: Optional[int] = Field(
        None,
        description="Maximum thinking tokens for reasoning"
    )
    timeout: Optional[int] = Field(
        default=3600, 
        ge=60, 
        le=7200, 
        description="Execution timeout in seconds (1 hour to 2 hours)"
    )
    environment: Optional[Dict[str, str]] = Field(
        default_factory=dict,
        description="Additional environment variables for execution"
    )
    repository_url: Optional[str] = Field(
        None,
        description="Git repository URL to clone (defaults to current repository if not specified)"
    )
    persistent: bool = Field(
        default=True,
        description="Keep workspace after completion (true=keep, false=delete)"
    )
    auto_merge: bool = Field(
        default=False,
        description="Automatically merge to main branch (true=auto-merge, false=manual)"
    )
    temp_workspace: bool = Field(
        default=False,
        description="Use temporary isolated workspace without git integration"
    )
    
    @validator('message')
    def message_not_empty(cls, v):
        """Validate that message is not empty."""
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()
    
    @validator('workflow_name')
    def workflow_name_valid(cls, v):
        """Validate workflow name format."""
        if not v or not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Workflow name must be alphanumeric with dashes or underscores')
        return v
    
    @validator('temp_workspace')
    def validate_temp_workspace_compatibility(cls, v, values):
        """Validate temp_workspace compatibility with other parameters."""
        if v:  # If temp_workspace is True
            incompatible = []
            if values.get('repository_url'):
                incompatible.append('repository_url')
            if values.get('git_branch'):
                incompatible.append('git_branch')
            if values.get('auto_merge'):
                incompatible.append('auto_merge')
            
            if incompatible:
                raise ValueError(
                    f"temp_workspace cannot be used with: {', '.join(incompatible)}. "
                    "Temporary workspaces are isolated environments without git integration."
                )
        return v
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Fix the session timeout issue in agent controller",
                "session_id": "session_abc123",
                "workflow_name": "surgeon",
                "max_turns": 50,
                "git_branch": "fix/session-timeout",
                "model": "sonnet",
                "timeout": 3600,
                "environment": {
                    "CUSTOM_VAR": "value"
                },
                "repository_url": "https://github.com/myorg/myrepo.git"
            }
        }
    )

class ClaudeCodeRunResponse(BaseModel):
    """Response model for async Claude CLI execution start."""
    
    run_id: str = Field(..., description="Unique identifier for this execution run")
    status: Literal["pending", "running", "completed", "failed", "killed"] = Field(
        ..., 
        description="Current status of the execution"
    )
    message: str = Field(default="Local execution initiated", description="Status message")
    session_id: str = Field(..., description="Session identifier")
    started_at: datetime = Field(..., description="When the execution was started")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "run_id": "run_abc123def456",
                "status": "pending",
                "message": "Container deployment initiated",
                "session_id": "session_xyz789",
                "started_at": "2025-06-03T10:00:00Z"
            }
        }
    )

# Enhanced response models for status API restructuring

class ProgressInfo(BaseModel):
    """Progress information for workflow execution."""
    
    turns: int = Field(..., description="Current number of turns completed")
    max_turns: Optional[int] = Field(None, description="Maximum turns allowed (None for unlimited)")
    current_phase: str = Field(..., description="Current workflow phase")
    phases_completed: List[str] = Field(default_factory=list, description="List of completed phases")
    is_running: bool = Field(..., description="Whether workflow is currently running")


class TokenInfo(BaseModel):
    """Token usage information."""
    
    total: int = Field(..., description="Total tokens used")
    input: int = Field(default=0, description="Input tokens")
    output: int = Field(default=0, description="Output tokens")
    cache_created: int = Field(default=0, description="Cache creation tokens")
    cache_read: int = Field(default=0, description="Cache read tokens")
    cache_efficiency: float = Field(default=0.0, description="Cache efficiency percentage")


class MetricsInfo(BaseModel):
    """Metrics information for workflow execution."""
    
    cost_usd: float = Field(..., description="Total cost in USD")
    tokens: TokenInfo = Field(..., description="Token usage breakdown")
    tools_used: List[str] = Field(default_factory=list, description="List of tools used")
    api_duration_ms: Optional[int] = Field(None, description="API duration in milliseconds")
    performance_score: Optional[float] = Field(None, description="Performance score (0-100)")


class ResultInfo(BaseModel):
    """Result information for workflow completion."""
    
    success: bool = Field(..., description="Whether workflow completed successfully")
    completion_type: str = Field(..., description="Type of completion (completed_successfully, max_turns_reached, failed)")
    message: str = Field(..., description="User-friendly completion message")
    final_output: Optional[str] = Field(None, description="Final output from Claude (truncated)")
    files_created: List[str] = Field(default_factory=list, description="List of files created during workflow")
    git_commits: List[str] = Field(default_factory=list, description="Git commits created")
    files_changed: List[Dict[str, Any]] = Field(default_factory=list, description="Git file changes with diffs")


class EnhancedStatusResponse(BaseModel):
    """Enhanced status response with simplified structure."""
    
    run_id: str = Field(..., description="Unique identifier for this execution run")
    status: Literal["pending", "running", "completed", "failed", "killed"] = Field(
        ..., 
        description="Current status of the execution"
    )
    workflow_name: str = Field(..., description="Name of the workflow being executed")
    started_at: datetime = Field(..., description="When the execution was started")
    completed_at: Optional[datetime] = Field(None, description="When the execution completed")
    execution_time_seconds: Optional[float] = Field(None, description="Total execution time in seconds")
    
    progress: ProgressInfo = Field(..., description="Workflow progress information")
    metrics: MetricsInfo = Field(..., description="Execution metrics")
    result: ResultInfo = Field(..., description="Workflow result information")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "run_id": "run_c706706174b7",
                "status": "completed",
                "workflow_name": "implement",
                "started_at": "2025-06-13T20:25:01Z",
                "completed_at": "2025-06-13T20:27:17Z",
                "execution_time_seconds": 136.5,
                "progress": {
                    "turns": 30,
                    "max_turns": 30,
                    "current_phase": "completed",
                    "phases_completed": ["initialization", "planning", "analysis", "implementation"],
                    "is_running": False
                },
                "metrics": {
                    "cost_usd": 0.7159,
                    "tokens": {
                        "total": 1099100,
                        "input": 850000,
                        "output": 249100,
                        "cache_created": 45000,
                        "cache_read": 120000,
                        "cache_efficiency": 72.7
                    },
                    "tools_used": ["TodoWrite", "LS", "Read", "Bash"],
                    "api_duration_ms": 136500,
                    "performance_score": 85.2
                },
                "result": {
                    "success": True,
                    "completion_type": "max_turns_reached",
                    "message": "⏰ Reached maximum turns - workflow stopped at turn limit",
                    "final_output": "Task partially completed. Review results and continue if needed.",
                    "files_created": ["src/feature.py", "tests/test_feature.py"],
                    "git_commits": ["abc123", "def456"]
                }
            }
        }
    )


class DebugStatusResponse(EnhancedStatusResponse):
    """Debug status response with comprehensive debug information."""
    
    debug: Dict[str, Any] = Field(..., description="Comprehensive debug information")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "run_id": "run_c706706174b7",
                "status": "completed",
                "workflow_name": "implement",
                "started_at": "2025-06-13T20:25:01Z",
                "completed_at": "2025-06-13T20:27:17Z",
                "execution_time_seconds": 136.5,
                "progress": {
                    "turns": 30,
                    "max_turns": 30,
                    "current_phase": "completed",
                    "phases_completed": ["initialization", "planning", "analysis", "implementation"],
                    "is_running": False
                },
                "metrics": {
                    "cost_usd": 0.7159,
                    "tokens": {"total": 1099100, "cache_efficiency": 72.7},
                    "tools_used": ["TodoWrite", "LS", "Read", "Bash"]
                },
                "result": {
                    "success": True,
                    "completion_type": "max_turns_reached",
                    "message": "⏰ Reached maximum turns - workflow stopped at turn limit",
                    "final_output": "Task partially completed. Review results and continue if needed."
                },
                "debug": {
                    "session_info": {"session_id": "12345", "claude_session_id": "uuid"},
                    "execution_details": {"exit_code": 0, "max_turns": 30},
                    "tool_usage": {"total_tool_calls": 30, "unique_tools_used": 4},
                    "timing_analysis": {"average_turn_time_seconds": 4.55},
                    "cost_breakdown": {"cost_per_token": 0.0000065},
                    "workflow_phases": {"phases_detected": ["initialization", "analysis", "implementation"]},
                    "performance_metrics": {"turn_efficiency_percent": 100.0},
                    "error_analysis": {"total_errors": 2, "error_rate_percent": 6.7},
                    "raw_stream_sample": [{"timestamp": "2025-06-13T20:27:17Z", "event_type": "result"}]
                }
            }
        }
    )


class ClaudeCodeStatusResponse(BaseModel):
    """Response model for execution status polling."""
    
    run_id: str = Field(..., description="Unique identifier for this execution run")
    status: Literal["pending", "running", "completed", "failed", "killed"] = Field(
        ..., 
        description="Current status of the execution"
    )
    session_id: str = Field(..., description="Session identifier")
    started_at: datetime = Field(..., description="When the execution was started")
    updated_at: datetime = Field(..., description="Last status update time")
    container_id: Optional[str] = Field(None, description="Docker container ID if running")
    execution_time: Optional[float] = Field(None, description="Total execution time in seconds")
    
    # Only populated when status is "completed" or "failed"
    result: Optional[str] = Field(None, description="Claude's final result text")
    exit_code: Optional[int] = Field(None, description="Container exit code")
    git_commits: List[str] = Field(default_factory=list, description="List of git commit SHAs")
    git_sha_end: Optional[str] = Field(None, description="Final git SHA after changes")
    error: Optional[str] = Field(None, description="Error message if execution failed")
    logs: Optional[str] = Field(None, description="Container execution logs")
    
    # Extended fields
    workflow_name: Optional[str] = Field(None, description="Workflow name")
    claude_session_id: Optional[str] = Field(None, description="Claude session ID")
    cost: Optional[float] = Field(None, description="Execution cost in USD")
    tokens: Optional[int] = Field(None, description="Total tokens used")
    turns: Optional[int] = Field(None, description="Number of turns completed")
    tool_calls: Optional[int] = Field(None, description="Number of tool calls made")
    tools_used: Optional[List[str]] = Field(None, description="List of tools used")
    progress_indicator: Optional[str] = Field(None, description="Progress indicator")
    last_activity: Optional[datetime] = Field(None, description="Last activity timestamp")
    recent_steps: Optional[List[str]] = Field(None, description="Recent workflow steps")
    elapsed_seconds: Optional[float] = Field(None, description="Elapsed time in seconds")
    current_turns: Optional[int] = Field(None, description="Current turn count")
    max_turns: Optional[int] = Field(None, description="Maximum turns allowed")
    debug_info: Optional[Dict[str, Any]] = Field(None, description="Debug information")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "run_id": "run_abc123def456",
                "status": "completed",
                "session_id": "session_xyz789",
                "started_at": "2025-06-03T10:00:00Z",
                "updated_at": "2025-06-03T11:00:00Z",
                "container_id": "claude-code-session_xyz789-abc123",
                "execution_time": 3600.5,
                "result": "Successfully fixed the session timeout issue",
                "exit_code": 0,
                "git_commits": ["abc123def456", "def456ghi789"],
                "git_sha_end": "def456ghi789",
                "error": None,
                "logs": "Container execution logs...",
                "workflow_name": "surgeon",
                "cost": 0.7159,
                "tokens": 1099100,
                "turns": 30,
                "debug_info": None
            }
        }
    )

class WorkflowInfo(BaseModel):
    """Information about an available workflow."""
    
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    path: str = Field(..., description="Filesystem path to workflow")
    valid: bool = Field(..., description="Whether workflow configuration is valid")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "surgeon",
                "description": "Bug fixing specialist workflow",
                "path": "/path/to/workflows/surgeon",
                "valid": True
            }
        }
    )

class ContainerInfo(BaseModel):
    """Information about a container."""
    
    container_id: str = Field(..., description="Docker container ID")
    status: str = Field(..., description="Container status")
    session_id: str = Field(..., description="Associated session ID")
    workflow_name: str = Field(..., description="Workflow being executed")
    created_at: datetime = Field(..., description="When container was created")
    started_at: Optional[datetime] = Field(None, description="When container started execution")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "container_id": "claude-code-session_xyz789-abc123",
                "status": "running",
                "session_id": "session_xyz789",
                "workflow_name": "surgeon",
                "created_at": "2025-06-03T10:00:00Z",
                "started_at": "2025-06-03T10:00:30Z"
            }
        }
    )

class ExecutionResult(BaseModel):
    """Result of a Claude CLI execution."""
    
    success: bool = Field(..., description="Whether execution succeeded")
    exit_code: int = Field(..., description="Container exit code")
    execution_time: float = Field(..., description="Total execution time in seconds")
    container_id: str = Field(..., description="Docker container ID")
    session_id: Optional[str] = Field(None, description="Claude session ID")
    result: Optional[str] = Field(None, description="Claude's result text")
    error: Optional[str] = Field(None, description="Error message if failed")
    logs: str = Field(..., description="Container execution logs")
    git_commits: List[str] = Field(default_factory=list, description="Git commit SHAs created")
    timeout: bool = Field(default=False, description="Whether execution timed out")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "exit_code": 0,
                "execution_time": 1234.5,
                "container_id": "claude-code-session_xyz789-abc123",
                "session_id": "claude_session_abc123",
                "result": "Task completed successfully",
                "error": None,
                "logs": "Container execution logs...",
                "git_commits": ["abc123def456"],
                "timeout": False
            }
        }
    )

class ClaudeCodeConfig(BaseModel):
    """Configuration for Claude-Code agent."""
    
    agent_type: str = Field(default="claude-code", description="Agent framework type")
    framework: str = Field(default="claude-cli", description="Underlying framework")
    docker_image: str = Field(default="claude-code-agent:latest", description="Docker image to use")
    container_timeout: int = Field(default=7200, description="Container timeout in seconds")
    max_concurrent_sessions: int = Field(default=10, description="Max concurrent containers")
    workspace_volume_prefix: str = Field(
        default="claude-code-workspace", 
        description="Prefix for workspace volumes"
    )
    default_workflow: str = Field(default="surgeon", description="Default workflow to use")
    git_branch: Optional[str] = Field(
        None,
        description="Default git branch (defaults to current branch)"
    )
    enabled: bool = Field(default=False, description="Whether claude-code agent is enabled")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "agent_type": "claude-code",
                "framework": "claude-cli",
                "docker_image": "claude-code-agent:latest",
                "container_timeout": 7200,
                "max_concurrent_sessions": 10,
                "workspace_volume_prefix": "claude-code-workspace",
                "default_workflow": "surgeon",
                "git_branch": "main",
                "enabled": True
            }
        }
    )


# Additional models for container management and execution
class ContainerStatus(str, Enum):
    """Container lifecycle status."""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    TERMINATED = "terminated"
    KILLED = "killed"


class ExecutionStatus(str, Enum):
    """Execution status for Claude runs."""
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    KILLED = "killed"


class WorkflowType(str, Enum):
    """Available workflow types - dynamically discovered from filesystem."""


class ContainerConfig(BaseModel):
    """Configuration for Docker container creation."""
    image: str = "claude-code:latest"
    cpu_limit: str = "2.0"
    memory_limit: str = "2g"
    timeout_seconds: int = 7200  # 2 hours
    volumes: Dict[str, str] = Field(default_factory=dict)
    environment: Dict[str, str] = Field(default_factory=dict)
    working_dir: str = "/workspace"
    command: Optional[List[str]] = None


class GitConfig(BaseModel):
    """Git configuration for repository operations."""
    repository_url: str
    branch: str = "main"
    user_name: str = "Claude Code Agent"
    user_email: str = "claude-code@automagik-agents.com"
    commit_prefix: str = ""
    auto_push: bool = True


class WorkflowConfig(BaseModel):
    """Configuration for a specific workflow."""
    name: str
    workflow_type: WorkflowType
    prompt_file: str
    allowed_tools: List[str] = Field(default_factory=list)
    mcp_config: Optional[Dict[str, Any]] = None
    environment: Dict[str, str] = Field(default_factory=dict)
    container_config: ContainerConfig = Field(default_factory=ContainerConfig)
    git_config: Optional[GitConfig] = None


class ExecutionMetadata(BaseModel):
    """Metadata for session storage."""
    agent_type: str = "claude-code"
    workflow_name: str
    container_id: Optional[str] = None
    volume_name: Optional[str] = None
    git_branch: Optional[str] = None
    repository_url: Optional[str] = None
    run_id: UUID = Field(default_factory=uuid4)
    status: ExecutionStatus = ExecutionStatus.QUEUED


class ExecutionContext(BaseModel):
    """Context information for execution."""
    execution_time: Optional[float] = None
    container_logs: Optional[str] = None
    git_operations: List[str] = Field(default_factory=list)
    resource_usage: Dict[str, Any] = Field(default_factory=dict)
    error_details: Optional[str] = None


class ContainerStats(BaseModel):
    """Container resource statistics."""
    cpu_percent: Optional[float] = None
    memory_usage: Optional[int] = None
    memory_limit: Optional[int] = None
    memory_percent: Optional[float] = None
    network_io: Optional[Dict[str, int]] = None
    block_io: Optional[Dict[str, int]] = None
    pids: Optional[int] = None


# Error models
class ClaudeCodeError(Exception):
    """Base exception for Claude-Code operations."""
    pass


class ContainerError(ClaudeCodeError):
    """Container-related errors."""
    pass


class ExecutorError(ClaudeCodeError):
    """Execution-related errors."""
    pass


class GitError(ClaudeCodeError):
    """Git operation errors."""
    pass


class WorkflowError(ClaudeCodeError):
    """Workflow configuration errors."""
    pass


# Time Machine models for container rollback
class ContainerSnapshot(BaseModel):
    """Snapshot of container execution for Time Machine rollback."""
    run_id: str = Field(..., description="Unique run identifier")
    container_id: str = Field(..., description="Docker container ID")
    volume_name: str = Field(..., description="Workspace volume name")
    git_branch: str = Field(..., description="Git branch name")
    parent_commit: str = Field(..., description="Base commit SHA before execution")
    execution_state: Dict[str, Any] = Field(..., description="Complete execution state")
    workflow_name: WorkflowType = Field(..., description="Workflow that was executed")
    claude_session_id: Optional[str] = Field(None, description="Claude session ID")
    container_status: ContainerStatus = Field(..., description="Final container status")
    claude_command: str = Field(..., description="Full claude command executed")
    max_turns_used: int = Field(..., description="Number of turns used")
    cost_usd: float = Field(..., description="Execution cost in USD")
    duration_ms: int = Field(..., description="Execution duration in milliseconds")
    exit_code: int = Field(..., description="Container exit code")
    git_commits: List[str] = Field(default_factory=list, description="Git commits created")
    final_git_sha: Optional[str] = Field(None, description="Final git SHA")
    human_feedback: Optional[str] = Field(None, description="Human feedback if provided")
    failure_analysis: Optional[Dict[str, Any]] = Field(None, description="Failure analysis if applicable")
    learning_context: Optional[str] = Field(None, description="Learning for next attempt")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Snapshot creation time")


class ClaudeExecutionOutput(BaseModel):
    """Output from Claude CLI execution in JSON format."""
    type: str = Field(default="result", description="Output type")
    subtype: str = Field(default="success", description="Output subtype")
    cost_usd: float = Field(..., description="Execution cost in USD")
    duration_ms: int = Field(..., description="Duration in milliseconds")
    num_turns: int = Field(..., description="Number of turns used")
    session_id: str = Field(..., description="Claude session identifier")
    result: str = Field(..., description="Result text from Claude")
    

class FailureAnalysis(BaseModel):
    """Analysis of container execution failure."""
    failure_type: str = Field(..., description="Type of failure (scope_creep, integration_issue, etc)")
    failure_point: str = Field(..., description="Where in the workflow the failure occurred")
    root_cause: str = Field(..., description="Detailed root cause analysis")
    prevention_strategy: str = Field(..., description="How to prevent this failure in future")
    failure_indicators: List[str] = Field(default_factory=list, description="Indicators of this failure type")
    recommended_changes: List[str] = Field(default_factory=list, description="Recommended configuration changes")