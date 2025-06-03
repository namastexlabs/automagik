"""Tests for Genie Orchestrator components."""
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.agents.pydanticai.genie.orchestrator.router import WorkflowRouter
from src.agents.pydanticai.genie.orchestrator.claude_client import ClaudeCodeClient
from src.agents.pydanticai.genie.orchestrator.approvals import ApprovalManager
from src.agents.pydanticai.genie.models import (
    WorkflowType, EpicRequest, ApprovalPoint, ApprovalTriggerType
)


class TestWorkflowRouter:
    """Test WorkflowRouter functionality."""

    def test_router_initialization(self):
        """Test WorkflowRouter can be initialized."""
        router = WorkflowRouter()
        assert router is not None
        assert hasattr(router, 'workflow_patterns')
        assert hasattr(router, 'cost_estimates')

    def test_select_workflows_for_testing_request(self):
        """Test workflow selection for testing-related requests."""
        router = WorkflowRouter()
        
        test_requests = [
            "Create comprehensive tests for the authentication system",
            "Add unit tests for the payment processor",
            "Write integration tests for the API endpoints"
        ]
        
        for request in test_requests:
            workflows = router.select_workflows(request)
            assert WorkflowType.TEST in workflows
            assert len(workflows) >= 1

    def test_select_workflows_for_implementation_request(self):
        """Test workflow selection for implementation requests."""
        router = WorkflowRouter()
        
        impl_requests = [
            "Implement a new user registration system",
            "Build a payment processing module", 
            "Create a REST API for user management"
        ]
        
        for request in impl_requests:
            workflows = router.select_workflows(request)
            assert WorkflowType.IMPLEMENT in workflows
            # Should likely include architecture planning
            assert WorkflowType.ARCHITECT in workflows

    def test_select_workflows_for_documentation_request(self):
        """Test workflow selection for documentation requests."""
        router = WorkflowRouter()
        
        doc_requests = [
            "Create documentation for the API",
            "Write user guide for the application",
            "Document the deployment process"
        ]
        
        for request in doc_requests:
            workflows = router.select_workflows(request)
            assert WorkflowType.DOCUMENT in workflows

    def test_select_workflows_for_complex_request(self):
        """Test workflow selection for complex multi-step requests."""
        router = WorkflowRouter()
        
        complex_request = "Design and implement a complete user authentication system with tests and documentation"
        workflows = router.select_workflows(complex_request)
        
        # Should include multiple workflow types
        assert len(workflows) >= 3
        assert WorkflowType.ARCHITECT in workflows
        assert WorkflowType.IMPLEMENT in workflows
        assert WorkflowType.TEST in workflows
        assert WorkflowType.DOCUMENT in workflows

    def test_estimate_cost_calculation(self):
        """Test cost estimation for different workflow combinations."""
        router = WorkflowRouter()
        
        # Single workflow
        single_workflow = [WorkflowType.TEST]
        cost = router.estimate_cost(single_workflow)
        assert cost > 0
        assert cost < 50  # Reasonable upper bound
        
        # Multiple workflows should cost more
        multiple_workflows = [WorkflowType.ARCHITECT, WorkflowType.IMPLEMENT, WorkflowType.TEST]
        multi_cost = router.estimate_cost(multiple_workflows)
        assert multi_cost > cost
        assert multi_cost > 0

    def test_estimate_duration_calculation(self):
        """Test duration estimation for workflows."""
        router = WorkflowRouter()
        
        workflows = [WorkflowType.TEST, WorkflowType.DOCUMENT]
        duration = router.estimate_duration(workflows)
        
        assert duration > 0
        assert duration < 500  # Reasonable upper bound in minutes
        assert isinstance(duration, (int, float))

    def test_workflow_ordering_logic(self):
        """Test that workflows are ordered logically."""
        router = WorkflowRouter()
        
        request = "Build and test a new feature"
        workflows = router.select_workflows(request)
        
        # Architecture should come before implementation
        if WorkflowType.ARCHITECT in workflows and WorkflowType.IMPLEMENT in workflows:
            arch_idx = workflows.index(WorkflowType.ARCHITECT)
            impl_idx = workflows.index(WorkflowType.IMPLEMENT)
            assert arch_idx < impl_idx
        
        # Implementation should come before testing
        if WorkflowType.IMPLEMENT in workflows and WorkflowType.TEST in workflows:
            impl_idx = workflows.index(WorkflowType.IMPLEMENT)
            test_idx = workflows.index(WorkflowType.TEST)
            assert impl_idx < test_idx


class TestClaudeCodeClient:
    """Test ClaudeCodeClient functionality."""

    def test_client_initialization(self):
        """Test ClaudeCodeClient can be initialized."""
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        assert client is not None
        assert client.base_url == "http://localhost:8000"

    @pytest.mark.asyncio
    async def test_create_container(self):
        """Test container creation."""
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "container_id": "test-container-123",
                "status": "created"
            }
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            result = await client.create_container(WorkflowType.TEST, "test-project")
            
            assert result["container_id"] == "test-container-123"
            assert result["status"] == "created"
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_workflow(self):
        """Test workflow execution."""
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        
        with patch.object(client, 'create_container') as mock_create, \
             patch.object(client, '_poll_workflow_completion') as mock_poll, \
             patch.object(client, 'get_container_logs') as mock_logs:
            
            mock_create.return_value = {"container_id": "test-123"}
            mock_poll.return_value = {"success": True, "cost": 5.0}
            mock_logs.return_value = ["Workflow completed successfully"]
            
            result = await client.execute_workflow(
                WorkflowType.TEST,
                "Create tests for authentication",
                {"project": "test-project"}
            )
            
            assert result["success"] is True
            assert result["cost"] == 5.0
            mock_create.assert_called_once()
            mock_poll.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_workflow_timeout(self):
        """Test workflow execution timeout handling."""
        client = ClaudeCodeClient(base_url="http://localhost:8000", timeout_minutes=1)
        
        with patch.object(client, 'create_container') as mock_create, \
             patch.object(client, '_poll_workflow_completion') as mock_poll:
            
            mock_create.return_value = {"container_id": "test-123"}
            mock_poll.side_effect = asyncio.TimeoutError("Workflow timed out")
            
            result = await client.execute_workflow(
                WorkflowType.IMPLEMENT,
                "Long running task",
                {}
            )
            
            assert result["success"] is False
            assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_get_container_logs(self):
        """Test container log retrieval."""
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.json.return_value = {
                "logs": ["Log line 1", "Log line 2", "Workflow completed"]
            }
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            logs = await client.get_container_logs("test-container-123")
            
            assert len(logs) == 3
            assert "Workflow completed" in logs
            mock_get.assert_called_once()


class TestApprovalManager:
    """Test ApprovalManager functionality."""

    def test_approval_manager_initialization(self):
        """Test ApprovalManager can be initialized."""
        manager = ApprovalManager()
        assert manager is not None
        assert hasattr(manager, 'approval_triggers')

    @pytest.mark.asyncio
    async def test_should_request_approval_for_high_cost(self):
        """Test approval request for high cost workflows."""
        manager = ApprovalManager(cost_threshold=25.0)
        
        workflow_result = {
            "workflow_type": WorkflowType.IMPLEMENT,
            "estimated_cost": 50.0,
            "changes": ["Created new authentication module"],
            "files_modified": ["src/auth/authenticator.py"]
        }
        
        should_approve = await manager.should_request_approval(workflow_result)
        assert should_approve is True

    @pytest.mark.asyncio
    async def test_should_request_approval_for_security_changes(self):
        """Test approval request for security-related changes."""
        manager = ApprovalManager()
        
        workflow_result = {
            "workflow_type": WorkflowType.IMPLEMENT,
            "estimated_cost": 10.0,
            "changes": ["Modified authentication middleware", "Updated password hashing"],
            "files_modified": ["src/auth/middleware.py", "src/auth/password.py"]
        }
        
        should_approve = await manager.should_request_approval(workflow_result)
        assert should_approve is True

    @pytest.mark.asyncio
    async def test_should_request_approval_for_database_changes(self):
        """Test approval request for database schema changes."""
        manager = ApprovalManager()
        
        workflow_result = {
            "workflow_type": WorkflowType.IMPLEMENT,
            "estimated_cost": 15.0,
            "changes": ["Added new user table", "Modified existing schema"],
            "files_modified": ["migrations/001_add_users.sql"]
        }
        
        should_approve = await manager.should_request_approval(workflow_result)
        assert should_approve is True

    @pytest.mark.asyncio
    async def test_no_approval_for_simple_changes(self):
        """Test no approval needed for simple, low-risk changes."""
        manager = ApprovalManager(cost_threshold=25.0)
        
        workflow_result = {
            "workflow_type": WorkflowType.TEST,
            "estimated_cost": 5.0,
            "changes": ["Added unit tests for utility functions"],
            "files_modified": ["tests/test_utils.py"]
        }
        
        should_approve = await manager.should_request_approval(workflow_result)
        assert should_approve is False

    @pytest.mark.asyncio
    async def test_create_approval_request(self):
        """Test creation of approval request."""
        manager = ApprovalManager()
        
        workflow_result = {
            "workflow_type": WorkflowType.IMPLEMENT,
            "estimated_cost": 45.0,
            "changes": ["Implemented new payment system"],
            "files_modified": ["src/payments/processor.py"]
        }
        
        approval_id = await manager.create_approval_request(
            epic_id="epic-123",
            workflow_result=workflow_result,
            trigger_type=ApprovalTriggerType.HIGH_COST
        )
        
        assert approval_id is not None
        assert isinstance(approval_id, str)
        assert len(approval_id) > 0

    @pytest.mark.asyncio
    async def test_wait_for_approval_timeout(self):
        """Test approval waiting with timeout."""
        manager = ApprovalManager()
        
        # Mock the approval waiting to timeout
        with patch.object(manager, '_check_approval_status') as mock_check:
            mock_check.return_value = None  # No approval yet
            
            result = await manager.wait_for_approval("approval-123", timeout_minutes=0.01)
            assert result is False

    @pytest.mark.asyncio
    async def test_format_approval_message(self):
        """Test approval message formatting for Slack."""
        manager = ApprovalManager()
        
        approval_point = ApprovalPoint(
            approval_id="approval-123",
            epic_id="epic-456",
            trigger_type=ApprovalTriggerType.HIGH_COST,
            workflow_type=WorkflowType.IMPLEMENT,
            estimated_cost=75.0,
            reason="Cost exceeds threshold",
            workflow_details={
                "changes": ["Major refactoring of payment system"],
                "files_modified": ["src/payments/"]
            },
            requested_at=None,
            approved_at=None,
            approved_by=None,
            approved=None
        )
        
        message = manager.format_approval_message(approval_point)
        
        assert "approval-123" in message
        assert "75.0" in message
        assert "payment system" in message.lower()
        assert "approve" in message.lower()


class TestOrchestratorIntegration:
    """Test integration between orchestrator components."""

    @pytest.mark.asyncio
    async def test_router_client_integration(self):
        """Test integration between router and client."""
        router = WorkflowRouter()
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        
        # Plan workflows
        workflows = router.select_workflows("Create comprehensive tests")
        cost = router.estimate_cost(workflows)
        
        assert len(workflows) > 0
        assert cost > 0
        
        # Mock client execution
        with patch.object(client, 'execute_workflow') as mock_execute:
            mock_execute.return_value = {
                "success": True,
                "cost": cost / len(workflows),
                "output": "Workflow completed"
            }
            
            for workflow in workflows:
                result = await client.execute_workflow(
                    workflow,
                    "Test task",
                    {"context": "test"}
                )
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_approval_workflow_integration(self):
        """Test integration of approval flow with orchestrator."""
        router = WorkflowRouter()
        manager = ApprovalManager(cost_threshold=20.0)
        
        # High-cost workflow should trigger approval
        workflows = router.select_workflows("Implement complete authentication system with database changes")
        cost = router.estimate_cost(workflows)
        
        if cost > 20.0:
            workflow_result = {
                "workflow_type": WorkflowType.IMPLEMENT,
                "estimated_cost": cost,
                "changes": ["Database schema changes", "Authentication implementation"],
                "files_modified": ["src/auth/", "migrations/"]
            }
            
            should_approve = await manager.should_request_approval(workflow_result)
            assert should_approve is True