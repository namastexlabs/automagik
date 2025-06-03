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
            assert hasattr(agent, '_load_mcp_servers')
            assert callable(getattr(agent, '_load_mcp_servers'))


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
                mock_execute.return_value = EpicState(
                    epic_id="test-epic",
                    request=sample_epic_request,
                    plan=EpicPlan(
                        workflows=[WorkflowType.TEST],
                        estimated_cost=10.0,
                        estimated_duration_minutes=30,
                        dependencies=[],
                        risk_factors=[],
                        success_criteria=[]
                    ),
                    phase=EpicPhase.COMPLETE,
                    current_workflow=None,
                    workflow_results=[],
                    approval_points=[],
                    rollback_points=[],
                    total_cost=10.0,
                    start_time=None,
                    completion_time=None,
                    error_message=None
                )
                
                result = await agent.create_epic(sample_epic_request)
                
                assert result is not None
                assert result.phase == EpicPhase.COMPLETE
                assert result.total_cost == 10.0
                mock_router.select_workflows.assert_called_once()
                mock_execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_epic_with_validation(self, genie_config, mock_dependencies):
        """Test epic creation with request validation."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            # Test with invalid request (empty description)
            invalid_request = EpicRequest(
                description="",
                requirements=[],
                acceptance_criteria=[]
            )
            
            with pytest.raises(ValueError, match="description cannot be empty"):
                await agent.create_epic(invalid_request)

    @pytest.mark.asyncio
    async def test_epic_planning_workflow_selection(self, genie_config, mock_dependencies, sample_epic_request):
        """Test workflow selection logic in epic planning."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'router') as mock_router:
                mock_router.select_workflows.return_value = [
                    WorkflowType.ARCHITECT,
                    WorkflowType.IMPLEMENT,
                    WorkflowType.TEST
                ]
                mock_router.estimate_cost.return_value = 45.0
                mock_router.estimate_duration.return_value = 90
                
                plan = await agent._plan_epic(sample_epic_request)
                
                assert plan.workflows == [WorkflowType.ARCHITECT, WorkflowType.IMPLEMENT, WorkflowType.TEST]
                assert plan.estimated_cost == 45.0
                assert plan.estimated_duration_minutes == 90
                mock_router.select_workflows.assert_called_once_with(sample_epic_request.description)


class TestGenieAgentNaturalLanguage:
    """Test natural language interface."""

    @pytest.mark.asyncio
    async def test_run_with_simple_request(self, genie_config, mock_dependencies):
        """Test run method with simple natural language request."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'create_epic') as mock_create_epic:
                mock_epic_state = EpicState(
                    epic_id="test-epic",
                    request=EpicRequest(
                        description="Create tests",
                        requirements=["Unit tests"],
                        acceptance_criteria=["Tests pass"]
                    ),
                    plan=EpicPlan(
                        workflows=[WorkflowType.TEST],
                        estimated_cost=10.0,
                        estimated_duration_minutes=30,
                        dependencies=[],
                        risk_factors=[],
                        success_criteria=[]
                    ),
                    phase=EpicPhase.COMPLETE,
                    current_workflow=None,
                    workflow_results=[],
                    approval_points=[],
                    rollback_points=[],
                    total_cost=10.0,
                    start_time=None,
                    completion_time=None,
                    error_message=None
                )
                mock_create_epic.return_value = mock_epic_state
                
                result = await agent.run("Create comprehensive tests for the authentication system")
                
                assert result.success is True
                assert "epic completed successfully" in result.text.lower()
                mock_create_epic.assert_called_once()
                
                # Verify the created epic request
                call_args = mock_create_epic.call_args[0][0]
                assert isinstance(call_args, EpicRequest)
                assert "authentication system" in call_args.description

    @pytest.mark.asyncio
    async def test_run_parses_requirements_from_natural_language(self, genie_config, mock_dependencies):
        """Test that run method parses requirements from natural language."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'create_epic') as mock_create_epic:
                mock_create_epic.return_value = Mock(phase=EpicPhase.COMPLETE)
                
                await agent.run("Create a login system with unit tests, integration tests, and documentation")
                
                mock_create_epic.assert_called_once()
                call_args = mock_create_epic.call_args[0][0]
                
                assert isinstance(call_args, EpicRequest)
                assert "login system" in call_args.description
                assert len(call_args.requirements) > 0
                assert any("unit tests" in req.lower() for req in call_args.requirements)


class TestGenieAgentErrorHandling:
    """Test error handling and recovery."""

    @pytest.mark.asyncio
    async def test_handle_workflow_execution_failure(self, genie_config, mock_dependencies, sample_epic_request):
        """Test handling of workflow execution failures."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'claude_client') as mock_client:
                mock_client.execute_workflow.side_effect = Exception("Workflow execution failed")
                
                with patch.object(agent, 'router') as mock_router:
                    mock_router.select_workflows.return_value = [WorkflowType.TEST]
                    mock_router.estimate_cost.return_value = 10.0
                    mock_router.estimate_duration.return_value = 30
                    
                    result = await agent.create_epic(sample_epic_request)
                    
                    assert result.phase == EpicPhase.FAILED
                    assert result.error_message is not None
                    assert "workflow execution failed" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_handle_cost_limit_exceeded(self, genie_config, mock_dependencies, sample_epic_request):
        """Test handling when cost limit is exceeded."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            # Set low cost limit
            genie_config["max_cost"] = 5.0
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'router') as mock_router:
                # Return high cost estimate
                mock_router.estimate_cost.return_value = 100.0
                mock_router.select_workflows.return_value = [WorkflowType.ARCHITECT]
                
                result = await agent.create_epic(sample_epic_request)
                
                assert result.phase == EpicPhase.FAILED
                assert "cost limit exceeded" in result.error_message.lower()

    @pytest.mark.asyncio
    async def test_run_handles_epic_creation_failure(self, genie_config, mock_dependencies):
        """Test that run method handles epic creation failures gracefully."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'create_epic') as mock_create_epic:
                mock_create_epic.side_effect = Exception("Epic creation failed")
                
                result = await agent.run("Create some tests")
                
                assert result.success is False
                assert "error creating epic" in result.text.lower()


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
            
            request = EpicRequest(
                description="Simple test request",
                requirements=["Basic test"],
                acceptance_criteria=["Test passes"]
            )
            
            result = await agent.create_epic(request)
            
            assert result is not None
            assert result.phase in [EpicPhase.COMPLETE, EpicPhase.EXECUTING]

    def test_agent_configuration_validation(self, mock_dependencies):
        """Test agent configuration validation."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            # Test with minimal config
            minimal_config = {"model_name": "openai:gpt-4o-mini"}
            agent = GenieAgent(minimal_config)
            assert agent is not None
            
            # Test with invalid config
            with pytest.raises((ValueError, KeyError)):
                invalid_config = {}
                GenieAgent(invalid_config)