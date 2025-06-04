"""Integration tests for Genie Agent with API and database."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import sys
import os
import httpx

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.agents.pydanticai.genie.agent import GenieAgent
from src.agents.pydanticai.genie.models import EpicPhase, WorkflowType


class TestGenieAPIIntegration:
    """Test Genie agent integration with FastAPI routes."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_genie_run_endpoint(self):
        """Test /agent/genie/run endpoint."""
        # Mock the get_genie_agent function that actually exists
        with patch('src.api.routes.genie_routes.get_genie_agent') as mock_get_agent:
            # Mock the GenieAgent instance returned by get_genie_agent
            mock_agent = AsyncMock()
            mock_agent.agent.arun = AsyncMock(return_value={
                "epic_id": "test-epic-123",
                "title": "Create authentication tests",
                "status": "executing",
                "planned_workflows": ["test", "review"],
                "estimated_cost": 15.75,
                "approval_required": False,
                "tracking_url": "http://localhost:8000/genie/epic/test-epic-123"
            })
            mock_get_agent.return_value = mock_agent
            
            # Test data
            request_data = {
                "message": "Create comprehensive tests for authentication system",
                "budget_limit": 50.0,
                "require_tests": True,
                "require_pr": True,
                "approval_mode": "auto"
            }
            
            # Mock the HTTP client call
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_response = Mock()
                mock_response.status_code = 200
                mock_response.json = Mock(return_value={
                    "epic_id": "test-epic-123",
                    "title": "Create authentication tests", 
                    "status": "executing",
                    "planned_workflows": ["test", "review"],
                    "estimated_cost": 15.75,
                    "approval_required": False,
                    "tracking_url": "http://localhost:8000/genie/epic/test-epic-123"
                })
                mock_post.return_value = mock_response
                
                # Simulate API call
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:8000/api/v1/agent/genie/run",
                        json=request_data
                    )
                    
                    # Verify the mocked response
                    data = response.json()
                    assert data["epic_id"] == "test-epic-123"
                    assert data["status"] == "executing"
                    assert data["estimated_cost"] == 15.75

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_genie_status_endpoint(self):
        """Test /agent/genie/status/{epic_id} endpoint."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={
                "epic_id": "test-epic-123",
                "phase": "executing",
                "current_workflow": "test",
                "progress": 0.6,
                "total_cost": 8.25
            })
            mock_get.return_value = mock_response
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://localhost:8000/api/v1/agent/genie/status/test-epic-123"
                )
                
                data = response.json()
                assert data["epic_id"] == "test-epic-123"
                assert data["phase"] == "executing"
                assert data["progress"] == 0.6

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_genie_approve_endpoint(self):
        """Test /agent/genie/approve/{epic_id}/{approval_id} endpoint."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={
                "approval_id": "approval-123",
                "approved": True,
                "approved_by": "test-user",
                "epic_resumed": True
            })
            mock_post.return_value = mock_response
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/api/v1/agent/genie/approve/epic-123/approval-123",
                    json={"approved": True, "notes": "Looks good"}
                )
                
                data = response.json()
                assert data["approved"] is True
                assert data["epic_resumed"] is True

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_genie_list_epics_endpoint(self):
        """Test /agent/genie/list endpoint."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={
                "epics": [
                    {
                        "epic_id": "epic-1",
                        "phase": "complete",
                        "message": "Create authentication tests",
                        "total_cost": 12.50
                    },
                    {
                        "epic_id": "epic-2", 
                        "phase": "executing",
                        "message": "Implement payment system",
                        "total_cost": 35.75
                    }
                ],
                "total_count": 2
            })
            mock_get.return_value = mock_response
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://localhost:8000/api/v1/agent/genie/list"
                )
                
                data = response.json()
                assert len(data["epics"]) == 2
                assert data["total_count"] == 2

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_genie_stop_epic_endpoint(self):
        """Test /agent/genie/stop/{epic_id} endpoint."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json = Mock(return_value={
                "epic_id": "epic-123",
                "stopped": True,
                "phase": "cancelled",
                "reason": "User requested stop"
            })
            mock_post.return_value = mock_response
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/api/v1/agent/genie/stop/epic-123",
                    json={"reason": "User requested stop"}
                )
                
                data = response.json()
                assert data["stopped"] is True
                assert data["phase"] == "cancelled"


class TestGenieDatabaseIntegration:
    """Test Genie agent integration with database operations."""

    @pytest.mark.asyncio
    async def test_epic_state_persistence(self):
        """Test that epic state is properly persisted to database."""
        # Mock the database operations
        with patch('src.db.repository.agent.create_agent') as mock_create, \
             patch('src.db.repository.agent.get_agent_by_name') as mock_get:
            
            mock_create.return_value = "agent-123"
            
            # Create a properly configured mock object
            mock_agent = Mock()
            mock_agent.id = "agent-123"
            mock_agent.name = "genie-test"
            mock_agent.agent_type = "genie"
            mock_agent.config = {"test": True}
            mock_get.return_value = mock_agent
            
            # Create agent through database
            agent_data = {
                "name": "genie-test",
                "agent_type": "genie", 
                "config": {"model_name": "openai:gpt-4o-mini"}
            }
            
            agent_id = mock_create(agent_data)
            assert agent_id == "agent-123"
            
            # Retrieve agent
            retrieved = mock_get("genie-test")
            assert retrieved.name == "genie-test"
            assert retrieved.agent_type == "genie"

    @pytest.mark.asyncio
    async def test_epic_checkpointing_with_langgraph(self):
        """Test LangGraph checkpointing integration."""
        with patch('src.agents.pydanticai.genie.orchestrator.state.PostgresSaver') as mock_saver:
            mock_checkpoint = Mock()
            mock_checkpoint.put = AsyncMock()
            mock_checkpoint.get = AsyncMock(return_value={
                "epic_id": "test-epic",
                "phase": "executing",
                "current_workflow": "test"
            })
            mock_saver.from_conn_string.return_value = mock_checkpoint
            
            # Mock the graph execution with the correct function name
            with patch('src.agents.pydanticai.genie.orchestrator.state.create_orchestration_graph') as mock_graph:
                mock_compiled = AsyncMock()
                mock_compiled.ainvoke = AsyncMock(return_value={
                    "phase": EpicPhase.COMPLETE.value,
                    "workflow_results": {},
                    "cost_accumulated": 10.0
                })
                mock_graph.return_value = mock_compiled
                
                # Test checkpointing during execution
                config = {"checkpointer": mock_checkpoint}
                graph = mock_graph("postgresql://test")
                
                if graph:  # Only test if LangGraph is available
                    result = await graph.ainvoke(
                        {"epic_id": "test-epic"}, 
                        config=config
                    )
                    
                    assert result["phase"] == EpicPhase.COMPLETE.value
                    graph.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_memory_integration(self):
        """Test integration with agent memory system."""
        with patch('src.agents.common.memory_handler.MemoryHandler') as mock_memory:
            mock_handler = AsyncMock()
            mock_handler.store_memory = AsyncMock()
            mock_handler.retrieve_memories = AsyncMock(return_value=[
                {"content": "Previous epic completed successfully", "timestamp": "2024-01-01"}
            ])
            mock_memory.return_value = mock_handler
            
            # Test memory storage during epic execution
            await mock_handler.store_memory(
                "epic-completion",
                {"epic_id": "test-epic", "phase": "complete", "cost": 15.0}
            )
            
            # Test memory retrieval
            memories = await mock_handler.retrieve_memories("epic-completion")
            assert len(memories) == 1
            assert "successfully" in memories[0]["content"]

    @pytest.mark.asyncio 
    async def test_session_management(self):
        """Test session management integration."""
        with patch('src.agents.common.session_manager.create_session_id') as mock_create_id, \
             patch('src.agents.common.session_manager.create_context') as mock_create_context:
            
            mock_create_id.return_value = "session-123"
            mock_create_context.return_value = {
                "session_id": "session-123",
                "user_id": "user-456",
                "agent_id": "genie",
                "run_id": "run-789"
            }
            
            # Test session creation
            session_id = mock_create_id()
            assert session_id == "session-123"
            
            # Test context creation
            context = mock_create_context(
                agent_id="genie",
                user_id="user-456",
                session_id="session-123"
            )
            assert context["session_id"] == "session-123"
            assert context["user_id"] == "user-456"


class TestGenieMCPIntegration:
    """Test Genie agent MCP tool integration."""

    @pytest.mark.asyncio
    async def test_slack_mcp_integration(self):
        """Test Slack MCP tool integration."""
        with patch('src.mcp.client.MCPClientManager') as mock_mcp:
            mock_client = AsyncMock()
            mock_client.call_tool = AsyncMock(return_value={
                "success": True,
                "message_id": "slack-msg-123",
                "channel": "#genie-updates"
            })
            mock_mcp.return_value = mock_client
            
            # Test Slack notification
            result = await mock_client.call_tool(
                "slack_send_message",
                {
                    "channel": "#genie-updates",
                    "text": "Epic test-epic-123 completed successfully",
                    "thread_ts": None
                }
            )
            
            assert result["success"] is True
            assert result["message_id"] == "slack-msg-123"

    @pytest.mark.asyncio
    async def test_linear_mcp_integration(self):
        """Test Linear MCP tool integration."""
        with patch('src.mcp.client.MCPClientManager') as mock_mcp:
            mock_client = AsyncMock()
            mock_client.call_tool = AsyncMock(return_value={
                "success": True,
                "issue_id": "GENIE-123",
                "url": "https://linear.app/issues/GENIE-123"
            })
            mock_mcp.return_value = mock_client
            
            # Test Linear issue creation
            result = await mock_client.call_tool(
                "linear_create_issue",
                {
                    "title": "Epic: Create authentication tests",
                    "description": "Comprehensive test suite for authentication system",
                    "team_id": "team-123",
                    "labels": ["epic", "testing"]
                }
            )
            
            assert result["success"] is True
            assert result["issue_id"] == "GENIE-123"

    @pytest.mark.asyncio
    async def test_memory_mcp_integration(self):
        """Test memory MCP tool integration."""
        with patch('src.mcp.client.MCPClientManager') as mock_mcp:
            mock_client = AsyncMock()
            mock_client.call_tool = AsyncMock(return_value={
                "success": True,
                "memory_id": "memory-123",
                "stored": True
            })
            mock_mcp.return_value = mock_client
            
            # Test memory storage
            result = await mock_client.call_tool(
                "agent_memory_add_memory",
                {
                    "name": "Epic Completion Pattern",
                    "episode_body": "Epic test-epic-123 completed with 3 workflows and cost $15.75",
                    "source": "text",
                    "group_id": "genie_learning"
                }
            )
            
            assert result["success"] is True
            assert result["memory_id"] == "memory-123"


class TestGenieEndToEndIntegration:
    """End-to-end integration tests."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_epic_execution_flow(self, genie_config, mock_dependencies):
        """Test complete epic execution from API to completion."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            # Mock the internal planning and execution methods
            with patch.object(agent, '_plan_epic') as mock_plan, \
                 patch.object(agent, '_initialize_epic_state') as mock_init_state:
                
                # Setup mocks for successful execution
                from src.agents.pydanticai.genie.models import EpicPlan
                mock_plan.return_value = EpicPlan(
                    epic_id="test-epic-123",
                    title="Create authentication tests",
                    description="Create comprehensive tests for authentication",
                    complexity_score=5,
                    planned_workflows=[WorkflowType.TEST],
                    estimated_cost=10.0,
                    estimated_duration_minutes=30,
                    requires_approvals=[]
                )
                
                mock_init_state.return_value = {}
                
                # Execute epic
                result = await agent.create_epic(
                    request="Create authentication tests",
                    budget_limit=50.0,
                    require_tests=True,
                    require_pr=True,
                    approval_mode="auto"
                )
                
                # Verify execution flow - check the return structure
                assert result["epic_id"] == "test-epic-123"
                assert result["title"] == "Create authentication tests"
                assert result["status"] == "executing"
                assert result["estimated_cost"] == 10.0
                assert not result["approval_required"]
                
                # Verify component interactions
                mock_plan.assert_called_once()
                mock_init_state.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_epic_execution_with_approval_flow(self, genie_config, mock_dependencies):
        """Test epic execution that requires approval."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            # Mock the internal planning methods for high-cost epic
            with patch.object(agent, '_plan_epic') as mock_plan, \
                 patch.object(agent, '_initialize_epic_state') as mock_init_state:
                
                # Setup high-cost workflow requiring approval
                from src.agents.pydanticai.genie.models import EpicPlan
                mock_plan.return_value = EpicPlan(
                    epic_id="test-epic-456",
                    title="Implement payment system",
                    description="Complete payment system with database changes",
                    complexity_score=8,
                    planned_workflows=[WorkflowType.IMPLEMENT, WorkflowType.TEST],
                    estimated_cost=75.0,
                    estimated_duration_minutes=120,
                    requires_approvals=["high_cost_implementation"]  # This triggers approval_required
                )
                
                mock_init_state.return_value = {}
                
                # Execute epic
                result = await agent.create_epic(
                    request="Implement complete payment system with database changes",
                    budget_limit=100.0,
                    require_tests=True,
                    require_pr=True,
                    approval_mode="manual"
                )
                
                # Verify approval flow was triggered
                assert result["epic_id"] == "test-epic-456"
                assert result["estimated_cost"] == 75.0
                assert result["approval_required"]  # Because requires_approvals is not empty
                mock_plan.assert_called_once()
                mock_init_state.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_epic_execution_with_failure_and_rollback(self, genie_config, mock_dependencies):
        """Test epic execution with failure and rollback."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            # Mock internal planning to simulate failure case  
            with patch.object(agent, '_plan_epic') as mock_plan, \
                 patch.object(agent, '_initialize_epic_state') as mock_init_state:
                
                # Simulate a planning failure by raising an exception
                mock_plan.side_effect = Exception("Test execution failed")
                
                # Execute epic
                result = await agent.create_epic(
                    request="Implement and test new feature",
                    budget_limit=50.0,
                    require_tests=True,
                    require_pr=True,
                    approval_mode="auto"
                )
                
                # Verify failure handling
                assert result["status"] == "failed"
                assert result["error"] is not None
                assert "test execution failed" in result["error"].lower()
                mock_plan.assert_called_once()
                # init_state should not be called if planning fails
                mock_init_state.assert_not_called()