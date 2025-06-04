"""Unit tests for Claude-Code agent models.

This module tests all Pydantic models for validation, edge cases,
and proper error handling.
"""
import pytest
from datetime import datetime
from uuid import uuid4
from pydantic import ValidationError

from src.agents.claude_code.models import (
    ClaudeCodeRunRequest,
    ClaudeCodeRunResponse,
    ClaudeCodeStatusResponse,
    WorkflowInfo,
    ContainerInfo,
    ExecutionResult,
    ClaudeCodeConfig,
    ContainerStatus,
    ExecutionStatus,
    WorkflowType,
    ContainerConfig,
    GitConfig,
    WorkflowConfig,
    ExecutionMetadata,
    ExecutionContext,
    ContainerStats,
    ContainerSnapshot,
    ClaudeExecutionOutput,
    FailureAnalysis
)


class TestClaudeCodeRunRequest:
    """Test ClaudeCodeRunRequest model validation."""
    
    def test_valid_request(self):
        """Test creating a valid request."""
        request = ClaudeCodeRunRequest(
            message="Fix the bug in session timeout",
            workflow_name="fix",
            max_turns=50
        )
        assert request.message == "Fix the bug in session timeout"
        assert request.workflow_name == "fix"
        assert request.max_turns == 50
        assert request.timeout == 3600  # Default
        
    def test_message_validation(self):
        """Test message validation."""
        # Empty message should fail
        with pytest.raises(ValidationError) as exc_info:
            ClaudeCodeRunRequest(message="", workflow_name="fix")
        assert "Message cannot be empty" in str(exc_info.value)
        
        # Whitespace-only message should fail
        with pytest.raises(ValidationError) as exc_info:
            ClaudeCodeRunRequest(message="   ", workflow_name="fix")
        assert "Message cannot be empty" in str(exc_info.value)
        
    def test_workflow_name_validation(self):
        """Test workflow name validation."""
        # Valid names
        valid_names = ["bug-fixer", "test_runner", "refactor123"]
        for name in valid_names:
            request = ClaudeCodeRunRequest(message="test", workflow_name=name)
            assert request.workflow_name == name
            
        # Invalid names
        with pytest.raises(ValidationError):
            ClaudeCodeRunRequest(message="test", workflow_name="")
        
    def test_max_turns_validation(self):
        """Test max_turns boundaries."""
        # Valid range
        request = ClaudeCodeRunRequest(message="test", workflow_name="fix", max_turns=1)
        assert request.max_turns == 1
        
        request = ClaudeCodeRunRequest(message="test", workflow_name="fix", max_turns=100)
        assert request.max_turns == 100
        
        # Out of range
        with pytest.raises(ValidationError):
            ClaudeCodeRunRequest(message="test", workflow_name="fix", max_turns=0)
            
        with pytest.raises(ValidationError):
            ClaudeCodeRunRequest(message="test", workflow_name="fix", max_turns=101)
            
    def test_timeout_validation(self):
        """Test timeout boundaries."""
        # Valid range
        request = ClaudeCodeRunRequest(message="test", workflow_name="fix", timeout=60)
        assert request.timeout == 60
        
        request = ClaudeCodeRunRequest(message="test", workflow_name="fix", timeout=7200)
        assert request.timeout == 7200
        
        # Out of range
        with pytest.raises(ValidationError):
            ClaudeCodeRunRequest(message="test", workflow_name="fix", timeout=59)
            
        with pytest.raises(ValidationError):
            ClaudeCodeRunRequest(message="test", workflow_name="fix", timeout=7201)


class TestClaudeCodeRunResponse:
    """Test ClaudeCodeRunResponse model."""
    
    def test_valid_response(self):
        """Test creating a valid response."""
        response = ClaudeCodeRunResponse(
            run_id="run_abc123",
            status="pending",
            session_id="session_xyz",
            started_at=datetime.utcnow()
        )
        assert response.run_id == "run_abc123"
        assert response.status == "pending"
        assert response.message == "Container deployment initiated"  # Default
        
    def test_status_validation(self):
        """Test status literal validation."""
        valid_statuses = ["pending", "running", "completed", "failed"]
        for status in valid_statuses:
            response = ClaudeCodeRunResponse(
                run_id="run_123",
                status=status,
                session_id="session_123",
                started_at=datetime.utcnow()
            )
            assert response.status == status
            
        # Invalid status
        with pytest.raises(ValidationError):
            ClaudeCodeRunResponse(
                run_id="run_123",
                status="invalid",
                session_id="session_123",
                started_at=datetime.utcnow()
            )


class TestClaudeCodeStatusResponse:
    """Test ClaudeCodeStatusResponse model."""
    
    def test_pending_status(self):
        """Test pending status response."""
        response = ClaudeCodeStatusResponse(
            run_id="run_123",
            status="pending",
            session_id="session_123",
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        assert response.result is None
        assert response.exit_code is None
        assert response.error is None
        
    def test_completed_status(self):
        """Test completed status with full results."""
        response = ClaudeCodeStatusResponse(
            run_id="run_123",
            status="completed",
            session_id="session_123",
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            container_id="container_abc",
            execution_time=3600.5,
            result="Task completed successfully",
            exit_code=0,
            git_commits=["abc123", "def456"],
            git_sha_end="def456",
            logs="Container execution logs..."
        )
        assert response.result == "Task completed successfully"
        assert response.exit_code == 0
        assert len(response.git_commits) == 2
        
    def test_failed_status(self):
        """Test failed status with error."""
        response = ClaudeCodeStatusResponse(
            run_id="run_123",
            status="failed",
            session_id="session_123",
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            container_id="container_abc",
            execution_time=100.5,
            exit_code=1,
            error="Container crashed",
            logs="Error logs..."
        )
        assert response.error == "Container crashed"
        assert response.exit_code == 1


class TestWorkflowInfo:
    """Test WorkflowInfo model."""
    
    def test_valid_workflow_info(self):
        """Test creating valid workflow info."""
        info = WorkflowInfo(
            name="bug-fixer",
            description="Fixes bugs in code",
            path="/path/to/workflow",
            valid=True
        )
        assert info.name == "bug-fixer"
        assert info.valid is True


class TestContainerInfo:
    """Test ContainerInfo model."""
    
    def test_container_info_creation(self):
        """Test creating container info."""
        info = ContainerInfo(
            container_id="container_123",
            status="running",
            session_id="session_123",
            workflow_name="fix",
            created_at=datetime.utcnow()
        )
        assert info.container_id == "container_123"
        assert info.status == "running"
        assert info.started_at is None  # Optional
        
        # With started_at
        info = ContainerInfo(
            container_id="container_123",
            status="running",
            session_id="session_123",
            workflow_name="fix",
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow()
        )
        assert info.started_at is not None


class TestExecutionResult:
    """Test ExecutionResult model."""
    
    def test_successful_execution(self):
        """Test successful execution result."""
        result = ExecutionResult(
            success=True,
            exit_code=0,
            execution_time=1234.5,
            container_id="container_123",
            session_id="session_123",
            result="Task completed",
            logs="Execution logs...",
            git_commits=["abc123"],
            timeout=False
        )
        assert result.success is True
        assert result.timeout is False
        assert len(result.git_commits) == 1
        
    def test_failed_execution(self):
        """Test failed execution result."""
        result = ExecutionResult(
            success=False,
            exit_code=1,
            execution_time=100.0,
            container_id="container_123",
            error="Task failed",
            logs="Error logs...",
            timeout=False
        )
        assert result.success is False
        assert result.error == "Task failed"
        
    def test_timeout_execution(self):
        """Test timeout execution result."""
        result = ExecutionResult(
            success=False,
            exit_code=-1,
            execution_time=7200.0,
            container_id="container_123",
            error="Execution timed out",
            logs="Timeout logs...",
            timeout=True
        )
        assert result.timeout is True


class TestClaudeCodeConfig:
    """Test ClaudeCodeConfig model."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ClaudeCodeConfig()
        assert config.agent_type == "claude-code"
        assert config.framework == "claude-cli"
        assert config.docker_image == "claude-code-agent:latest"
        assert config.container_timeout == 7200
        assert config.max_concurrent_sessions == 10
        assert config.enabled is False
        
    def test_custom_config(self):
        """Test custom configuration."""
        config = ClaudeCodeConfig(
            docker_image="my-claude:v2",
            container_timeout=3600,
            max_concurrent_sessions=5,
            enabled=True
        )
        assert config.docker_image == "my-claude:v2"
        assert config.container_timeout == 3600
        assert config.max_concurrent_sessions == 5
        assert config.enabled is True


class TestEnums:
    """Test enum models."""
    
    def test_container_status_enum(self):
        """Test ContainerStatus enum values."""
        assert ContainerStatus.PENDING == "pending"
        assert ContainerStatus.RUNNING == "running"
        assert ContainerStatus.COMPLETED == "completed"
        assert ContainerStatus.FAILED == "failed"
        assert ContainerStatus.TIMEOUT == "timeout"
        
    def test_execution_status_enum(self):
        """Test ExecutionStatus enum values."""
        assert ExecutionStatus.QUEUED == "queued"
        assert ExecutionStatus.RUNNING == "running"
        assert ExecutionStatus.COMPLETED == "completed"
        assert ExecutionStatus.FAILED == "failed"
        
    def test_workflow_type_enum(self):
        """Test WorkflowType enum values."""
        assert WorkflowType.ARCHITECT == "architect"
        assert WorkflowType.TEST == "test"
        assert WorkflowType.FIX == "fix"
        assert WorkflowType.REVIEW == "review"


class TestContainerConfig:
    """Test ContainerConfig model."""
    
    def test_default_container_config(self):
        """Test default container configuration."""
        config = ContainerConfig()
        assert config.image == "claude-code:latest"
        assert config.cpu_limit == "2.0"
        assert config.memory_limit == "2g"
        assert config.timeout_seconds == 7200
        assert config.working_dir == "/workspace"
        assert config.volumes == {}
        assert config.environment == {}
        assert config.command is None
        
    def test_custom_container_config(self):
        """Test custom container configuration."""
        config = ContainerConfig(
            image="custom:latest",
            cpu_limit="4.0",
            memory_limit="4g",
            timeout_seconds=3600,
            volumes={"/host/path": "/container/path"},
            environment={"KEY": "value"},
            command=["python", "script.py"]
        )
        assert config.cpu_limit == "4.0"
        assert config.memory_limit == "4g"
        assert len(config.volumes) == 1
        assert len(config.command) == 2


class TestGitConfig:
    """Test GitConfig model."""
    
    def test_git_config(self):
        """Test git configuration."""
        config = GitConfig(
            repository_url="https://github.com/org/repo.git",
            branch="feature-branch",
            user_name="Test User",
            user_email="test@example.com",
            commit_prefix="[AUTO] ",
            auto_push=False
        )
        assert config.repository_url == "https://github.com/org/repo.git"
        assert config.branch == "feature-branch"
        assert config.auto_push is False
        
    def test_git_config_defaults(self):
        """Test git configuration defaults."""
        config = GitConfig(repository_url="https://github.com/org/repo.git")
        assert config.branch == "main"
        assert config.user_name == "Claude Code Agent"
        assert config.auto_push is True


class TestWorkflowConfig:
    """Test WorkflowConfig model."""
    
    def test_workflow_config(self):
        """Test workflow configuration."""
        config = WorkflowConfig(
            name="test-workflow",
            workflow_type=WorkflowType.TEST,
            prompt_file="prompt.md",
            allowed_tools=["tool1", "tool2"],
            mcp_config={"server": "config"},
            environment={"ENV_VAR": "value"}
        )
        assert config.name == "test-workflow"
        assert config.workflow_type == WorkflowType.TEST
        assert len(config.allowed_tools) == 2
        assert config.mcp_config["server"] == "config"


class TestExecutionMetadata:
    """Test ExecutionMetadata model."""
    
    def test_execution_metadata(self):
        """Test execution metadata creation."""
        metadata = ExecutionMetadata(
            workflow_name="fix",
            container_id="container_123",
            git_branch="feature-branch"
        )
        assert metadata.agent_type == "claude-code"
        assert metadata.workflow_name == "fix"
        assert metadata.status == ExecutionStatus.QUEUED
        assert metadata.run_id is not None  # Auto-generated UUID


class TestContainerSnapshot:
    """Test ContainerSnapshot model for Time Machine."""
    
    def test_container_snapshot(self):
        """Test container snapshot creation."""
        snapshot = ContainerSnapshot(
            run_id="run_123",
            container_id="container_123",
            volume_name="volume_123",
            git_branch="feature-branch",
            parent_commit="abc123",
            execution_state={"key": "value"},
            workflow_name=WorkflowType.FIX,
            container_status=ContainerStatus.COMPLETED,
            claude_command="claude --max-turns 30",
            max_turns_used=25,
            cost_usd=0.50,
            duration_ms=60000,
            exit_code=0,
            git_commits=["def456"],
            final_git_sha="def456"
        )
        assert snapshot.run_id == "run_123"
        assert snapshot.cost_usd == 0.50
        assert snapshot.max_turns_used == 25
        assert len(snapshot.git_commits) == 1
        
    def test_container_snapshot_with_failure(self):
        """Test container snapshot with failure analysis."""
        failure = FailureAnalysis(
            failure_type="scope_creep",
            failure_point="implementation",
            root_cause="Task expanded beyond original scope",
            prevention_strategy="Better task definition",
            failure_indicators=["Multiple unrelated changes"],
            recommended_changes=["Set clearer boundaries"]
        )
        
        snapshot = ContainerSnapshot(
            run_id="run_123",
            container_id="container_123",
            volume_name="volume_123",
            git_branch="feature-branch",
            parent_commit="abc123",
            execution_state={},
            workflow_name=WorkflowType.FIX,
            container_status=ContainerStatus.FAILED,
            claude_command="claude --max-turns 30",
            max_turns_used=30,
            cost_usd=1.00,
            duration_ms=120000,
            exit_code=1,
            failure_analysis=failure.dict(),
            human_feedback="Task went off track"
        )
        assert snapshot.container_status == ContainerStatus.FAILED
        assert snapshot.failure_analysis is not None
        assert snapshot.human_feedback == "Task went off track"


class TestClaudeExecutionOutput:
    """Test ClaudeExecutionOutput model."""
    
    def test_claude_execution_output(self):
        """Test Claude execution output parsing."""
        output = ClaudeExecutionOutput(
            type="result",
            subtype="success",
            cost_usd=0.25,
            duration_ms=30000,
            num_turns=15,
            session_id="claude_session_123",
            result="Fixed the bug successfully"
        )
        assert output.cost_usd == 0.25
        assert output.num_turns == 15
        assert output.result == "Fixed the bug successfully"


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_empty_environment_dict(self):
        """Test models with empty dictionaries."""
        request = ClaudeCodeRunRequest(
            message="test",
            workflow_name="fix",
            environment={}
        )
        assert request.environment == {}
        
    def test_none_optional_fields(self):
        """Test models with None optional fields."""
        response = ClaudeCodeStatusResponse(
            run_id="run_123",
            status="pending",
            session_id="session_123",
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            container_id=None,
            execution_time=None,
            result=None,
            exit_code=None,
            error=None,
            logs=None
        )
        assert response.container_id is None
        assert response.result is None
        
    def test_large_git_commits_list(self):
        """Test handling large lists."""
        commits = [f"commit_{i}" for i in range(100)]
        result = ExecutionResult(
            success=True,
            exit_code=0,
            execution_time=1000.0,
            container_id="container_123",
            logs="logs",
            git_commits=commits
        )
        assert len(result.git_commits) == 100
        
    def test_special_characters_in_strings(self):
        """Test special characters in string fields."""
        request = ClaudeCodeRunRequest(
            message="Fix bug with 'quotes' and \"double quotes\" and \n newlines",
            workflow_name="fix-special_chars-123"
        )
        assert "quotes" in request.message
        assert "newlines" in request.message