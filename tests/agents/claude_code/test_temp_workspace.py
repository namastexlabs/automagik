"""Unit tests for temporary workspace functionality in ClaudeCodeAgent.

This module tests the temporary workspace creation, validation, and cleanup
functionality for the Claude Code agent.
"""
import pytest
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.agents.claude_code.models import ClaudeCodeRunRequest
from src.agents.claude_code.cli_environment import CLIEnvironmentManager
from src.agents.claude_code.sdk_execution_strategies import ExecutionStrategies


class TestTempWorkspaceCreation:
    """Test temporary workspace creation functionality."""
    
    @pytest.mark.asyncio
    async def test_create_temp_workspace(self):
        """Test basic temporary workspace creation."""
        env_manager = CLIEnvironmentManager()
        
        user_id = "test_user_123"
        run_id = "test_run_456"
        
        # Create temp workspace
        workspace_path = await env_manager.create_temp_workspace(user_id, run_id)
        
        # Verify path structure
        assert workspace_path == Path(f"/tmp/claude-code-temp/{user_id}/workspace_{run_id}")
        assert workspace_path.exists()
        assert workspace_path.is_dir()
        
        # Verify it's tracked as active
        assert run_id in env_manager.active_workspaces
        assert env_manager.active_workspaces[run_id] == workspace_path
        
        # Cleanup
        await env_manager.cleanup_temp_workspace(workspace_path)
        assert not workspace_path.exists()
    
    @pytest.mark.asyncio
    async def test_temp_workspace_cleanup(self):
        """Test temporary workspace cleanup functionality."""
        env_manager = CLIEnvironmentManager()
        
        user_id = "cleanup_user"
        run_id = "cleanup_run"
        
        # Create temp workspace
        workspace_path = await env_manager.create_temp_workspace(user_id, run_id)
        
        # Add some test files
        test_file = workspace_path / "test.txt"
        test_file.write_text("test content")
        
        test_dir = workspace_path / "subdir"
        test_dir.mkdir()
        (test_dir / "nested.txt").write_text("nested content")
        
        # Cleanup
        cleanup_success = await env_manager.cleanup_temp_workspace(workspace_path)
        
        # Verify cleanup
        assert cleanup_success is True
        assert not workspace_path.exists()
        assert not test_file.exists()
        assert not test_dir.exists()
    
    @pytest.mark.asyncio
    async def test_cleanup_safety_check(self):
        """Test that cleanup refuses to delete non-temp workspaces."""
        env_manager = CLIEnvironmentManager()
        
        # Try to cleanup a non-temp path
        non_temp_path = Path("/home/user/important_files")
        
        cleanup_success = await env_manager.cleanup_temp_workspace(non_temp_path)
        
        # Should refuse to cleanup
        assert cleanup_success is False


class TestTempWorkspaceValidation:
    """Test parameter validation for temp workspaces."""
    
    def test_temp_workspace_incompatible_with_repository_url(self):
        """Test that temp_workspace cannot be used with repository_url."""
        with pytest.raises(ValueError) as exc_info:
            ClaudeCodeRunRequest(
                message="Test task",
                workflow_name="test",
                temp_workspace=True,
                repository_url="https://github.com/test/repo.git"
            )
        
        assert "temp_workspace cannot be used with: repository_url" in str(exc_info.value)
    
    def test_temp_workspace_incompatible_with_git_branch(self):
        """Test that temp_workspace cannot be used with git_branch."""
        with pytest.raises(ValueError) as exc_info:
            ClaudeCodeRunRequest(
                message="Test task",
                workflow_name="test",
                temp_workspace=True,
                git_branch="feature/test"
            )
        
        assert "temp_workspace cannot be used with: git_branch" in str(exc_info.value)
    
    def test_temp_workspace_incompatible_with_auto_merge(self):
        """Test that temp_workspace cannot be used with auto_merge."""
        with pytest.raises(ValueError) as exc_info:
            ClaudeCodeRunRequest(
                message="Test task",
                workflow_name="test",
                temp_workspace=True,
                auto_merge=True
            )
        
        assert "temp_workspace cannot be used with: auto_merge" in str(exc_info.value)
    
    def test_temp_workspace_multiple_incompatible_params(self):
        """Test error message with multiple incompatible parameters."""
        with pytest.raises(ValueError) as exc_info:
            ClaudeCodeRunRequest(
                message="Test task",
                workflow_name="test",
                temp_workspace=True,
                repository_url="https://github.com/test/repo.git",
                git_branch="main",
                auto_merge=True
            )
        
        error_msg = str(exc_info.value)
        assert "temp_workspace cannot be used with:" in error_msg
        assert "repository_url" in error_msg
        assert "git_branch" in error_msg
        assert "auto_merge" in error_msg


class TestTempWorkspaceExecution:
    """Test temp workspace execution in SDK strategies."""
    
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.sdk_execution_strategies.query')
    @patch('src.agents.claude_code.sdk_execution_strategies.ensure_node_in_path')
    async def test_execute_with_temp_workspace(self, mock_ensure_node, mock_query):
        """Test execution with temporary workspace."""
        # Setup mocks
        env_manager = Mock(spec=CLIEnvironmentManager)
        temp_workspace = Path("/tmp/claude-code-temp/user123/workspace_run456")
        env_manager.create_temp_workspace = AsyncMock(return_value=temp_workspace)
        env_manager.cleanup_temp_workspace = AsyncMock(return_value=True)
        
        # Mock query to return an async generator
        async def mock_generator():
            yield  # Empty generator that completes immediately
        
        mock_query.return_value = mock_generator()
        
        # Create execution strategy
        strategy = ExecutionStrategies(environment_manager=env_manager)
        
        # Create request with temp_workspace
        request = ClaudeCodeRunRequest(
            message="Test task",
            workflow_name="test",
            temp_workspace=True,
            run_id="run456"
        )
        
        agent_context = {
            "user_id": "user123",
            "workspace": "/ignored/path"  # Should be ignored when temp_workspace=True
        }
        
        # Execute
        result = await strategy.execute_simple(request, agent_context)
        
        # Verify temp workspace was created
        env_manager.create_temp_workspace.assert_called_once_with("user123", "run456")
        
        # Verify cleanup was called
        env_manager.cleanup_temp_workspace.assert_called_once_with(temp_workspace)
        
        # Verify result contains temp workspace path
        assert result['workspace_path'] == str(temp_workspace)
        assert result['success'] is True
    
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.sdk_execution_strategies.query')
    async def test_temp_workspace_cleanup_on_error(self, mock_query):
        """Test that temp workspace is cleaned up even on error."""
        # Setup mocks
        env_manager = Mock(spec=CLIEnvironmentManager)
        temp_workspace = Path("/tmp/claude-code-temp/user456/workspace_error")
        env_manager.create_temp_workspace = AsyncMock(return_value=temp_workspace)
        env_manager.cleanup_temp_workspace = AsyncMock(return_value=True)
        
        # Mock query to raise an error
        mock_query.side_effect = Exception("Test execution error")
        
        # Create execution strategy
        strategy = ExecutionStrategies(environment_manager=env_manager)
        
        # Create request with temp_workspace
        request = ClaudeCodeRunRequest(
            message="Test task",
            workflow_name="test",
            temp_workspace=True,
            run_id="error_run"
        )
        
        agent_context = {
            "user_id": "user456"
        }
        
        # Execute and expect error
        result = await strategy.execute_simple(request, agent_context)
        
        # Verify cleanup was still called despite error
        env_manager.cleanup_temp_workspace.assert_called_once_with(temp_workspace)
        
        # Verify error result
        assert result['success'] is False
        assert "Test execution error" in result['result']


class TestTempWorkspaceIntegration:
    """Integration tests for temp workspace with full workflow."""
    
    @pytest.mark.asyncio
    async def test_temp_workspace_full_lifecycle(self):
        """Test full lifecycle of temp workspace creation and cleanup."""
        env_manager = CLIEnvironmentManager()
        
        user_id = "integration_user"
        run_id = "integration_run"
        
        # Create temp workspace
        workspace_path = await env_manager.create_temp_workspace(user_id, run_id)
        
        # Simulate work in the workspace
        work_file = workspace_path / "work_output.txt"
        work_file.write_text("Work completed successfully")
        
        config_dir = workspace_path / ".config"
        config_dir.mkdir()
        (config_dir / "settings.json").write_text('{"test": true}')
        
        # Verify workspace is functional
        assert work_file.exists()
        assert work_file.read_text() == "Work completed successfully"
        assert (config_dir / "settings.json").exists()
        
        # Get workspace info
        info = await env_manager.get_workspace_info(run_id)
        assert info is not None
        assert info['run_id'] == run_id
        assert info['path'] == str(workspace_path)
        assert info['file_count'] >= 2  # At least our two files
        
        # Cleanup
        cleanup_success = await env_manager.cleanup_temp_workspace(workspace_path)
        assert cleanup_success is True
        
        # Verify complete cleanup
        assert not workspace_path.exists()
        assert not work_file.exists()
        assert not config_dir.exists()
        
        # Verify removed from active workspaces
        info_after = await env_manager.get_workspace_info(run_id)
        assert info_after is None


# Cleanup function to ensure test workspaces are removed
def teardown_module():
    """Clean up any test workspaces that might remain."""
    temp_base = Path("/tmp/claude-code-temp")
    if temp_base.exists():
        # Only clean up test users
        for user_dir in temp_base.iterdir():
            if user_dir.name.startswith(("test_", "cleanup_", "integration_")):
                shutil.rmtree(user_dir, ignore_errors=True)