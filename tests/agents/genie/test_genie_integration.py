"""Integration tests for Genie Agent with API and database."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os
import httpx

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))

from src.agents.pydanticai.genie.agent import GenieAgent
from src.agents.pydanticai.genie.models import EpicRequest, EpicPhase, WorkflowType


class TestGenieAPIIntegration:
    """Test Genie agent integration with FastAPI routes."""

    @pytest.mark.asyncio
    async def test_genie_run_endpoint(self):
        """Test /agent/genie/run endpoint."""
        # Mock the global agent instance
        with patch('src.api.routes.genie_routes.genie_agent') as mock_agent:
            mock_result = AsyncMock()
            mock_result.phase = EpicPhase.COMPLETE
            mock_result.epic_id = "test-epic-123"
            mock_result.total_cost = 15.75
            mock_result.workflow_results = []
            
            mock_agent.create_epic = AsyncMock(return_value=mock_result)
            
            # Test data
            request_data = {
                "description": "Create comprehensive tests for authentication system",
                "requirements": ["Unit tests", "Integration tests"],
                "acceptance_criteria": ["95% coverage", "All tests pass"]
            }
            
            # Mock the HTTP client call
            with patch('httpx.AsyncClient.post') as mock_post:
                mock_response = AsyncMock()
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "epic_id": "test-epic-123",
                    "phase": "complete",
                    "total_cost": 15.75,
                    "success": True
                }
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
                    assert data["phase"] == "complete"
                    assert data["total_cost"] == 15.75

    @pytest.mark.asyncio
    async def test_genie_status_endpoint(self):
        """Test /agent/genie/status/{epic_id} endpoint."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "epic_id": "test-epic-123",
                "phase": "executing",
                "current_workflow": "test",
                "progress": 0.6,
                "total_cost": 8.25
            }
            mock_get.return_value = mock_response
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://localhost:8000/api/v1/agent/genie/status/test-epic-123"
                )
                
                data = response.json()
                assert data["epic_id"] == "test-epic-123"
                assert data["phase"] == "executing"
                assert data["progress"] == 0.6

    @pytest.mark.asyncio
    async def test_genie_approve_endpoint(self):
        """Test /agent/genie/approve/{epic_id}/{approval_id} endpoint."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "approval_id": "approval-123",
                "approved": True,
                "approved_by": "test-user",
                "epic_resumed": True
            }
            mock_post.return_value = mock_response
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:8000/api/v1/agent/genie/approve/epic-123/approval-123",
                    json={"approved": True, "notes": "Looks good"}
                )
                
                data = response.json()
                assert data["approved"] is True
                assert data["epic_resumed"] is True

    @pytest.mark.asyncio
    async def test_genie_list_epics_endpoint(self):
        """Test /agent/genie/list endpoint."""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "epics": [
                    {
                        "epic_id": "epic-1",
                        "phase": "complete",
                        "description": "Create authentication tests",
                        "total_cost": 12.50
                    },
                    {
                        "epic_id": "epic-2", 
                        "phase": "executing",
                        "description": "Implement payment system",
                        "total_cost": 35.75
                    }
                ],
                "total_count": 2
            }
            mock_get.return_value = mock_response
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://localhost:8000/api/v1/agent/genie/list"
                )
                
                data = response.json()
                assert len(data["epics"]) == 2
                assert data["total_count"] == 2

    @pytest.mark.asyncio
    async def test_genie_stop_epic_endpoint(self):
        """Test /agent/genie/stop/{epic_id} endpoint."""
        with patch('httpx.AsyncClient.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "epic_id": "epic-123",
                "stopped": True,
                "phase": "cancelled",
                "reason": "User requested stop"
            }
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
            mock_get.return_value = Mock(
                id="agent-123",
                name="genie-test",
                agent_type="genie",
                config={"test": True}
            )
            
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
            mock_saver.return_value = mock_checkpoint
            
            # Mock the graph execution
            with patch('src.agents.pydanticai.genie.orchestrator.state.create_epic_graph') as mock_graph:
                mock_compiled = AsyncMock()
                mock_compiled.ainvoke = AsyncMock(return_value={
                    "phase": EpicPhase.COMPLETE,
                    "workflow_results": [],
                    "total_cost": 10.0
                })
                mock_graph.return_value.compile.return_value = mock_compiled
                
                # Test checkpointing during execution
                config = {"checkpointer": mock_checkpoint}
                result = await mock_compiled.ainvoke(
                    {"epic_id": "test-epic"}, 
                    config=config
                )
                
                assert result["phase"] == EpicPhase.COMPLETE
                mock_compiled.ainvoke.assert_called_once()

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
        with patch('src.agents.common.session_manager.SessionManager') as mock_session:
            mock_manager = AsyncMock()
            mock_manager.create_session = AsyncMock(return_value="session-123")
            mock_manager.get_session = AsyncMock(return_value={
                "session_id": "session-123",
                "user_id": "user-456",
                "agent_name": "genie",
                "active": True
            })
            mock_session.return_value = mock_manager
            
            # Test session creation
            session_id = await mock_manager.create_session(
                user_id="user-456",
                agent_name="genie"
            )
            assert session_id == "session-123"
            
            # Test session retrieval
            session = await mock_manager.get_session("session-123")
            assert session["agent_name"] == "genie"
            assert session["active"] is True


class TestGenieMCPIntegration:
    """Test Genie agent MCP tool integration."""

    @pytest.mark.asyncio
    async def test_slack_mcp_integration(self):
        """Test Slack MCP tool integration."""
        with patch('src.mcp.client.MCPClient') as mock_mcp:
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
        with patch('src.mcp.client.MCPClient') as mock_mcp:
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
        with patch('src.mcp.client.MCPClient') as mock_mcp:
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

    @pytest.mark.asyncio
    async def test_complete_epic_execution_flow(self, genie_config, mock_dependencies):
        """Test complete epic execution from API to completion."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            # Mock all external components
            with patch.object(agent, 'router') as mock_router, \
                 patch.object(agent, 'claude_client') as mock_client, \
                 patch.object(agent, 'approval_manager') as mock_approval:
                
                # Setup mocks for successful execution
                mock_router.select_workflows.return_value = [WorkflowType.TEST]
                mock_router.estimate_cost.return_value = 10.0
                mock_router.estimate_duration.return_value = 30
                
                mock_client.execute_workflow.return_value = {
                    "success": True,
                    "output": "Tests created successfully",
                    "cost": 10.0,
                    "logs": ["Created test_auth.py", "All tests passing"]
                }
                
                mock_approval.should_request_approval.return_value = False
                
                # Execute epic
                request = EpicRequest(
                    description="Create authentication tests",
                    requirements=["Unit tests", "Integration tests"],
                    acceptance_criteria=["95% coverage"]
                )
                
                result = await agent.create_epic(request)
                
                # Verify execution flow
                assert result.phase == EpicPhase.COMPLETE
                assert result.total_cost == 10.0
                assert len(result.workflow_results) == 1
                
                # Verify component interactions
                mock_router.select_workflows.assert_called_once()
                mock_client.execute_workflow.assert_called_once()
                mock_approval.should_request_approval.assert_called()

    @pytest.mark.asyncio
    async def test_epic_execution_with_approval_flow(self, genie_config, mock_dependencies):
        """Test epic execution that requires approval."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'router') as mock_router, \
                 patch.object(agent, 'claude_client') as mock_client, \
                 patch.object(agent, 'approval_manager') as mock_approval:
                
                # Setup high-cost workflow requiring approval
                mock_router.select_workflows.return_value = [WorkflowType.IMPLEMENT, WorkflowType.TEST]
                mock_router.estimate_cost.return_value = 75.0
                mock_router.estimate_duration.return_value = 120
                
                mock_approval.should_request_approval.return_value = True
                mock_approval.create_approval_request.return_value = "approval-123"
                mock_approval.wait_for_approval.return_value = True  # Approved
                
                mock_client.execute_workflow.return_value = {
                    "success": True,
                    "output": "Implementation completed",
                    "cost": 37.5
                }
                
                # Execute epic
                request = EpicRequest(
                    description="Implement complete payment system with database changes",
                    requirements=["Payment processing", "Database schema", "Tests"],
                    acceptance_criteria=["Secure payments", "Data integrity"]
                )
                
                result = await agent.create_epic(request)
                
                # Verify approval flow was triggered
                assert result.phase == EpicPhase.COMPLETE
                assert len(result.approval_points) > 0
                mock_approval.create_approval_request.assert_called()
                mock_approval.wait_for_approval.assert_called()

    @pytest.mark.asyncio
    async def test_epic_execution_with_failure_and_rollback(self, genie_config, mock_dependencies):
        """Test epic execution with failure and rollback."""
        with patch('src.agents.pydanticai.genie.agent.AutomagikAgentsDependencies', return_value=mock_dependencies):
            agent = GenieAgent(genie_config)
            
            with patch.object(agent, 'router') as mock_router, \
                 patch.object(agent, 'claude_client') as mock_client:
                
                mock_router.select_workflows.return_value = [WorkflowType.IMPLEMENT, WorkflowType.TEST]
                mock_router.estimate_cost.return_value = 25.0
                
                # First workflow succeeds, second fails
                mock_client.execute_workflow.side_effect = [
                    {"success": True, "output": "Implementation done", "cost": 15.0},
                    {"success": False, "error": "Test execution failed", "cost": 5.0}
                ]
                
                request = EpicRequest(
                    description="Implement and test new feature",
                    requirements=["Implementation", "Tests"],
                    acceptance_criteria=["Working feature"]
                )
                
                result = await agent.create_epic(request)
                
                # Verify failure handling
                assert result.phase == EpicPhase.FAILED
                assert result.error_message is not None
                assert "test execution failed" in result.error_message.lower()
                assert len(result.rollback_points) > 0