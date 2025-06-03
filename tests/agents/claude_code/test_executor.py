"""Unit tests for ClaudeExecutor implementation.

This module tests the ClaudeExecutor class that handles execution
of Claude CLI commands within Docker containers.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock, mock_open
import json
import os
from typing import Dict, Any

from src.agents.claude_code.executor import ClaudeExecutor
from src.agents.claude_code.container import ContainerManager
from src.agents.claude_code.models import ClaudeCodeRunRequest


class TestClaudeExecutorInitialization:
    """Test ClaudeExecutor initialization."""
    
    def test_executor_initialization(self):
        """Test basic executor initialization."""
        mock_container_manager = Mock(spec=ContainerManager)
        
        executor = ClaudeExecutor(mock_container_manager)
        
        assert executor.container_manager == mock_container_manager


class TestExecuteClaudeTask:
    """Test execute_claude_task method."""
    
    @pytest.mark.asyncio
    async def test_execute_success(self):
        """Test successful execution."""
        # Setup mocks for container manager
        mock_container_manager = Mock(spec=ContainerManager)
        mock_container_manager.docker_client = Mock()  # Already initialized
        mock_container_manager.initialize = AsyncMock(return_value=True)
        mock_container_manager.create_container = AsyncMock(return_value="container_123")
        mock_container_manager.start_container = AsyncMock(return_value=True)
        mock_container_manager.wait_for_completion = AsyncMock(return_value={
            'success': True,
            'exit_code': 0,
            'result': 'Task completed'
        })
        
        executor = ClaudeExecutor(mock_container_manager)
        
        # Mock all the internal methods that are called during execution
        mock_workflow_config = {
            'name': 'test-workflow',
            'path': '/path/to/workflow',
            'prompt': 'Test prompt'
        }
        
        # Create proper async mocks with explicit return values
        async def mock_load_workflow_config(workflow_name):
            return mock_workflow_config
            
        async def mock_prepare_environment(request, workflow_config, agent_context):
            return {'ENV': 'value'}
            
        async def mock_prepare_volumes(request, workflow_config):
            return {'vol': {'bind': '/vol'}}
            
        async def mock_build_claude_command(request, workflow_config):
            return ['claude', 'command']
        
        # Assign the mocked methods
        executor._load_workflow_config = mock_load_workflow_config
        executor._prepare_environment = mock_prepare_environment
        executor._prepare_volumes = mock_prepare_volumes
        executor._build_claude_command = mock_build_claude_command
        
        # Create request
        request = ClaudeCodeRunRequest(
            message="Fix the bug",
            workflow_name="test-workflow"
        )
        
        # Execute
        result = await executor.execute_claude_task(request, {'agent_id': 'agent_123'})
        
        # Verify
        assert result['success'] is True
        assert result['exit_code'] == 0
        assert result['result'] == 'Task completed'
        assert result['workflow_name'] == 'test-workflow'
        assert result['request_message'] == 'Fix the bug'
        
        # Verify calls
        mock_container_manager.create_container.assert_called_once()
        mock_container_manager.start_container.assert_called_once_with('container_123', ['claude', 'command'])
        mock_container_manager.wait_for_completion.assert_called_once_with('container_123')
        
    @pytest.mark.asyncio
    async def test_execute_docker_not_initialized(self):
        """Test execution when Docker not initialized."""
        mock_container_manager = Mock(spec=ContainerManager)
        mock_container_manager.docker_client = None  # Not initialized
        mock_container_manager.initialize = AsyncMock(return_value=False)
        
        executor = ClaudeExecutor(mock_container_manager)
        
        request = ClaudeCodeRunRequest(
            message="Fix the bug",
            workflow_name="test-workflow"
        )
        
        result = await executor.execute_claude_task(request, {})
        
        assert result['success'] is False
        assert result['error'] == 'Failed to initialize Docker client'
        assert result['exit_code'] == -1
        
    @pytest.mark.asyncio
    async def test_execute_workflow_not_found(self):
        """Test execution with missing workflow."""
        mock_container_manager = Mock(spec=ContainerManager)
        mock_container_manager.docker_client = Mock()
        
        executor = ClaudeExecutor(mock_container_manager)
        executor._load_workflow_config = AsyncMock(return_value=None)
        
        request = ClaudeCodeRunRequest(
            message="Fix the bug",
            workflow_name="missing-workflow"
        )
        
        result = await executor.execute_claude_task(request, {})
        
        assert result['success'] is False
        assert 'Failed to load workflow configuration' in result['error']
        assert result['exit_code'] == -1
        
    @pytest.mark.asyncio
    async def test_execute_container_start_failure(self):
        """Test execution when container fails to start."""
        mock_container_manager = Mock(spec=ContainerManager)
        mock_container_manager.docker_client = Mock()
        mock_container_manager.create_container = AsyncMock(return_value="container_123")
        mock_container_manager.start_container = AsyncMock(return_value=False)
        
        executor = ClaudeExecutor(mock_container_manager)
        executor._load_workflow_config = AsyncMock(return_value={'name': 'test'})
        executor._prepare_environment = AsyncMock(return_value={})
        executor._prepare_volumes = AsyncMock(return_value={})
        executor._build_claude_command = AsyncMock(return_value=['cmd'])
        
        request = ClaudeCodeRunRequest(
            message="Fix the bug",
            workflow_name="test-workflow"
        )
        
        result = await executor.execute_claude_task(request, {})
        
        assert result['success'] is False
        assert 'Failed to start container' in result['error']
        assert result['exit_code'] == -1
        
    @pytest.mark.asyncio
    async def test_execute_with_session_id(self):
        """Test execution with provided session ID."""
        mock_container_manager = Mock(spec=ContainerManager)
        mock_container_manager.docker_client = Mock()
        mock_container_manager.create_container = AsyncMock(return_value="container_123")
        mock_container_manager.start_container = AsyncMock(return_value=True)
        mock_container_manager.wait_for_completion = AsyncMock(return_value={'success': True})
        
        executor = ClaudeExecutor(mock_container_manager)
        executor._load_workflow_config = AsyncMock(return_value={'name': 'test'})
        executor._prepare_environment = AsyncMock(return_value={})
        executor._prepare_volumes = AsyncMock(return_value={})
        executor._build_claude_command = AsyncMock(return_value=['cmd'])
        
        request = ClaudeCodeRunRequest(
            message="Fix the bug",
            workflow_name="test-workflow",
            session_id="custom_session_123"
        )
        
        result = await executor.execute_claude_task(request, {})
        
        # Verify session ID was used
        create_call_args = mock_container_manager.create_container.call_args[1]
        assert create_call_args['session_id'] == "custom_session_123"
        assert result['session_id'] == "custom_session_123"
        
    @pytest.mark.asyncio
    async def test_execute_exception_handling(self):
        """Test exception handling during execution."""
        mock_container_manager = Mock(spec=ContainerManager)
        mock_container_manager.docker_client = Mock()
        mock_container_manager.create_container = AsyncMock(side_effect=Exception("Docker error"))
        
        executor = ClaudeExecutor(mock_container_manager)
        executor._load_workflow_config = AsyncMock(return_value={'name': 'test'})
        executor._prepare_environment = AsyncMock(return_value={})
        executor._prepare_volumes = AsyncMock(return_value={})
        executor._build_claude_command = AsyncMock(return_value=['cmd'])
        
        request = ClaudeCodeRunRequest(
            message="Fix the bug",
            workflow_name="test-workflow"
        )
        
        result = await executor.execute_claude_task(request, {})
        
        assert result['success'] is False
        assert result['error'] == "Docker error"
        assert result['exit_code'] == -1


class TestLoadWorkflowConfig:
    """Test _load_workflow_config method."""
    
    @pytest.mark.asyncio
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    @patch('json.load')
    async def test_load_workflow_config_success(self, mock_json_load, mock_file_open, mock_exists):
        """Test successful workflow config loading."""
        # Mock file existence
        mock_exists.side_effect = [
            True,   # workflow directory exists
            True,   # prompt.md exists
            True,   # .mcp.json exists
            True,   # allowed_tools.json exists
            False   # .env doesn't exist
        ]
        
        # Mock file contents
        mock_file_open.return_value.read.return_value = "Test prompt content"
        mock_json_load.side_effect = [
            {"mcp": "config"},  # MCP config
            ["tool1", "tool2"]  # Allowed tools
        ]
        
        executor = ClaudeExecutor(Mock())
        config = await executor._load_workflow_config("test-workflow")
        
        assert config is not None
        assert config['name'] == "test-workflow"
        assert config['prompt'] == "Test prompt content"
        assert config['mcp_config'] == {"mcp": "config"}
        assert config['allowed_tools'] == ["tool1", "tool2"]
        assert 'env_file' not in config
        
    @pytest.mark.asyncio
    @patch('os.path.exists')
    async def test_load_workflow_config_not_found(self, mock_exists):
        """Test loading non-existent workflow."""
        mock_exists.return_value = False
        
        executor = ClaudeExecutor(Mock())
        config = await executor._load_workflow_config("missing-workflow")
        
        assert config is None
        
    @pytest.mark.asyncio
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    async def test_load_workflow_config_missing_files(self, mock_file_open, mock_exists):
        """Test loading workflow with missing files."""
        # Workflow exists but files are missing
        mock_exists.side_effect = [
            True,   # workflow directory exists
            False,  # prompt.md missing
            False,  # .mcp.json missing
            False,  # allowed_tools.json missing
            False   # .env missing
        ]
        
        executor = ClaudeExecutor(Mock())
        config = await executor._load_workflow_config("test-workflow")
        
        assert config is not None
        assert config['prompt'] == ""
        assert config['mcp_config'] == {}
        assert config['allowed_tools'] == []
        
    @pytest.mark.asyncio
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    async def test_load_workflow_config_with_env_file(self, mock_file_open, mock_exists):
        """Test loading workflow with .env file."""
        mock_exists.side_effect = [
            True,   # workflow directory
            False,  # prompt.md
            False,  # .mcp.json
            False,  # allowed_tools.json
            True    # .env exists
        ]
        
        executor = ClaudeExecutor(Mock())
        config = await executor._load_workflow_config("test-workflow")
        
        assert config is not None
        assert 'env_file' in config
        
    @pytest.mark.asyncio
    @patch('os.path.exists')
    @patch('builtins.open')
    async def test_load_workflow_config_exception(self, mock_open, mock_exists):
        """Test loading workflow with exception."""
        mock_exists.return_value = True
        mock_open.side_effect = Exception("Read error")
        
        executor = ClaudeExecutor(Mock())
        config = await executor._load_workflow_config("test-workflow")
        
        assert config is None


class TestPrepareEnvironment:
    """Test _prepare_environment method."""
    
    @pytest.mark.asyncio
    async def test_prepare_environment_basic(self):
        """Test basic environment preparation."""
        executor = ClaudeExecutor(Mock())
        
        request = ClaudeCodeRunRequest(
            message="Fix bug",
            workflow_name="test",
            session_id="session_123",
            max_turns=50,
            git_branch="feature-branch"
        )
        
        workflow_config = {'name': 'test'}
        agent_context = {
            'agent_id': 'agent_123',
            'user_id': 'user_456',
            'run_id': 'run_789'
        }
        
        env = await executor._prepare_environment(request, workflow_config, agent_context)
        
        assert env['SESSION_ID'] == 'session_123'
        assert env['WORKFLOW_NAME'] == 'test'
        assert env['GIT_BRANCH'] == 'feature-branch'
        assert env['CLAUDE_MESSAGE'] == 'Fix bug'
        assert env['MAX_TURNS'] == '50'
        assert env['AGENT_ID'] == 'agent_123'
        assert env['USER_ID'] == 'user_456'
        assert env['RUN_ID'] == 'run_789'
        
    @pytest.mark.asyncio
    async def test_prepare_environment_no_session_id(self):
        """Test environment preparation without session ID."""
        executor = ClaudeExecutor(Mock())
        
        request = ClaudeCodeRunRequest(
            message="Fix bug",
            workflow_name="test"
        )
        
        env = await executor._prepare_environment(request, {}, {})
        
        assert env['SESSION_ID'] == ''
        
    @pytest.mark.asyncio
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open)
    async def test_prepare_environment_with_env_file(self, mock_file_open, mock_exists):
        """Test environment preparation with .env file."""
        mock_exists.return_value = True
        mock_file_open.return_value.read.return_value = """
        # Comment
        KEY1=value1
        KEY2=value2
        INVALID_LINE
        KEY3 = value3
        """
        mock_file_open.return_value.__iter__.return_value = [
            "# Comment\n",
            "KEY1=value1\n",
            "KEY2=value2\n",
            "INVALID_LINE\n",
            "KEY3 = value3\n"
        ]
        
        executor = ClaudeExecutor(Mock())
        
        request = ClaudeCodeRunRequest(message="Fix bug", workflow_name="test")
        workflow_config = {'env_file': '/path/to/.env'}
        
        env = await executor._prepare_environment(request, workflow_config, {})
        
        assert env['KEY1'] == 'value1'
        assert env['KEY2'] == 'value2'
        assert env['KEY3'] == 'value3'
        assert 'INVALID_LINE' not in env
        
    @pytest.mark.asyncio
    @patch('os.path.exists')
    @patch('builtins.open')
    async def test_prepare_environment_env_file_error(self, mock_open, mock_exists):
        """Test environment preparation with .env file error."""
        mock_exists.return_value = True
        mock_open.side_effect = Exception("Read error")
        
        executor = ClaudeExecutor(Mock())
        
        request = ClaudeCodeRunRequest(message="Fix bug", workflow_name="test")
        workflow_config = {'env_file': '/path/to/.env'}
        
        # Should not raise exception
        env = await executor._prepare_environment(request, workflow_config, {})
        
        # Basic env vars should still be set
        assert env['WORKFLOW_NAME'] == 'test'


class TestPrepareVolumes:
    """Test _prepare_volumes method."""
    
    @pytest.mark.asyncio
    @patch('os.path.exists')
    @patch('os.path.expanduser')
    async def test_prepare_volumes_basic(self, mock_expanduser, mock_exists):
        """Test basic volume preparation."""
        mock_expanduser.return_value = '/home/user/.ssh'
        mock_exists.return_value = False  # No SSH dir
        
        executor = ClaudeExecutor(Mock())
        
        request = ClaudeCodeRunRequest(
            message="Fix bug",
            workflow_name="test",
            session_id="session_123"
        )
        
        workflow_config = {'path': '/path/to/workflow'}
        
        volumes = await executor._prepare_volumes(request, workflow_config)
        
        # Check workflow volume
        assert '/path/to/workflow' in volumes
        assert volumes['/path/to/workflow']['bind'] == '/workspace/workflow'
        assert volumes['/path/to/workflow']['mode'] == 'ro'
        
        # Check workspace volume
        assert 'claude-workspace-session_123' in volumes
        assert volumes['claude-workspace-session_123']['bind'] == '/workspace'
        assert volumes['claude-workspace-session_123']['mode'] == 'rw'
        
        # Check Docker socket
        assert '/var/run/docker.sock' in volumes
        assert volumes['/var/run/docker.sock']['bind'] == '/var/run/docker.sock'
        
    @pytest.mark.asyncio
    @patch('os.path.exists')
    @patch('os.path.expanduser')
    async def test_prepare_volumes_with_ssh(self, mock_expanduser, mock_exists):
        """Test volume preparation with SSH directory."""
        mock_expanduser.return_value = '/home/user/.ssh'
        mock_exists.return_value = True  # SSH dir exists
        
        executor = ClaudeExecutor(Mock())
        
        request = ClaudeCodeRunRequest(
            message="Fix bug",
            workflow_name="test"
        )
        
        workflow_config = {'path': '/path/to/workflow'}
        
        volumes = await executor._prepare_volumes(request, workflow_config)
        
        # Check SSH volume
        assert '/home/user/.ssh' in volumes
        assert volumes['/home/user/.ssh']['bind'] == '/home/claude/.ssh'
        assert volumes['/home/user/.ssh']['mode'] == 'ro'
        
    @pytest.mark.asyncio
    async def test_prepare_volumes_no_session_id(self):
        """Test volume preparation without session ID."""
        executor = ClaudeExecutor(Mock())
        
        request = ClaudeCodeRunRequest(
            message="Fix bug",
            workflow_name="test"
        )
        
        workflow_config = {'path': '/path/to/workflow'}
        
        volumes = await executor._prepare_volumes(request, workflow_config)
        
        # Should use 'default' as session ID
        assert 'claude-workspace-default' in volumes


class TestBuildClaudeCommand:
    """Test _build_claude_command method."""
    
    @pytest.mark.asyncio
    async def test_build_claude_command(self):
        """Test building Claude command."""
        executor = ClaudeExecutor(Mock())
        
        request = ClaudeCodeRunRequest(
            message="Fix the bug in session controller",
            workflow_name="test"
        )
        
        workflow_config = {'name': 'test'}
        
        command = await executor._build_claude_command(request, workflow_config)
        
        assert command == ["Fix the bug in session controller"]


class TestGetExecutionLogs:
    """Test get_execution_logs method."""
    
    @pytest.mark.asyncio
    async def test_get_execution_logs_success(self):
        """Test getting execution logs."""
        mock_container = Mock()
        mock_container.logs.return_value = b"Execution logs here"
        
        mock_container_manager = Mock()
        mock_container_manager.active_containers = {
            "container_123": {
                'container': mock_container
            }
        }
        
        executor = ClaudeExecutor(mock_container_manager)
        
        logs = await executor.get_execution_logs("container_123")
        
        assert logs == "Execution logs here"
        mock_container.logs.assert_called_once_with(stdout=True, stderr=True)
        
    @pytest.mark.asyncio
    async def test_get_execution_logs_not_found(self):
        """Test getting logs for non-existent container."""
        mock_container_manager = Mock()
        mock_container_manager.active_containers = {}
        
        executor = ClaudeExecutor(mock_container_manager)
        
        logs = await executor.get_execution_logs("container_999")
        
        assert "Container container_999 not found" in logs
        
    @pytest.mark.asyncio
    async def test_get_execution_logs_exception(self):
        """Test getting logs with exception."""
        mock_container = Mock()
        mock_container.logs.side_effect = Exception("Docker error")
        
        mock_container_manager = Mock()
        mock_container_manager.active_containers = {
            "container_123": {
                'container': mock_container
            }
        }
        
        executor = ClaudeExecutor(mock_container_manager)
        
        logs = await executor.get_execution_logs("container_123")
        
        assert "Error retrieving logs: Docker error" in logs


class TestCancelExecution:
    """Test cancel_execution method."""
    
    @pytest.mark.asyncio
    async def test_cancel_execution_success(self):
        """Test successful execution cancellation."""
        mock_container_manager = Mock()
        mock_container_manager.active_containers = {
            "container_123": {}
        }
        mock_container_manager._kill_container = AsyncMock()
        mock_container_manager._cleanup_container = AsyncMock()
        
        executor = ClaudeExecutor(mock_container_manager)
        
        result = await executor.cancel_execution("container_123")
        
        assert result is True
        mock_container_manager._kill_container.assert_called_once_with("container_123")
        mock_container_manager._cleanup_container.assert_called_once_with("container_123")
        
    @pytest.mark.asyncio
    async def test_cancel_execution_not_found(self):
        """Test cancelling non-existent container."""
        mock_container_manager = Mock()
        mock_container_manager.active_containers = {}
        
        executor = ClaudeExecutor(mock_container_manager)
        
        result = await executor.cancel_execution("container_999")
        
        assert result is False
        
    @pytest.mark.asyncio
    async def test_cancel_execution_exception(self):
        """Test cancellation with exception."""
        mock_container_manager = Mock()
        mock_container_manager.active_containers = {
            "container_123": {}
        }
        mock_container_manager._kill_container = AsyncMock(side_effect=Exception("Kill failed"))
        
        executor = ClaudeExecutor(mock_container_manager)
        
        result = await executor.cancel_execution("container_123")
        
        assert result is False


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_execute_with_empty_agent_context(self):
        """Test execution with empty agent context."""
        mock_container_manager = Mock(spec=ContainerManager)
        mock_container_manager.docker_client = Mock()
        mock_container_manager.create_container = AsyncMock(return_value="container_123")
        mock_container_manager.start_container = AsyncMock(return_value=True)
        mock_container_manager.wait_for_completion = AsyncMock(return_value={'success': True})
        
        executor = ClaudeExecutor(mock_container_manager)
        executor._load_workflow_config = AsyncMock(return_value={'name': 'test'})
        
        request = ClaudeCodeRunRequest(
            message="Fix bug",
            workflow_name="test"
        )
        
        # Empty context should not cause issues
        result = await executor.execute_claude_task(request, {})
        
        assert result['success'] is True
        
    @pytest.mark.asyncio
    async def test_execute_with_none_agent_context(self):
        """Test execution with None agent context."""
        mock_container_manager = Mock(spec=ContainerManager)
        mock_container_manager.docker_client = Mock()
        mock_container_manager.create_container = AsyncMock(return_value="container_123")
        mock_container_manager.start_container = AsyncMock(return_value=True)
        mock_container_manager.wait_for_completion = AsyncMock(return_value={'success': True})
        
        executor = ClaudeExecutor(mock_container_manager)
        executor._load_workflow_config = AsyncMock(return_value={'name': 'test'})
        
        request = ClaudeCodeRunRequest(
            message="Fix bug",
            workflow_name="test"
        )
        
        # None context should not cause issues
        result = await executor.execute_claude_task(request, None)
        
        assert result['success'] is True