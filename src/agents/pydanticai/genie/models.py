"""Data models for Genie orchestrator agent."""

from typing import Dict, List, Optional, Any, Literal, TypedDict
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class WorkflowType(str, Enum):
    """Available workflow types - dynamically discovered from Claude Code."""
    # Legacy enum removed - workflows are now discovered dynamically
    # This enum is kept for backward compatibility but should not be used
    pass


class EpicPhase(str, Enum):
    """Epic execution phases."""
    PLANNING = "planning"
    EXECUTING = "executing"
    REVIEWING = "reviewing"
    COMPLETE = "complete"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ApprovalStatus(str, Enum):
    """Human approval status."""
    NOT_REQUIRED = "not_required"
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    TIMEOUT = "timeout"


class ApprovalTriggerType(str, Enum):
    """Approval trigger reasons."""
    HIGH_COST = "high_cost"
    DESTRUCTIVE_CHANGES = "destructive_changes"
    EXTERNAL_DEPENDENCIES = "external_dependencies"
    MANUAL_OVERRIDE = "manual_override"


class WorkflowResult(BaseModel):
    """Result from a workflow execution."""
    workflow: str  # Dynamic workflow name
    container_id: str
    status: Literal["success", "failed", "timeout", "cancelled", "killed"]
    start_time: datetime
    end_time: Optional[datetime] = None
    cost_usd: float = 0.0
    summary: Optional[str] = None
    error: Optional[str] = None
    git_commits: List[str] = Field(default_factory=list)
    files_changed: List[str] = Field(default_factory=list)
    artifacts: Dict[str, Any] = Field(default_factory=dict)


class ApprovalPoint(BaseModel):
    """Human approval checkpoint."""
    id: str
    workflow: str  # Dynamic workflow name
    trigger_type: ApprovalTriggerType
    reason: str
    description: str
    requested_at: datetime
    decided_at: Optional[datetime] = None
    decision: Optional[ApprovalStatus] = None
    approver: Optional[str] = None
    comments: Optional[str] = None


class RollbackPoint(BaseModel):
    """Git rollback checkpoint."""
    id: str
    workflow: str  # Dynamic workflow name
    commit_sha: str
    branch_name: str
    created_at: datetime
    description: str


class EpicRequest(BaseModel):
    """User's epic request."""
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)
    budget_limit: float = 50.0
    require_tests: bool = True
    require_pr: bool = True
    approval_mode: Literal["auto", "manual"] = "auto"


class EpicPlan(BaseModel):
    """Planned epic execution."""
    epic_id: str
    title: str
    description: str
    complexity_score: int = Field(ge=1, le=10)
    planned_workflows: List[str]  # Dynamic workflow names
    estimated_cost: float
    estimated_duration_minutes: int
    requires_approvals: List[str] = Field(default_factory=list)
    
    
class EpicState(TypedDict):
    """LangGraph state for epic orchestration."""
    # Core identifiers
    epic_id: str
    session_id: str
    user_id: Optional[str]
    thread_id: str
    
    # Epic details
    original_request: str
    epic_title: str
    epic_description: str
    complexity_score: int
    
    # Workflow planning
    planned_workflows: List[str]
    completed_workflows: List[str]
    current_workflow: Optional[str]
    workflow_results: Dict[str, Any]
    
    # Cost management
    cost_accumulated: float
    cost_limit: float
    cost_estimates: Dict[str, float]
    
    # Human approval tracking
    approval_points: List[Dict[str, Any]]
    pending_approvals: List[str]
    approval_history: Dict[str, Any]
    
    # Execution state
    phase: str  # planning, executing, reviewing, complete, failed
    error_count: int
    rollback_points: List[Dict[str, Any]]
    
    # Learning & patterns
    applied_patterns: List[str]
    discovered_patterns: List[str]
    failure_reasons: List[str]
    
    # Communication
    slack_channel_id: Optional[str]
    slack_thread_ts: Optional[str]
    messages: List[Dict[str, Any]]
    
    # Git state
    git_branch: str
    git_snapshots: Dict[str, str]
    
    # Claude Code integration
    active_container_id: Optional[str]
    container_history: List[Dict[str, Any]]
    
    # Timestamps
    created_at: str
    updated_at: str
    completed_at: Optional[str]


class ClaudeCodeRequest(BaseModel):
    """Request to Claude Code API."""
    workflow: str  # Dynamic workflow name
    message: str
    session_id: str
    config: Dict[str, Any] = Field(default_factory=dict)
    

class ClaudeCodeResponse(BaseModel):
    """Response from Claude Code API."""
    run_id: str
    status: Literal["running", "completed", "failed", "timeout", "killed"]
    container_id: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    cost_usd: float = 0.0
    

class EpicSummary(BaseModel):
    """Summary of completed epic."""
    epic_id: str
    title: str
    status: EpicPhase
    workflows_completed: List[str]  # Dynamic workflow names
    total_cost: float
    duration_minutes: int
    git_commits: List[str]
    files_changed: List[str]
    approvals_required: int
    approvals_received: int
    rollbacks_performed: int
    success_rate: float
    summary: str