"""Unit tests for ClaudeCodeAgent implementation.

This module tests the ClaudeCodeAgent class initialization, run methods,
workflow validation, and async execution functionality.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone
from typing import Dict, Any

from src.agents.claude_code.agent import ClaudeCodeAgent
from src.agents.claude_code.models import (
    ClaudeCodeRunRequest,
    ClaudeCodeRunResponse,
    ExecutionResult
)
from src.agents.models.response import AgentResponse
from src.memory.message_history import MessageHistory


class TestClaudeCodeAgentInitialization:
    """Test ClaudeCodeAgent initialization."""
    
    @patch('src.agents.claude_code.agent.ContainerManager')
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    def test_agent_initialization(self, mock_executor_factory, mock_container_class):
        """Test basic agent initialization."""
        # Mock the classes
        mock_container = Mock()
        mock_executor = Mock()
        mock_container_class.return_value = mock_container
        mock_executor_factory.create_executor.return_value = mock_executor
        
        # Initialize agent
        config = {
            "docker_image": "test-image:latest",
            "container_timeout": "3600",
            "max_concurrent_sessions": "5"
        }
        agent = ClaudeCodeAgent(config)
        
        # Verify initialization
        assert agent.description == "Containerized Claude CLI agent for autonomous code tasks"
        assert agent.config.get("agent_type") == "claude-code"
        assert agent.config.get("framework") == "claude-cli"
        assert agent.config.get("docker_image") == "test-image:latest"
        assert agent.config.get("container_timeout") == 3600
        assert agent.config.get("max_concurrent_sessions") == 5
        
        # Verify managers were created
        mock_container_class.assert_called_once_with(
            docker_image="test-image:latest",
            container_timeout=3600,
            max_concurrent=5
        )
        mock_executor_factory.create_executor.assert_called_once_with(
            mode="docker",
            container_manager=mock_container,
            workspace_base="/tmp/claude-workspace",
            cleanup_on_complete=True
        )
        
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    def test_agent_default_values(self, mock_executor_factory):
        """Test agent initialization with default values."""
        agent = ClaudeCodeAgent({})
        
        # Check defaults
        assert agent.config.get("docker_image") == "claude-code-agent:latest"
        assert agent.config.get("container_timeout") == 7200
        assert agent.config.get("max_concurrent_sessions") == 10
        assert agent.config.get("default_workflow") == "bug-fixer"
        assert agent.config.get("git_branch") == "NMSTX-187-langgraph-orchestrator-migration"
        
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    def test_agent_dependencies(self, mock_executor_factory):
        """Test agent dependencies setup."""
        agent = ClaudeCodeAgent({})
        
        assert agent.dependencies is not None
        assert agent.dependencies.model_name == "claude-3-5-sonnet-20241022"
        

class TestClaudeCodeAgentRun:
    """Test ClaudeCodeAgent run method."""
    
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.settings')
    async def test_run_disabled_agent(self, mock_settings):
        """Test running agent when disabled via feature flag."""
        # Mock settings to disable agent
        mock_settings.AM_ENABLE_CLAUDE_CODE = False
        
        agent = ClaudeCodeAgent({})
        response = await agent.run("Test message")
        
        assert response.success is False
        assert "Claude-Code agent is disabled" in response.text
        assert response.error_message == "Agent disabled via feature flag"
        
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.settings')
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_run_invalid_workflow(self, mock_executor_factory, mock_settings):
        """Test running with invalid workflow."""
        mock_settings.AM_ENABLE_CLAUDE_CODE = True
        
        agent = ClaudeCodeAgent({})
        # Mock workflow validation to return False
        agent._validate_workflow = AsyncMock(return_value=False)
        
        response = await agent.run("Test message")
        
        assert response.success is False
        assert "Workflow 'bug-fixer' not found or invalid" in response.text
        
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.settings')
    @patch('src.agents.claude_code.agent.ContainerManager')
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_run_successful_execution(self, mock_executor_factory, mock_container_class, mock_settings):
        """Test successful execution."""
        mock_settings.AM_ENABLE_CLAUDE_CODE = True
        
        # Mock executor
        mock_executor = AsyncMock()
        mock_execution_result = {
            "success": True,
            "result": "Task completed successfully",
            "container_id": "container_123",
            "execution_time": 100.5,
            "exit_code": 0,
            "git_commits": ["abc123"]
        }
        mock_executor.execute_claude_task.return_value = mock_execution_result
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        agent._validate_workflow = AsyncMock(return_value=True)
        
        response = await agent.run("Fix the bug")
        
        assert response.success is True
        assert response.text == "Task completed successfully"
        assert response.raw_message == mock_execution_result
        
        # Verify executor was called
        mock_executor.execute_claude_task.assert_called_once()
        call_args = mock_executor.execute_claude_task.call_args[1]
        assert call_args["request"].message == "Fix the bug"
        
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.settings')
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_run_failed_execution(self, mock_executor_factory, mock_settings):
        """Test failed execution."""
        mock_settings.AM_ENABLE_CLAUDE_CODE = True
        
        # Mock executor
        mock_executor = AsyncMock()
        mock_execution_result = {
            "success": False,
            "error": "Container crashed",
            "container_id": "container_123",
            "execution_time": 50.0,
            "exit_code": 1
        }
        mock_executor.execute_claude_task.return_value = mock_execution_result
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        agent._validate_workflow = AsyncMock(return_value=True)
        
        response = await agent.run("Fix the bug")
        
        assert response.success is False
        assert "Task failed: Container crashed" in response.text
        assert response.error_message == "Container crashed"
        
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.settings')
    @patch('src.agents.claude_code.agent.ContainerManager')
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_run_with_message_history(self, mock_executor_factory, mock_container_class, mock_settings):
        """Test run with message history storage."""
        mock_settings.AM_ENABLE_CLAUDE_CODE = True
        
        # Mock executor
        mock_executor = AsyncMock()
        mock_execution_result = {
            "success": True,
            "result": "Task completed",
            "container_id": "container_123",
            "execution_time": 100.0,
            "exit_code": 0,
            "git_commits": ["abc123"]
        }
        mock_executor.execute_claude_task.return_value = mock_execution_result
        mock_executor_factory.create_executor.return_value = mock_executor
        
        # Mock message history
        mock_history = Mock(spec=MessageHistory)
        
        agent = ClaudeCodeAgent({})
        agent.db_id = "agent_123"
        agent._validate_workflow = AsyncMock(return_value=True)
        
        response = await agent.run(
            "Fix the bug",
            message_history_obj=mock_history,
            channel_payload={"channel": "test"}
        )
        
        assert response.success is True
        
        # Verify message history was updated
        assert mock_history.add_message.call_count == 2
        
        # Check user message
        user_msg = mock_history.add_message.call_args_list[0][0][0]
        assert user_msg["role"] == "user"
        assert user_msg["content"] == "Fix the bug"
        assert user_msg["agent_id"] == "agent_123"
        assert user_msg["channel_payload"] == {"channel": "test"}
        
        # Check assistant message
        assistant_msg = mock_history.add_message.call_args_list[1][0][0]
        assert assistant_msg["role"] == "assistant"
        assert assistant_msg["content"] == "Task completed"
        assert assistant_msg["context"]["container_id"] == "container_123"
        assert assistant_msg["context"]["git_commits"] == ["abc123"]
        
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.settings')
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_run_exception_handling(self, mock_executor_factory, mock_settings):
        """Test exception handling during run."""
        mock_settings.AM_ENABLE_CLAUDE_CODE = True
        
        # Mock executor to raise exception
        mock_executor = AsyncMock()
        mock_executor.execute_claude_task.side_effect = Exception("Unexpected error")
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        agent._validate_workflow = AsyncMock(return_value=True)
        
        response = await agent.run("Fix the bug")
        
        assert response.success is False
        assert "Error executing Claude task: Unexpected error" in response.text
        assert response.error_message == "Unexpected error"


class TestWorkflowValidation:
    """Test workflow validation methods."""
    
    @pytest.mark.asyncio
    @patch('os.path.exists')
    async def test_validate_workflow_success(self, mock_exists):
        """Test successful workflow validation."""
        # Mock file existence checks
        mock_exists.side_effect = [
            True,  # workflow directory exists
            True,  # prompt.md exists
            True,  # .mcp.json exists
            True   # allowed_tools.json exists
        ]
        
        agent = ClaudeCodeAgent({})
        result = await agent._validate_workflow("test-workflow")
        
        assert result is True
        assert mock_exists.call_count == 4
        
    @pytest.mark.asyncio
    @patch('os.path.exists')
    async def test_validate_workflow_missing_directory(self, mock_exists):
        """Test workflow validation with missing directory."""
        mock_exists.return_value = False
        
        agent = ClaudeCodeAgent({})
        result = await agent._validate_workflow("missing-workflow")
        
        assert result is False
        
    @pytest.mark.asyncio
    @patch('os.path.exists')
    async def test_validate_workflow_missing_files(self, mock_exists):
        """Test workflow validation with missing required files."""
        # Workflow directory exists but prompt.md is missing
        mock_exists.side_effect = [True, False]
        
        agent = ClaudeCodeAgent({})
        result = await agent._validate_workflow("incomplete-workflow")
        
        assert result is False
        
    @pytest.mark.asyncio
    @patch('os.path.exists')
    async def test_validate_workflow_exception(self, mock_exists):
        """Test workflow validation with exception."""
        mock_exists.side_effect = Exception("OS error")
        
        agent = ClaudeCodeAgent({})
        result = await agent._validate_workflow("error-workflow")
        
        assert result is False


class TestGetAvailableWorkflows:
    """Test getting available workflows."""
    
    @pytest.mark.asyncio
    @patch('os.listdir')
    @patch('os.path.exists')
    @patch('os.path.isdir')
    async def test_get_available_workflows(self, mock_isdir, mock_exists, mock_listdir):
        """Test getting list of available workflows."""
        # Mock directory listing
        mock_listdir.return_value = ["workflow1", "workflow2", "not-a-dir"]
        mock_isdir.side_effect = [True, True, False]  # First two are dirs
        mock_exists.return_value = True
        
        # Mock file reading
        with patch('builtins.open', create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.readlines.return_value = [
                "# Workflow 1 Description\n"
            ]
            
            agent = ClaudeCodeAgent({})
            agent._validate_workflow = AsyncMock(side_effect=[True, False])
            
            workflows = await agent.get_available_workflows()
        
        assert len(workflows) == 2
        assert "workflow1" in workflows
        assert workflows["workflow1"]["description"] == "Workflow 1 Description"
        assert workflows["workflow1"]["valid"] is True
        assert workflows["workflow2"]["valid"] is False
        
    @pytest.mark.asyncio
    @patch('os.path.exists')
    async def test_get_available_workflows_no_directory(self, mock_exists):
        """Test getting workflows when directory doesn't exist."""
        mock_exists.return_value = False
        
        agent = ClaudeCodeAgent({})
        workflows = await agent.get_available_workflows()
        
        assert workflows == {}


class TestAsyncExecution:
    """Test async execution methods."""
    
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_create_async_run(self, mock_executor_factory):
        """Test creating async run."""
        agent = ClaudeCodeAgent({})
        
        # Mock background task creation
        with patch('asyncio.create_task') as mock_create_task:
            response = await agent.create_async_run(
                "Fix the bug",
                "bug-fixer",
                session_id="session_123",
                max_turns=50
            )
        
        assert response.run_id.startswith("run_")
        assert response.status == "pending"
        assert response.message == "Container deployment initiated"
        assert response.session_id == "session_123"
        
        # Verify background task was created
        mock_create_task.assert_called_once()
        
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_execute_async_run_success(self, mock_executor_factory):
        """Test executing async run successfully."""
        # Mock executor
        mock_executor = AsyncMock()
        mock_result = {
            "success": True,
            "result": "Task completed"
        }
        mock_executor.execute_claude_task.return_value = mock_result
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        
        # Create request
        request = ClaudeCodeRunRequest(
            message="Fix bug",
            workflow_name="fix"
        )
        
        # Set up context entry (normally done by create_async_run)
        agent.context["run_run_123"] = {
            "status": "pending",
            "request": request.model_dump(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "workflow_name": "fix"
        }
        
        # Execute
        await agent._execute_async_run("run_123", request)
        
        # Check context was updated
        assert agent.context["run_run_123"]["status"] == "completed"
        assert agent.context["run_run_123"]["result"] == mock_result
        
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_execute_async_run_failure(self, mock_executor_factory):
        """Test executing async run with failure."""
        # Mock executor to raise exception
        mock_executor = AsyncMock()
        mock_executor.execute_claude_task.side_effect = Exception("Execution failed")
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        
        # Create request
        request = ClaudeCodeRunRequest(
            message="Fix bug",
            workflow_name="fix"
        )
        
        # Set up context entry (normally done by create_async_run)
        agent.context["run_run_123"] = {
            "status": "pending",
            "request": request.model_dump(),
            "started_at": datetime.now(timezone.utc).isoformat(),
            "workflow_name": "fix"
        }
        
        # Execute
        await agent._execute_async_run("run_123", request)
        
        # Check context was updated with failure
        assert agent.context["run_run_123"]["status"] == "failed"
        assert agent.context["run_run_123"]["error"] == "Execution failed"
        
    @pytest.mark.asyncio
    async def test_get_run_status(self):
        """Test getting run status."""
        agent = ClaudeCodeAgent({})
        
        # Add run to context
        agent.context["run_run_123"] = {
            "status": "completed",
            "result": {"success": True}
        }
        
        status = await agent.get_run_status("run_123")
        
        assert status["run_id"] == "run_123"
        assert status["status"] == "completed"
        assert status["result"]["success"] is True
        
    @pytest.mark.asyncio
    async def test_get_run_status_not_found(self):
        """Test getting status for non-existent run."""
        agent = ClaudeCodeAgent({})
        
        status = await agent.get_run_status("run_999")
        
        assert status["run_id"] == "run_999"
        assert status["status"] == "not_found"
        assert "not found" in status["error"]


class TestCleanup:
    """Test cleanup methods."""
    
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_cleanup(self, mock_executor_factory):
        """Test agent cleanup."""
        # Mock executor with cleanup method
        mock_executor = AsyncMock()
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        
        # Mock parent cleanup
        with patch('src.agents.models.automagik_agent.AutomagikAgent.cleanup') as mock_parent_cleanup:
            mock_parent_cleanup.return_value = None
            await agent.cleanup()
        
        # Verify cleanup was called
        mock_executor.cleanup.assert_called_once()
        mock_parent_cleanup.assert_called_once()
        
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_cleanup_exception(self, mock_executor_factory):
        """Test cleanup with exception."""
        # Mock executor that raises exception
        mock_executor = AsyncMock()
        mock_executor.cleanup.side_effect = Exception("Cleanup failed")
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        
        # Should not raise exception
        await agent.cleanup()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.settings')
    async def test_run_with_multimodal_content(self, mock_settings):
        """Test run with multimodal content (should be ignored)."""
        mock_settings.AM_ENABLE_CLAUDE_CODE = True
        
        agent = ClaudeCodeAgent({})
        agent._validate_workflow = AsyncMock(return_value=True)
        agent.executor = AsyncMock()
        agent.executor.execute_claude_task.return_value = {
            "success": True,
            "result": "Done"
        }
        
        # Multimodal content should be ignored
        response = await agent.run(
            "Fix bug",
            multimodal_content={"image": "data"},
            system_message="Custom system message"  # Also ignored
        )
        
        assert response.success is True
        
        # Verify the call was made correctly
        agent.executor.execute_claude_task.assert_called_once()
        
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.settings')
    async def test_run_with_custom_workflow_context(self, mock_settings):
        """Test run with custom workflow from context."""
        mock_settings.AM_ENABLE_CLAUDE_CODE = True
        
        agent = ClaudeCodeAgent({})
        agent.context["workflow_name"] = "custom-workflow"
        agent._validate_workflow = AsyncMock(return_value=True)
        agent.executor = AsyncMock()
        agent.executor.execute_claude_task.return_value = {
            "success": True,
            "result": "Done"
        }
        
        response = await agent.run("Fix bug")
        
        assert response.success is True
        
        # Verify custom workflow was used
        call_args = agent.executor.execute_claude_task.call_args[1]
        assert call_args["request"].workflow_name == "custom-workflow"