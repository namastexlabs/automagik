"""Data models for Claude-Code agent.

This module defines Pydantic models for request/response handling,
configuration validation, and container management.
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Literal
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4

class ClaudeCodeRunRequest(BaseModel):
    """Request model for Claude CLI execution."""
    
    message: str = Field(..., description="The task message for Claude to execute")
    session_id: Optional[str] = Field(None, description="Optional session ID for continuity")
    workflow_name: str = Field("bug-fixer", description="Name of the workflow to execute")
    max_turns: int = Field(default=30, ge=1, le=100, description="Maximum number of Claude turns")
    git_branch: str = Field(
        default="NMSTX-187-langgraph-orchestrator-migration", 
        description="Git branch to work on"
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
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "message": "Fix the session timeout issue in agent controller",
                "session_id": "session_abc123",
                "workflow_name": "bug-fixer",
                "max_turns": 50,
                "git_branch": "fix/session-timeout",
                "timeout": 3600,
                "environment": {
                    "CUSTOM_VAR": "value"
                }
            }
        }

class ClaudeCodeRunResponse(BaseModel):
    """Response model for async Claude CLI execution start."""
    
    run_id: str = Field(..., description="Unique identifier for this execution run")
    status: Literal["pending", "running", "completed", "failed"] = Field(
        ..., 
        description="Current status of the execution"
    )
    message: str = Field(default="Container deployment initiated", description="Status message")
    session_id: str = Field(..., description="Session identifier")
    started_at: datetime = Field(..., description="When the execution was started")
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "run_id": "run_abc123def456",
                "status": "pending",
                "message": "Container deployment initiated",
                "session_id": "session_xyz789",
                "started_at": "2025-06-03T10:00:00Z"
            }
        }

class ClaudeCodeStatusResponse(BaseModel):
    """Response model for execution status polling."""
    
    run_id: str = Field(..., description="Unique identifier for this execution run")
    status: Literal["pending", "running", "completed", "failed"] = Field(
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
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
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
                "logs": "Container execution logs..."
            }
        }

class WorkflowInfo(BaseModel):
    """Information about an available workflow."""
    
    name: str = Field(..., description="Workflow name")
    description: str = Field(..., description="Workflow description")
    path: str = Field(..., description="Filesystem path to workflow")
    valid: bool = Field(..., description="Whether workflow configuration is valid")
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "name": "bug-fixer",
                "description": "Bug fixing specialist workflow",
                "path": "/path/to/workflows/bug-fixer",
                "valid": True
            }
        }

class ContainerInfo(BaseModel):
    """Information about a container."""
    
    container_id: str = Field(..., description="Docker container ID")
    status: str = Field(..., description="Container status")
    session_id: str = Field(..., description="Associated session ID")
    workflow_name: str = Field(..., description="Workflow being executed")
    created_at: datetime = Field(..., description="When container was created")
    started_at: Optional[datetime] = Field(None, description="When container started execution")
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "container_id": "claude-code-session_xyz789-abc123",
                "status": "running",
                "session_id": "session_xyz789",
                "workflow_name": "bug-fixer",
                "created_at": "2025-06-03T10:00:00Z",
                "started_at": "2025-06-03T10:00:30Z"
            }
        }

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
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
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
    default_workflow: str = Field(default="bug-fixer", description="Default workflow to use")
    git_branch: str = Field(
        default="NMSTX-187-langgraph-orchestrator-migration",
        description="Default git branch"
    )
    enabled: bool = Field(default=False, description="Whether claude-code agent is enabled")
    
    class Config:
        """Pydantic model configuration."""
        schema_extra = {
            "example": {
                "agent_type": "claude-code",
                "framework": "claude-cli",
                "docker_image": "claude-code-agent:latest",
                "container_timeout": 7200,
                "max_concurrent_sessions": 10,
                "workspace_volume_prefix": "claude-code-workspace",
                "default_workflow": "bug-fixer",
                "git_branch": "main",
                "enabled": True
            }
        }


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


class ExecutionStatus(str, Enum):
    """Execution status for Claude runs."""
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


class WorkflowType(str, Enum):
    """Available workflow types."""
    ARCHITECT = "architect"
    IMPLEMENT = "implement"
    TEST = "test"
    REVIEW = "review"
    FIX = "fix"
    REFACTOR = "refactor"
    DOCUMENT = "document"
    PR = "pr"


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
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Snapshot creation time")


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