"""Tests for Genie Agent models and data structures."""
import pytest
from unittest.mock import Mock
import sys
import os
from datetime import datetime
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

# Test the models directly without importing the full agent
from src.agents.pydanticai.genie.models import (
    WorkflowType, EpicPhase, EpicRequest, EpicPlan, EpicState,
    WorkflowResult, ApprovalPoint, ApprovalStatus, ApprovalTriggerType, RollbackPoint
)


class TestWorkflowType:
    """Test WorkflowType enum."""

    def test_workflow_type_values(self):
        """Test that all expected workflow types exist."""
        expected_types = [
            "architect", "implement", "test", "review", 
            "fix", "refactor", "document", "pr"
        ]
        
        actual_types = [wt.value for wt in WorkflowType]
        
        for expected in expected_types:
            assert expected in actual_types

    def test_workflow_type_enum_membership(self):
        """Test workflow type enum membership."""
        assert WorkflowType.TEST in WorkflowType
        assert WorkflowType.IMPLEMENT in WorkflowType
        assert WorkflowType.ARCHITECT in WorkflowType


class TestEpicPhase:
    """Test EpicPhase enum."""

    def test_epic_phase_values(self):
        """Test that all expected epic phases exist."""
        expected_phases = [
            "planning", "executing", "reviewing", 
            "complete", "failed", "cancelled"
        ]
        
        actual_phases = [ep.value for ep in EpicPhase]
        
        for expected in expected_phases:
            assert expected in actual_phases

    def test_epic_phase_progression(self):
        """Test logical epic phase progression."""
        # Test typical progression
        assert EpicPhase.PLANNING.value == "planning"
        assert EpicPhase.EXECUTING.value == "executing"
        assert EpicPhase.COMPLETE.value == "complete"


class TestEpicRequest:
    """Test EpicRequest model."""

    def test_epic_request_creation(self):
        """Test creating a valid EpicRequest."""
        request = EpicRequest(
            message="Create comprehensive tests",
            context={"project": "auth"},
            budget_limit=100.0,
            require_tests=True,
            require_pr=True
        )
        
        assert request.message == "Create comprehensive tests"
        assert request.context["project"] == "auth"
        assert request.budget_limit == 100.0
        assert request.require_tests is True

    def test_epic_request_validation(self):
        """Test EpicRequest validation."""
        # Test with minimal required fields
        request = EpicRequest(
            message="Simple task"
        )
        
        # Check defaults are applied
        assert request.message == "Simple task"
        assert request.budget_limit == 50.0  # Default
        assert request.require_tests is True  # Default

    def test_epic_request_with_optional_fields(self):
        """Test EpicRequest with optional fields."""
        request = EpicRequest(
            message="Complex task with custom settings",
            budget_limit=200.0,
            require_tests=False,
            require_pr=False,
            approval_mode="manual"
        )
        
        assert request.message == "Complex task with custom settings"
        assert request.budget_limit == 200.0
        assert request.require_tests is False
        assert request.approval_mode == "manual"


class TestEpicPlan:
    """Test EpicPlan model."""

    def test_epic_plan_creation(self):
        """Test creating a valid EpicPlan."""
        plan = EpicPlan(
            epic_id="epic-123",
            title="Authentication Implementation",
            description="Create comprehensive authentication system",
            complexity_score=7,
            planned_workflows=[WorkflowType.ARCHITECT, WorkflowType.IMPLEMENT, WorkflowType.TEST],
            estimated_cost=45.50,
            estimated_duration_minutes=90,
            requires_approvals=["security-review"]
        )
        
        assert plan.epic_id == "epic-123"
        assert plan.title == "Authentication Implementation"
        assert len(plan.planned_workflows) == 3
        assert plan.estimated_cost == 45.50
        assert plan.estimated_duration_minutes == 90
        assert WorkflowType.TEST in plan.planned_workflows

    def test_epic_plan_cost_validation(self):
        """Test epic plan cost validation."""
        plan = EpicPlan(
            epic_id="epic-test",
            title="Simple Test",
            description="Simple test task",
            complexity_score=2,
            planned_workflows=[WorkflowType.TEST],
            estimated_cost=0.0,  # Zero cost should be valid
            estimated_duration_minutes=15
        )
        
        assert plan.estimated_cost == 0.0
        assert plan.complexity_score == 2

    def test_epic_plan_workflow_ordering(self):
        """Test that workflow ordering is preserved."""
        workflows = [WorkflowType.ARCHITECT, WorkflowType.IMPLEMENT, WorkflowType.TEST]
        plan = EpicPlan(
            epic_id="epic-order",
            title="Workflow Order Test",
            description="Test workflow ordering",
            complexity_score=5,
            planned_workflows=workflows,
            estimated_cost=30.0,
            estimated_duration_minutes=60
        )
        
        assert plan.planned_workflows == workflows
        assert plan.planned_workflows[0] == WorkflowType.ARCHITECT
        assert plan.planned_workflows[2] == WorkflowType.TEST


class TestEpicState:
    """Test EpicState model."""

    def test_epic_state_creation(self):
        """Test creating a complete EpicState."""
        state: EpicState = {
            "epic_id": "epic-123",
            "session_id": "session-456",
            "user_id": "user-789",
            "thread_id": "thread-012",
            "original_request": "Create comprehensive tests",
            "epic_title": "Test Creation Epic",
            "epic_description": "Create a comprehensive test suite",
            "complexity_score": 5,
            "planned_workflows": ["architect", "implement", "test"],
            "completed_workflows": [],
            "current_workflow": None,
            "workflow_results": {},
            "cost_accumulated": 0.0,
            "cost_limit": 50.0,
            "cost_estimates": {},
            "approval_points": [],
            "pending_approvals": [],
            "approval_history": {},
            "phase": "planning",
            "error_count": 0,
            "rollback_points": [],
            "applied_patterns": [],
            "discovered_patterns": [],
            "failure_reasons": [],
            "slack_channel_id": None,
            "slack_thread_ts": None,
            "messages": [],
            "git_branch": "main",
            "git_snapshots": {},
            "active_container_id": None,
            "container_history": [],
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:00:00Z",
            "completed_at": None
        }
        
        assert state["epic_id"] == "epic-123"
        assert state["phase"] == "planning"
        assert state["cost_accumulated"] == 0.0
        assert len(state["planned_workflows"]) == 3

    def test_epic_state_phase_transitions(self):
        """Test epic state phase transitions."""
        state: EpicState = {
            "epic_id": "epic-123",
            "session_id": "session-456",
            "user_id": None,
            "thread_id": "thread-012",
            "original_request": "Test request",
            "epic_title": "Test Epic",
            "epic_description": "Test description",
            "complexity_score": 3,
            "planned_workflows": ["test"],
            "completed_workflows": [],
            "current_workflow": None,
            "workflow_results": {},
            "cost_accumulated": 0.0,
            "cost_limit": 50.0,
            "cost_estimates": {},
            "approval_points": [],
            "pending_approvals": [],
            "approval_history": {},
            "phase": "planning",
            "error_count": 0,
            "rollback_points": [],
            "applied_patterns": [],
            "discovered_patterns": [],
            "failure_reasons": [],
            "slack_channel_id": None,
            "slack_thread_ts": None,
            "messages": [],
            "git_branch": "main",
            "git_snapshots": {},
            "active_container_id": None,
            "container_history": [],
            "created_at": "2024-01-01T10:00:00Z",
            "updated_at": "2024-01-01T10:00:00Z",
            "completed_at": None
        }
        
        # Test phase updates
        state["phase"] = "executing"
        assert state["phase"] == "executing"
        
        state["phase"] = "complete"
        assert state["phase"] == "complete"


class TestWorkflowResult:
    """Test WorkflowResult model."""

    def test_workflow_result_creation(self):
        """Test creating a WorkflowResult."""
        result = WorkflowResult(
            workflow=WorkflowType.TEST,
            container_id="container-123",
            status="success",
            start_time=datetime.now(),
            end_time=datetime.now(),
            cost_usd=12.50,
            summary="Tests completed successfully",
            git_commits=["abc123"],
            files_changed=["tests/test_auth.py", "src/auth.py"]
        )
        
        assert result.workflow == WorkflowType.TEST
        assert result.status == "success"
        assert result.cost_usd == 12.50
        assert len(result.git_commits) == 1
        assert "test_auth.py" in result.files_changed[0]

    def test_workflow_result_failure(self):
        """Test WorkflowResult for failed workflow."""
        result = WorkflowResult(
            workflow=WorkflowType.IMPLEMENT,
            container_id="container-456",
            status="failed",
            start_time=datetime.now(),
            cost_usd=5.0,
            error="Implementation failed due to missing dependencies"
        )
        
        assert result.status == "failed"
        assert result.error is not None
        assert "missing dependencies" in result.error


class TestApprovalPoint:
    """Test ApprovalPoint model."""

    def test_approval_point_creation(self):
        """Test creating an ApprovalPoint."""
        approval = ApprovalPoint(
            id="approval-123",
            workflow=WorkflowType.IMPLEMENT,
            trigger_type=ApprovalTriggerType.HIGH_COST,
            reason="Cost exceeds threshold of $50",
            description="High cost workflow requires approval",
            requested_at=datetime.now()
        )
        
        assert approval.id == "approval-123"
        assert approval.workflow == WorkflowType.IMPLEMENT
        assert approval.reason == "Cost exceeds threshold of $50"
        assert approval.decision is None  # Pending approval

    def test_approval_point_approval_process(self):
        """Test approval point approval process."""
        approval = ApprovalPoint(
            id="approval-123",
            workflow=WorkflowType.IMPLEMENT,
            trigger_type=ApprovalTriggerType.EXTERNAL_DEPENDENCIES,
            reason="Security-related changes detected",
            description="Authentication module changes require review",
            requested_at=datetime.now()
        )
        
        # Simulate approval
        approval.decision = ApprovalStatus.APPROVED
        approval.approver = "user-123"
        approval.decided_at = datetime.now()
        approval.comments = "Looks good, approved"
        
        assert approval.decision == ApprovalStatus.APPROVED
        assert approval.approver == "user-123"
        assert approval.decided_at is not None
        assert "approved" in approval.comments.lower()


class TestApprovalStatus:
    """Test ApprovalStatus enum."""

    def test_approval_status_values(self):
        """Test that all expected approval status values exist."""
        expected_statuses = [
            "not_required", "pending", "approved", "denied", "timeout"
        ]
        
        actual_statuses = [status.value for status in ApprovalStatus]
        
        for expected in expected_statuses:
            assert expected in actual_statuses

    def test_approval_status_flow(self):
        """Test typical approval status flow."""
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.DENIED.value == "denied"


class TestRollbackPoint:
    """Test RollbackPoint model."""

    def test_rollback_point_creation(self):
        """Test creating a RollbackPoint."""
        rollback = RollbackPoint(
            id="rollback-123",
            workflow=WorkflowType.IMPLEMENT,
            commit_sha="abc123def456",
            branch_name="epic-feature-branch",
            created_at=datetime.now(),
            description="Before implementing authentication changes"
        )
        
        assert rollback.id == "rollback-123"
        assert rollback.workflow == WorkflowType.IMPLEMENT
        assert rollback.commit_sha == "abc123def456"
        assert rollback.branch_name == "epic-feature-branch"
        assert rollback.created_at is not None


class TestModelIntegration:
    """Test integration between different models."""

    def test_epic_request_to_plan_integration(self):
        """Test integration from EpicRequest to EpicPlan."""
        request = EpicRequest(
            message="Implement user authentication with comprehensive testing",
            context={
                "requirements": [
                    "Secure password hashing",
                    "JWT token management", 
                    "Unit tests",
                    "Integration tests"
                ]
            },
            budget_limit=100.0,
            require_tests=True
        )
        
        # Simulate plan generation from request
        plan = EpicPlan(
            epic_id="epic-123",
            title="User Authentication Implementation",
            description=request.message,
            complexity_score=8,
            planned_workflows=[
                WorkflowType.ARCHITECT,
                WorkflowType.IMPLEMENT,
                WorkflowType.TEST,
                WorkflowType.REVIEW
            ],
            estimated_cost=85.0,
            estimated_duration_minutes=180,
            requires_approvals=["security-review"]
        )
        
        assert len(plan.planned_workflows) == 4
        assert WorkflowType.ARCHITECT in plan.planned_workflows
        assert plan.description == request.message
        assert plan.estimated_cost < request.budget_limit

    def test_complete_epic_lifecycle(self):
        """Test complete epic lifecycle through models."""
        # Start with request
        request = EpicRequest(
            message="Create API documentation",
            budget_limit=50.0,
            require_tests=False
        )
        
        # Generate plan
        plan = EpicPlan(
            epic_id="epic-doc-123",
            title="API Documentation",
            description=request.message,
            complexity_score=4,
            planned_workflows=[WorkflowType.DOCUMENT],
            estimated_cost=15.0,
            estimated_duration_minutes=45
        )
        
        # Create initial state
        state: EpicState = {
            "epic_id": plan.epic_id,
            "session_id": "session-123",
            "user_id": "user-456",
            "thread_id": "thread-789",
            "original_request": request.message,
            "epic_title": plan.title,
            "epic_description": plan.description,
            "complexity_score": plan.complexity_score,
            "planned_workflows": [w.value for w in plan.planned_workflows],
            "completed_workflows": [],
            "current_workflow": None,
            "workflow_results": {},
            "cost_accumulated": 0.0,
            "cost_limit": request.budget_limit,
            "cost_estimates": {},
            "approval_points": [],
            "pending_approvals": [],
            "approval_history": {},
            "phase": "planning",
            "error_count": 0,
            "rollback_points": [],
            "applied_patterns": [],
            "discovered_patterns": [],
            "failure_reasons": [],
            "slack_channel_id": None,
            "slack_thread_ts": None,
            "messages": [],
            "git_branch": "main",
            "git_snapshots": {},
            "active_container_id": None,
            "container_history": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "completed_at": None
        }
        
        # Simulate execution
        state["phase"] = "executing"
        state["current_workflow"] = "document"
        
        # Add workflow result
        result = WorkflowResult(
            workflow=WorkflowType.DOCUMENT,
            container_id="container-123",
            status="success",
            start_time=datetime.now(),
            end_time=datetime.now(),
            cost_usd=15.0,
            summary="Documentation created successfully",
            git_commits=["abc123"],
            files_changed=["docs/api.md", "docs/user-guide.md"]
        )
        
        state["workflow_results"]["document"] = {
            "workflow": result.workflow.value,
            "status": result.status,
            "cost_usd": result.cost_usd,
            "summary": result.summary
        }
        state["cost_accumulated"] += result.cost_usd
        state["phase"] = "complete"
        state["completed_at"] = datetime.now().isoformat()
        
        # Verify complete lifecycle
        assert state["phase"] == "complete"
        assert state["cost_accumulated"] == 15.0
        assert len(state["workflow_results"]) == 1
        assert state["workflow_results"]["document"]["status"] == "success"
        assert state["completed_at"] is not None