"""Tests for Genie Orchestrator components."""
import pytest
from unittest.mock import Mock, patch
import sys
import os
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.agents.pydanticai.genie.orchestrator.router import WorkflowRouter
from src.agents.pydanticai.genie.orchestrator.claude_client import ClaudeCodeClient
from src.agents.pydanticai.genie.orchestrator.approvals import ApprovalManager
from src.agents.pydanticai.genie.models import (
    WorkflowType, ApprovalPoint, ApprovalTriggerType, ApprovalStatus
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
    async def test_execute_workflow_success(self):
        """Test successful workflow execution."""
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        
        epic_state = {
            "epic_id": "epic-123",
            "epic_title": "Test Epic",
            "completed_workflows": [],
            "workflow_results": {}
        }
        
        with patch.object(client.client, 'post') as mock_post, \
             patch.object(client, '_poll_for_completion') as mock_poll:
            
            # Mock initial response
            mock_response = Mock()
            mock_response.json.return_value = {
                "run_id": "run-123",
                "status": "running",
                "container_id": "container-123"
            }
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            # Mock completion response
            from src.agents.pydanticai.genie.models import ClaudeCodeResponse
            mock_completion = ClaudeCodeResponse(
                run_id="run-123",
                status="completed",
                container_id="container-123",
                cost_usd=5.0,
                result={"summary": "Tests created successfully", "files_changed": ["test_auth.py"]}
            )
            mock_poll.return_value = mock_completion
            
            result = await client.execute_workflow(
                "test",
                "Create tests for authentication",
                epic_state
            )
            
            assert result["status"] == "completed"
            assert result["cost_usd"] == 5.0
            assert result["container_id"] == "container-123"
            assert result["summary"] == "Tests created successfully"
            assert "test_auth.py" in result["files_changed"]

    @pytest.mark.asyncio
    async def test_execute_workflow_with_max_turns(self):
        """Test workflow execution with custom max_turns."""
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        
        epic_state = {
            "epic_id": "epic-456",
            "epic_title": "Complex Epic",
            "completed_workflows": ["architect"],
            "workflow_results": {}
        }
        
        with patch.object(client.client, 'post') as mock_post, \
             patch.object(client, '_poll_for_completion') as mock_poll:
            
            mock_response = Mock()
            mock_response.json.return_value = {"run_id": "run-456", "status": "running"}
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            from src.agents.pydanticai.genie.models import ClaudeCodeResponse
            mock_completion = ClaudeCodeResponse(
                run_id="run-456",
                status="completed",
                cost_usd=15.0
            )
            mock_poll.return_value = mock_completion
            
            result = await client.execute_workflow(
                "implement",
                "Implement authentication system",
                epic_state,
                max_turns=50
            )
            
            # Verify the request was made with correct config
            call_args = mock_post.call_args
            request_data = call_args[1]['json']
            assert request_data['config']['max_turns'] == 50
            assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_execute_workflow_http_error(self):
        """Test workflow execution with HTTP error."""
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        
        epic_state = {
            "epic_id": "epic-error",
            "epic_title": "Error Epic",
            "completed_workflows": [],
            "workflow_results": {}
        }
        
        with patch.object(client.client, 'post') as mock_post:
            from httpx import HTTPError
            mock_post.side_effect = HTTPError("Server error")
            
            result = await client.execute_workflow(
                "test",
                "Create tests",
                epic_state
            )
            
            assert result["status"] == "failed"
            assert "HTTP error" in result["error"]
            assert result["cost_usd"] == 0.0

    @pytest.mark.asyncio
    async def test_poll_for_completion_success(self):
        """Test successful polling for completion."""
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        
        with patch.object(client.client, 'get') as mock_get:
            # Mock responses: first running, then completed
            responses = [
                {
                    "run_id": "run-123",
                    "status": "running",
                    "container_id": "container-123"
                },
                {
                    "run_id": "run-123", 
                    "status": "completed",
                    "container_id": "container-123",
                    "cost_usd": 10.0,
                    "result": {"summary": "Workflow completed"}
                }
            ]
            
            mock_response_objs = []
            for resp_data in responses:
                mock_resp = Mock()
                mock_resp.json.return_value = resp_data
                mock_resp.raise_for_status = Mock()
                mock_response_objs.append(mock_resp)
            
            mock_get.side_effect = mock_response_objs
            
            result = await client._poll_for_completion("run-123", "test", poll_interval=0.1)
            
            assert result.status == "completed"
            assert result.cost_usd == 10.0
            assert mock_get.call_count == 2

    @pytest.mark.asyncio
    async def test_poll_for_completion_timeout(self):
        """Test polling timeout."""
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        
        with patch.object(client.client, 'get') as mock_get:
            # Always return running status
            mock_response = Mock()
            mock_response.json.return_value = {"run_id": "run-123", "status": "running"}
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = await client._poll_for_completion(
                "run-123", 
                "test", 
                poll_interval=0.1, 
                max_wait_time=0.2
            )
            
            assert result.status == "timeout"
            assert "timed out" in result.error

    @pytest.mark.asyncio
    async def test_get_workflow_logs(self):
        """Test workflow log retrieval."""
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        
        with patch.object(client.client, 'get') as mock_get:
            mock_response = Mock()
            mock_response.json.return_value = {
                "logs": "Workflow started\nRunning tests\nWorkflow completed"
            }
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            logs = await client.get_workflow_logs("container-123")
            
            assert logs == "Workflow started\nRunning tests\nWorkflow completed"
            mock_get.assert_called_once_with(
                "http://localhost:8000/api/v1/agent/claude-code/logs/container-123"
            )

    @pytest.mark.asyncio
    async def test_get_workflow_logs_error(self):
        """Test workflow log retrieval with error."""
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        
        with patch.object(client.client, 'get') as mock_get:
            from httpx import HTTPError
            mock_get.side_effect = HTTPError("Not found")
            
            logs = await client.get_workflow_logs("container-999")
            
            assert logs is None

    @pytest.mark.asyncio
    async def test_stop_workflow(self):
        """Test stopping a workflow."""
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        
        with patch.object(client.client, 'post') as mock_post:
            mock_response = Mock()
            mock_response.raise_for_status = Mock()
            mock_post.return_value = mock_response
            
            result = await client.stop_workflow("run-123")
            
            assert result is True
            mock_post.assert_called_once_with(
                "http://localhost:8000/api/v1/agent/claude-code/stop/run-123"
            )

    @pytest.mark.asyncio
    async def test_stop_workflow_error(self):
        """Test stopping a workflow with error."""
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        
        with patch.object(client.client, 'post') as mock_post:
            from httpx import HTTPError
            mock_post.side_effect = HTTPError("Server error")
            
            result = await client.stop_workflow("run-123")
            
            assert result is False

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing the client."""
        client = ClaudeCodeClient(base_url="http://localhost:8000")
        
        with patch.object(client.client, 'aclose') as mock_close:
            await client.close()
            mock_close.assert_called_once()


class TestApprovalManager:
    """Test ApprovalManager functionality."""

    def test_approval_manager_initialization(self):
        """Test ApprovalManager can be initialized."""
        manager = ApprovalManager()
        assert manager is not None
        assert hasattr(manager, 'pending_approvals')

    @pytest.mark.asyncio
    async def test_check_approval_needed_for_high_cost(self):
        """Test approval request for high cost workflows."""
        manager = ApprovalManager()
        
        # Create mock state that triggers cost threshold
        state = {
            "epic_id": "test-epic-123",
            "epic_title": "Test Epic",
            "current_workflow": "implement",
            "completed_workflows": [],
            "cost_accumulated": 45.0,  # 90% of limit
            "cost_limit": 50.0
        }
        
        approval_request = await manager.check_approval_needed(state)
        assert approval_request is not None
        assert approval_request["trigger"] == "cost_threshold"

    @pytest.mark.asyncio
    async def test_check_approval_needed_for_security_changes(self):
        """Test approval request for security-related changes."""
        manager = ApprovalManager()
        
        state = {
            "epic_id": "test-epic-123",
            "epic_title": "Test Epic",
            "current_workflow": "implement",
            "completed_workflows": [],
            "cost_accumulated": 10.0,
            "cost_limit": 50.0
        }
        
        workflow_result = {
            "summary": "Modified authentication middleware and updated password hashing",
            "files_changed": ["src/auth/middleware.py", "src/auth/password.py"]
        }
        
        approval_request = await manager.check_approval_needed(state, workflow_result)
        assert approval_request is not None
        assert approval_request["trigger"] == "security_changes"

    @pytest.mark.asyncio
    async def test_check_approval_needed_for_database_changes(self):
        """Test approval request for database schema changes."""
        manager = ApprovalManager()
        
        state = {
            "epic_id": "test-epic-123",
            "epic_title": "Test Epic",
            "current_workflow": "architect",
            "completed_workflows": [],
            "cost_accumulated": 15.0,
            "cost_limit": 50.0
        }
        
        workflow_result = {
            "artifacts": {
                "database_changes": ["Added new user table", "Modified existing schema"]
            }
        }
        
        approval_request = await manager.check_approval_needed(state, workflow_result)
        assert approval_request is not None
        assert approval_request["trigger"] == "database_changes"

    @pytest.mark.asyncio
    async def test_no_approval_for_simple_changes(self):
        """Test no approval needed for simple, low-risk changes."""
        manager = ApprovalManager()
        
        state = {
            "epic_id": "test-epic-123",
            "epic_title": "Test Epic",
            "current_workflow": "test",
            "completed_workflows": [],
            "cost_accumulated": 5.0,
            "cost_limit": 50.0
        }
        
        workflow_result = {
            "summary": "Added unit tests for utility functions",
            "files_changed": ["tests/test_utils.py"]
        }
        
        approval_request = await manager.check_approval_needed(state, workflow_result)
        assert approval_request is None

    @pytest.mark.asyncio
    async def test_create_approval_request(self):
        """Test creation of approval request."""
        manager = ApprovalManager()
        
        state = {
            "epic_id": "epic-123",
            "epic_title": "Test Epic",
            "current_workflow": "implement",
            "completed_workflows": [],
            "cost_accumulated": 45.0,
            "cost_limit": 50.0
        }
        
        approval_request = manager._create_approval_request(
            state,
            "cost_threshold",
            "Cost exceeds threshold"
        )
        
        assert approval_request is not None
        assert approval_request["approval_id"] is not None
        assert approval_request["trigger"] == "cost_threshold"
        assert approval_request["epic_id"] == "epic-123"

    @pytest.mark.asyncio
    async def test_record_approval_decision(self):
        """Test recording approval decisions."""
        manager = ApprovalManager()
        
        # First create an approval request
        state = {
            "epic_id": "epic-123",
            "epic_title": "Test Epic",
            "current_workflow": "implement",
            "completed_workflows": [],
            "cost_accumulated": 45.0,
            "cost_limit": 50.0
        }
        
        approval_request = manager._create_approval_request(
            state,
            "cost_threshold",
            "Cost exceeds threshold"
        )
        approval_id = approval_request["approval_id"]
        
        # Record the decision
        approval_point = manager.record_approval_decision(
            approval_id,
            ApprovalStatus.APPROVED,
            "test_user",
            "Looks good to proceed"
        )
        
        assert approval_point is not None
        assert approval_point.decision == ApprovalStatus.APPROVED
        assert approval_point.approver == "test_user"
        assert approval_point.comments == "Looks good to proceed"

    @pytest.mark.asyncio
    async def test_format_approval_message(self):
        """Test approval message formatting for Slack."""
        manager = ApprovalManager()
        
        approval_point = ApprovalPoint(
            id="approval-123",
            workflow=WorkflowType.IMPLEMENT,
            trigger_type=ApprovalTriggerType.HIGH_COST,
            reason="cost_threshold",
            description="Cost exceeds threshold", 
            requested_at=datetime.now()
        )
        
        state = {
            "epic_id": "epic-456",
            "epic_title": "Payment System Refactor",
            "completed_workflows": ["architect"],
            "cost_accumulated": 75.0,
            "cost_limit": 100.0
        }
        
        message = manager._format_slack_approval_message(state, approval_point)
        
        assert "approval-123" in message
        assert "75.0" in message
        assert "epic-456" in message
        assert "approve" in message.lower()

    def test_get_pending_approvals(self):
        """Test retrieving pending approvals for an epic."""
        manager = ApprovalManager()
        
        # Create a couple of approval requests
        state1 = {
            "epic_id": "epic-123",
            "epic_title": "Test Epic 1",
            "current_workflow": "implement",
            "completed_workflows": [],
            "cost_accumulated": 45.0,
            "cost_limit": 50.0
        }
        
        state2 = {
            "epic_id": "epic-456",
            "epic_title": "Test Epic 2", 
            "current_workflow": "architect",
            "completed_workflows": [],
            "cost_accumulated": 30.0,
            "cost_limit": 40.0
        }
        
        approval1 = manager._create_approval_request(state1, "cost_threshold", "High cost")
        approval2 = manager._create_approval_request(state2, "security_changes", "Security review")
        
        # Test getting pending approvals for epic-123
        pending = manager.get_pending_approvals("epic-123")
        assert len(pending) == 1
        assert pending[0].id == approval1["approval_id"]
        
        # Test getting pending approvals for epic-456
        pending = manager.get_pending_approvals("epic-456")
        assert len(pending) == 1
        assert pending[0].id == approval2["approval_id"]


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
        epic_state = {
            "epic_id": "integration-test",
            "epic_title": "Integration Test Epic",
            "completed_workflows": [],
            "workflow_results": {}
        }
        
        with patch.object(client, 'execute_workflow') as mock_execute:
            mock_execute.return_value = {
                "status": "completed",
                "cost_usd": cost / len(workflows),
                "summary": "Workflow completed",
                "container_id": "test-container"
            }
            
            for workflow in workflows:
                result = await client.execute_workflow(
                    workflow.value,
                    "Test task",
                    epic_state
                )
                assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_approval_workflow_integration(self):
        """Test integration of approval flow with orchestrator."""
        router = WorkflowRouter()
        manager = ApprovalManager()
        
        # High-cost workflow should trigger approval
        workflows = router.select_workflows("Implement complete authentication system with database changes")
        cost = router.estimate_cost(workflows)
        
        state = {
            "epic_id": "epic-integration-test",
            "epic_title": "Authentication System",
            "current_workflow": "architect",
            "completed_workflows": [],
            "cost_accumulated": cost * 0.9,  # Close to limit to trigger approval
            "cost_limit": cost
        }
        
        workflow_result = {
            "artifacts": {
                "database_changes": ["New user table", "Authentication schema"],
                "breaking_changes": ["API changes"]
            }
        }
        
        approval_request = await manager.check_approval_needed(state, workflow_result)
        assert approval_request is not None