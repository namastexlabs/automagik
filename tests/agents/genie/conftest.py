"""Pytest configuration for Genie Agent tests."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.pydanticai.genie.models import (
    EpicRequest, EpicPlan, WorkflowType, EpicPhase
)


@pytest.fixture
def genie_config():
    """Basic configuration for Genie agent testing."""
    return {
        "model_name": "openai:gpt-4.1-mini",
        "model_provider": "openai", 
        "temperature": "0.1",
        "max_tokens": "1000",
        "orchestrator_enabled": True,
        "max_workflow_steps": 5
    }


@pytest.fixture
def mock_dependencies():
    """Mock AutomagikAgentsDependencies for testing."""
    deps = AutomagikAgentsDependencies(
        test_mode=True,
        disable_memory_operations=True,
        mock_external_apis=True,
        model_name="openai:gpt-4.1-mini",
        model_settings={"temperature": 0.0}
    )
    return deps


@pytest.fixture
def sample_epic_request():
    """Sample epic request for testing."""
    return EpicRequest(
        message="Create comprehensive tests for the user authentication system",
        context={
            "requirements": ["Unit tests", "Integration tests", "Edge cases"],
            "acceptance_criteria": ["95% code coverage", "All tests pass", "Performance tests included"]
        }
    )


@pytest.fixture
def sample_epic_plan():
    """Sample epic plan for testing."""
    return EpicPlan(
        epic_id="test-epic-123",
        title="User Authentication Tests",
        description="Create comprehensive tests for the user authentication system",
        complexity_score=7,
        planned_workflows=[WorkflowType.ARCHITECT, WorkflowType.IMPLEMENT, WorkflowType.TEST],
        estimated_cost=25.50,
        estimated_duration_minutes=45,
        requires_approvals=[]
    )


@pytest.fixture
def sample_epic_state():
    """Sample epic state for testing."""
    return {
        # Core identifiers
        "epic_id": "test-epic-123",
        "session_id": "test-session",
        "user_id": "test-user",
        "thread_id": "test-thread",
        
        # Epic details
        "original_request": "Test epic",
        "epic_title": "Test Epic",
        "epic_description": "Test epic description",
        "complexity_score": 5,
        
        # Workflow planning
        "planned_workflows": ["test"],
        "completed_workflows": [],
        "current_workflow": None,
        "workflow_results": {},
        
        # Cost management
        "cost_accumulated": 0.0,
        "cost_limit": 50.0,
        "cost_estimates": {"test": 10.0},
        
        # Approval tracking
        "approval_points": [],
        "pending_approvals": [],
        "approval_history": {},
        
        # Execution state
        "phase": EpicPhase.PLANNING.value,
        "error_count": 0,
        "rollback_points": [],
        
        # Learning & patterns
        "applied_patterns": [],
        "discovered_patterns": [],
        "failure_reasons": [],
        
        # Communication
        "slack_channel_id": None,
        "slack_thread_ts": None,
        "messages": [],
        
        # Git state
        "git_branch": "genie/test-epic-123",
        "git_snapshots": {},
        
        # Container tracking
        "active_container_id": None,
        "container_history": [],
        
        # Timestamps
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00",
        "completed_at": None
    }


@pytest.fixture
def mock_claude_code_client():
    """Mock Claude Code client for testing."""
    client = AsyncMock()
    client.create_container = AsyncMock(return_value={
        "container_id": "test-container-123",
        "status": "created"
    })
    client.execute_workflow = AsyncMock(return_value={
        "success": True,
        "output": "Workflow completed successfully",
        "cost": 5.25,
        "duration_minutes": 15
    })
    client.get_container_logs = AsyncMock(return_value=[
        "Log entry 1",
        "Log entry 2",
        "Workflow completed"
    ])
    return client


@pytest.fixture
def mock_workflow_router():
    """Mock workflow router for testing."""
    router = Mock()
    router.select_workflows = Mock(return_value=[
        WorkflowType.ARCHITECT,
        WorkflowType.IMPLEMENT,
        WorkflowType.TEST
    ])
    router.estimate_cost = Mock(return_value=25.50)
    router.estimate_duration = Mock(return_value=45)
    router.estimate_workflow_cost = Mock(return_value=15.0)
    return router


@pytest.fixture
def mock_approval_manager():
    """Mock approval manager for testing."""
    manager = AsyncMock()
    manager.should_request_approval = AsyncMock(return_value=False)
    manager.create_approval_request = AsyncMock(return_value="approval-123")
    manager.wait_for_approval = AsyncMock(return_value=True)
    return manager


@pytest.fixture
def mock_langgraph_state():
    """Mock LangGraph state for testing."""
    with patch('src.agents.pydanticai.genie.orchestrator.state.create_orchestration_graph') as mock_graph:
        mock_compiled_graph = AsyncMock()
        mock_compiled_graph.ainvoke = AsyncMock(return_value={
            "phase": EpicPhase.COMPLETE.value,
            "workflow_results": {},
            "cost_accumulated": 15.75
        })
        mock_graph.return_value = mock_compiled_graph
        yield mock_compiled_graph


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment between tests."""
    original_env = os.environ.copy()
    # Set test environment variables
    os.environ["TEST_MODE"] = "true"
    os.environ["DISABLE_EXTERNAL_APIS"] = "true"
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def mock_mcp_tools():
    """Mock MCP tools for testing."""
    return {
        "linear": Mock(),
        "slack": Mock(),
        "memory": Mock()
    }