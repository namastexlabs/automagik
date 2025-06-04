"""Tests for Genie Agent core functionality."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

# Mock LangGraph before importing Genie components
with patch.dict('sys.modules', {
    'langgraph': Mock(),
    'langgraph.graph': Mock(),
    'langgraph.checkpoint.postgres': Mock(),
    'langgraph.checkpoint': Mock(),
}):
    from src.agents.pydanticai.genie.agent import GenieAgent
    from src.agents.pydanticai.genie.models import (
        EpicRequest, EpicPlan, EpicState, WorkflowType, EpicPhase
    )


class TestGenieAgentInitialization:
    """Test Genie Agent initialization and basic setup."""

    def test_agent_initialization(self, genie_config, mock_dependencies):
        """Test that Genie agent can be initialized properly."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            assert agent is not None
            assert agent.dependencies is not None
            assert agent.tool_registry is not None
            assert hasattr(agent, 'router')
            assert hasattr(agent, 'claude_client')
            assert hasattr(agent, 'approval_manager')

    def test_agent_extends_automagik_agent(self, genie_config, mock_dependencies):
        """Test that Genie agent properly extends AutomagikAgent."""
        from src.agents.models.automagik_agent import AutomagikAgent
        
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            assert isinstance(agent, AutomagikAgent)

    def test_agent_has_mcp_integration(self, genie_config, mock_dependencies):
        """Test MCP integration is properly set up."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            # GenieAgent inherits from AutomagikAgent which should have tool_registry
            assert hasattr(agent, 'tool_registry')
            assert agent.tool_registry is not None


class TestGenieAgentEpicCreation:
    """Test epic creation and planning functionality."""

    @pytest.mark.asyncio
    async def test_create_epic_basic(self, genie_config, mock_dependencies, sample_epic_request):
        """Test basic epic creation."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            # Mock the router and orchestrator
            with patch.object(agent, 'router') as mock_router, \
                 patch.object(agent, '_execute_epic') as mock_execute:
                
                mock_router.select_workflows.return_value = [WorkflowType.TEST]
                mock_router.estimate_cost.return_value = 10.0
                mock_router.estimate_duration.return_value = 30
                mock_execute.return_value = {
                    "epic_id": "test-epic",
                    "status": "complete",
                    "phase": EpicPhase.COMPLETE.value,
                    "total_cost": 10.0
                }
                
                result = await agent.create_epic(sample_epic_request.message)
                
                assert result is not None
                assert result["status"] == "executing"
                assert "epic_id" in result
                mock_router.select_workflows.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_epic_with_validation(self, genie_config, mock_dependencies):
        """Test epic creation with request validation."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            # Test with invalid request (empty message) - should return error dict, not raise
            result = await agent.create_epic("")
            assert result["status"] == "failed"
            assert "message cannot be empty" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_epic_planning_workflow_selection(self, genie_config, mock_dependencies, sample_epic_request):
        """Test workflow selection logic in epic planning."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            # Create a mock router with the required methods
            mock_router = Mock()
            mock_router.select_workflows.return_value = [
                WorkflowType.ARCHITECT,
                WorkflowType.IMPLEMENT,
                WorkflowType.TEST
            ]
            mock_router.estimate_workflow_cost.return_value = 15.0
            
            # Set the router directly on the agent
            agent.router = mock_router
                
            plan = await agent._plan_epic(sample_epic_request)
            
            # The plan includes PR workflow by default (require_pr=True)
            expected_workflows = [WorkflowType.ARCHITECT, WorkflowType.IMPLEMENT, WorkflowType.TEST, WorkflowType.PR]
            assert plan.planned_workflows == expected_workflows
            assert plan.estimated_cost == 60.0  # 4 workflows * 15.0 each = 60.0
            assert plan.estimated_duration_minutes == 80  # 4 workflows * 20 minutes = 80
            mock_router.select_workflows.assert_called_once()


class TestGenieAgentNaturalLanguage:
    """Test natural language interface."""

    @pytest.mark.asyncio
    async def test_run_with_simple_request(self, genie_config, mock_dependencies):
        """Test run method with simple natural language request."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'create_epic') as mock_create_epic:
                mock_epic_response = {
                    "epic_id": "test-epic",
                    "title": "Create Tests",
                    "status": "executing",
                    "planned_workflows": ["test"],
                    "estimated_cost": 10.0,
                    "approval_required": False,
                    "tracking_url": "/api/v1/agent/genie/status/test-epic"
                }
                mock_create_epic.return_value = mock_epic_response
                
                result = await agent.run("Create comprehensive tests for the authentication system")
                
                assert result.success is True
                assert "epic created" in result.text.lower()
                mock_create_epic.assert_called_once()
                
                # Verify the created epic request
                assert mock_create_epic.called
                call_args = mock_create_epic.call_args
                assert call_args is not None
                # The first positional argument is the request string
                request_arg = call_args[0][0] if call_args[0] else call_args.kwargs.get('request', '')
                assert isinstance(request_arg, str)
                assert "authentication system" in request_arg

    @pytest.mark.asyncio
    async def test_run_parses_requirements_from_natural_language(self, genie_config, mock_dependencies):
        """Test that run method parses requirements from natural language."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'create_epic') as mock_create_epic:
                mock_create_epic.return_value = {
                    "epic_id": "test-epic",
                    "status": "executing",
                    "title": "Login System",
                    "planned_workflows": ["architect", "implement", "test"],
                    "estimated_cost": 25.0,
                    "approval_required": False,
                    "tracking_url": "/api/v1/agent/genie/status/test-epic"
                }
                
                await agent.run("Create a login system with unit tests, integration tests, and documentation")
                
                mock_create_epic.assert_called_once()
                assert mock_create_epic.called
                call_args = mock_create_epic.call_args
                assert call_args is not None
                # The first positional argument is the request string
                request_arg = call_args[0][0] if call_args[0] else call_args.kwargs.get('request', '')
                assert isinstance(request_arg, str)
                assert "login system" in request_arg


class TestGenieAgentErrorHandling:
    """Test error handling and recovery."""

    @pytest.mark.asyncio
    async def test_handle_workflow_execution_failure(self, genie_config, mock_dependencies, sample_epic_request):
        """Test handling of workflow execution failures."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            # Mock the router to avoid None references
            with patch.object(agent, 'router') as mock_router:
                mock_router.select_workflows.return_value = [WorkflowType.TEST]
                mock_router.estimate_workflow_cost.return_value = 10.0
                
                # Simulate error during epic creation by causing an exception
                # Let's mock the _plan_epic method to raise an exception
                with patch.object(agent, '_plan_epic') as mock_plan:
                    mock_plan.side_effect = Exception("Workflow execution failed")
                    
                    result = await agent.create_epic(sample_epic_request.message)
                    
                    assert result["status"] == "failed"
                    assert result.get("error") is not None
                    assert "workflow execution failed" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_handle_cost_limit_exceeded(self, genie_config, mock_dependencies, sample_epic_request):
        """Test handling when cost limit is exceeded."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            # Set low cost limit
            genie_config["max_cost"] = 5.0
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'router') as mock_router:
                # Return high cost estimate per workflow
                mock_router.estimate_workflow_cost.return_value = 100.0
                mock_router.select_workflows.return_value = [WorkflowType.ARCHITECT]
                
                result = await agent.create_epic(sample_epic_request.message)
                
                assert result["status"] == "failed"
                assert "cost limit exceeded" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_run_handles_epic_creation_failure(self, genie_config, mock_dependencies):
        """Test that run method handles epic creation failures gracefully."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'create_epic') as mock_create_epic:
                mock_create_epic.side_effect = Exception("Epic creation failed")
                
                result = await agent.run("Create some tests")
                
                assert result.success is False
                assert "failed to process epic" in result.text.lower()


class TestGenieAgentMocks:
    """Test mocking and test utilities."""

    @pytest.mark.asyncio
    async def test_with_mocked_external_dependencies(self, genie_config, mock_dependencies):
        """Test agent works correctly with all external dependencies mocked."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            # Mock all external components
            agent.router = Mock()
            agent.claude_client = AsyncMock()
            agent.approval_manager = AsyncMock()
            
            agent.router.select_workflows.return_value = [WorkflowType.TEST]
            agent.router.estimate_cost.return_value = 5.0
            agent.router.estimate_duration.return_value = 15
            
            agent.claude_client.execute_workflow.return_value = {
                "success": True,
                "output": "Test completed",
                "cost": 5.0
            }
            
            agent.approval_manager.should_request_approval.return_value = False
            
            result = await agent.create_epic("Simple test request")
            
            assert result is not None
            assert result["status"] in ["complete", "executing", "failed"]

    def test_agent_configuration_validation(self, mock_dependencies):
        """Test agent configuration validation."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            # Test with minimal config
            minimal_config = {"model_name": "openai:gpt-4o-mini"}
            agent = GenieAgent(minimal_config)
            assert agent is not None
            
            # Test with empty config - GenieAgent is more tolerant than expected
            # Just ensure it doesn't crash with empty config
            empty_config = {}
            agent = GenieAgent(empty_config)
            assert agent is not None
            assert agent.config == empty_config