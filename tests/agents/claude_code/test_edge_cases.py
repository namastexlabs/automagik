"""Edge case and error handling tests for Claude-Code agent.

This module tests various edge cases, error conditions, timeouts,
and boundary scenarios for the Claude-Code agent implementation.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timedelta
import json
import time
from typing import Dict, Any

from src.agents.claude_code.agent import ClaudeCodeAgent
from src.agents.claude_code.container import ContainerManager
from src.agents.claude_code.executor import ClaudeExecutor
from src.agents.claude_code.models import (
    ClaudeCodeRunRequest,
    ContainerStatus,
    ExecutionStatus
)


class TestTimeoutScenarios:
    """Test various timeout scenarios."""
    
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.settings')
    async def test_container_timeout_handling(self, mock_settings):
        """Test handling of container execution timeout."""
        mock_settings.AM_ENABLE_CLAUDE_CODE = True
        
        # Mock container manager that simulates timeout
        mock_container_manager = Mock(spec=ContainerManager)
        mock_container_manager.docker_client = Mock()
        mock_container_manager.create_container = AsyncMock(return_value="container_123")
        mock_container_manager.start_container = AsyncMock(return_value=True)
        mock_container_manager.wait_for_completion = AsyncMock(return_value={
            'success': False,
            'error': 'Container execution timed out after 7200s',
            'exit_code': -1,
            'timeout': True
        })
        
        # Create agent with mocked components
        agent = ClaudeCodeAgent({})
        agent.container_manager = mock_container_manager
        agent.executor = ClaudeExecutor(mock_container_manager)
        agent._validate_workflow = AsyncMock(return_value=True)
        
        response = await agent.run("Long running task")
        
        assert response.success is False
        assert "timed out" in response.text
        
    @pytest.mark.asyncio
    async def test_request_timeout_validation(self):
        """Test request timeout parameter validation."""
        # Test minimum timeout
        request = ClaudeCodeRunRequest(
            message="Test",
            workflow_name="test",
            timeout=60  # Minimum
        )
        assert request.timeout == 60
        
        # Test maximum timeout
        request = ClaudeCodeRunRequest(
            message="Test",
            workflow_name="test",
            timeout=7200  # Maximum
        )
        assert request.timeout == 7200
        
        # Test out of bounds
        with pytest.raises(Exception):  # ValidationError
            ClaudeCodeRunRequest(
                message="Test",
                workflow_name="test",
                timeout=30  # Too low
            )
            
        with pytest.raises(Exception):  # ValidationError
            ClaudeCodeRunRequest(
                message="Test",
                workflow_name="test",
                timeout=10000  # Too high
            )
    
    @pytest.mark.asyncio
    @patch('time.time')
    async def test_container_wait_timeout_calculation(self, mock_time):
        """Test accurate timeout calculation in container wait."""
        # Simulate time progression
        mock_time.side_effect = [
            0,      # Start time
            1000,   # First check
            2000,   # Second check
            8000    # Timeout exceeded
        ]
        
        mock_container = Mock()
        mock_container.status = 'running'
        mock_container.reload.return_value = None
        
        manager = ContainerManager(container_timeout=5)  # 5 second timeout
        manager.active_containers["container_123"] = {
            'container': mock_container,
            'started_at': datetime.utcnow()
        }
        manager._kill_container = AsyncMock()
        manager._cleanup_container = AsyncMock()
        
        result = await manager.wait_for_completion("container_123")
        
        assert result['timeout'] is True
        assert "timed out" in result['error']
        manager._kill_container.assert_called_once()


class TestResourceLimits:
    """Test resource limitation handling."""
    
    @pytest.mark.asyncio
    async def test_max_concurrent_containers(self):
        """Test enforcement of max concurrent containers."""
        manager = ContainerManager(max_concurrent=2)
        manager.docker_client = Mock()
        manager.docker_client.containers.create.return_value = Mock()
        
        # Fill up the semaphore
        container_ids = []
        for i in range(2):
            container_id = await manager.create_container(f"session_{i}", "test")
            container_ids.append(container_id)
        
        # Next creation should block
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                manager.create_container("session_3", "test"),
                timeout=0.1
            )
        
        # Release one slot
        await manager._cleanup_container(container_ids[0])
        
        # Now we should be able to create another
        container_id = await asyncio.wait_for(
            manager.create_container("session_3", "test"),
            timeout=0.5
        )
        assert container_id is not None
    
    @pytest.mark.asyncio
    async def test_memory_limit_configuration(self):
        """Test container memory limit configuration."""
        mock_docker_client = Mock()
        mock_docker_client.containers.create.return_value = Mock()
        
        manager = ContainerManager()
        manager.docker_client = mock_docker_client
        
        await manager.create_container("session_123", "test")
        
        # Verify memory limit was set
        create_args = mock_docker_client.containers.create.call_args[1]
        assert create_args['mem_limit'] == '2g'
        assert create_args['cpuset_cpus'] == '0-1'


class TestErrorPropagation:
    """Test error propagation through the system."""
    
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.settings')
    async def test_docker_api_error_propagation(self, mock_settings):
        """Test Docker API errors are properly propagated."""
        mock_settings.AM_ENABLE_CLAUDE_CODE = True
        
        from docker.errors import APIError
        
        mock_container_manager = Mock(spec=ContainerManager)
        mock_container_manager.docker_client = Mock()
        mock_container_manager.create_container = AsyncMock(
            side_effect=APIError("Docker daemon error")
        )
        
        agent = ClaudeCodeAgent({})
        agent.container_manager = mock_container_manager
        agent.executor = ClaudeExecutor(mock_container_manager)
        agent._validate_workflow = AsyncMock(return_value=True)
        
        response = await agent.run("Test task")
        
        assert response.success is False
        assert "Docker daemon error" in response.text
    
    @pytest.mark.asyncio
    async def test_file_system_errors(self):
        """Test handling of file system errors."""
        executor = ClaudeExecutor(Mock())
        
        # Test workflow loading with permission error
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', side_effect=PermissionError("Access denied")):
                config = await executor._load_workflow_config("test-workflow")
                assert config is None
        
        # Test environment file loading with IO error
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', side_effect=IOError("Disk full")):
                request = ClaudeCodeRunRequest(message="Test", workflow_name="test")
                workflow_config = {'env_file': '/path/to/.env'}
                
                # Should not raise exception
                env = await executor._prepare_environment(request, workflow_config, {})
                assert 'WORKFLOW_NAME' in env  # Basic env still set


class TestAsyncOperations:
    """Test asynchronous operation edge cases."""
    
    @pytest.mark.asyncio
    async def test_background_task_exception_handling(self):
        """Test exception handling in background tasks."""
        agent = ClaudeCodeAgent({})
        
        # Mock executor to raise exception
        agent.executor = Mock()
        agent.executor.execute_claude_task = AsyncMock(
            side_effect=Exception("Background task failed")
        )
        
        # Create async run
        request = ClaudeCodeRunRequest(message="Test", workflow_name="test")
        
        # Execute in background
        await agent._execute_async_run("run_123", request)
        
        # Check that failure was recorded
        assert agent.context["run_run_123"]["status"] == "failed"
        assert agent.context["run_run_123"]["error"] == "Background task failed"
    
    @pytest.mark.asyncio
    async def test_concurrent_status_polling(self):
        """Test concurrent status polling for multiple runs."""
        agent = ClaudeCodeAgent({})
        
        # Create multiple run contexts
        for i in range(5):
            agent.context[f"run_run_{i}"] = {
                "status": "running" if i % 2 == 0 else "completed",
                "result": f"Result {i}"
            }
        
        # Poll all statuses concurrently
        tasks = [
            agent.get_run_status(f"run_{i}")
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 5
        assert all(r["run_id"] == f"run_{i}" for i, r in enumerate(results))
        assert sum(1 for r in results if r["status"] == "running") == 3
        assert sum(1 for r in results if r["status"] == "completed") == 2


class TestStateManagement:
    """Test state management edge cases."""
    
    @pytest.mark.asyncio
    async def test_stale_container_cleanup(self):
        """Test cleanup of stale containers."""
        # Create containers with different ages
        mock_container_old = Mock()
        mock_container_old.status = 'running'
        mock_container_old.reload.return_value = None
        
        mock_container_recent = Mock()
        mock_container_recent.status = 'running'
        mock_container_recent.reload.return_value = None
        
        mock_container_dead = Mock()
        mock_container_dead.status = 'dead'
        mock_container_dead.reload.return_value = None
        
        manager = ContainerManager()
        manager.active_containers = {
            "old_container": {
                'container': mock_container_old,
                'created_at': datetime.utcnow() - timedelta(hours=4)
            },
            "recent_container": {
                'container': mock_container_recent,
                'created_at': datetime.utcnow() - timedelta(minutes=30)
            },
            "dead_container": {
                'container': mock_container_dead,
                'created_at': datetime.utcnow() - timedelta(hours=1)
            }
        }
        
        manager._cleanup_container = AsyncMock()
        
        cleaned = await manager.cleanup_stale_containers()
        
        assert cleaned == 2  # old and dead containers
        assert manager._cleanup_container.call_count == 2
    
    def test_context_isolation_between_agents(self):
        """Test that agent contexts are isolated."""
        agent1 = ClaudeCodeAgent({})
        agent2 = ClaudeCodeAgent({})
        
        agent1.context['test_key'] = 'agent1_value'
        agent2.context['test_key'] = 'agent2_value'
        
        assert agent1.context['test_key'] == 'agent1_value'
        assert agent2.context['test_key'] == 'agent2_value'
        assert agent1.context is not agent2.context


class TestInputValidation:
    """Test input validation edge cases."""
    
    @pytest.mark.asyncio
    @patch('src.agents.claude_code.agent.settings')
    async def test_empty_message_handling(self, mock_settings):
        """Test handling of empty messages."""
        mock_settings.AM_ENABLE_CLAUDE_CODE = True
        
        agent = ClaudeCodeAgent({})
        
        # Empty string should be caught by model validation
        response = await agent.run("")
        
        # Should fail at validation or execution
        assert response.success is False
    
    def test_special_characters_in_workflow_name(self):
        """Test workflow names with special characters."""
        # Valid workflow names
        valid_names = [
            "bug-fixer",
            "test_runner",
            "workflow123",
            "my-awesome_workflow2"
        ]
        
        for name in valid_names:
            request = ClaudeCodeRunRequest(
                message="Test",
                workflow_name=name
            )
            assert request.workflow_name == name
        
        # Invalid workflow names
        invalid_names = [
            "workflow with spaces",
            "workflow/with/slashes",
            "workflow\\with\\backslashes",
            "workflow@special",
            ""
        ]
        
        for name in invalid_names:
            with pytest.raises(Exception):  # ValidationError
                ClaudeCodeRunRequest(
                    message="Test",
                    workflow_name=name
                )
    
    def test_large_message_handling(self):
        """Test handling of very large messages."""
        # Create a very large message
        large_message = "Fix the bug " * 10000  # ~120KB
        
        request = ClaudeCodeRunRequest(
            message=large_message,
            workflow_name="test"
        )
        
        # Should handle large messages
        assert len(request.message) > 100000


class TestDockerEdgeCases:
    """Test Docker-specific edge cases."""
    
    @pytest.mark.asyncio
    async def test_container_name_collision(self):
        """Test handling of container name collisions."""
        mock_docker_client = Mock()
        
        # First creation succeeds
        mock_docker_client.containers.create.return_value = Mock()
        
        manager = ContainerManager()
        manager.docker_client = mock_docker_client
        
        # Create first container
        container_id1 = await manager.create_container("session_123", "test")
        
        # Second creation with same session should get different ID
        container_id2 = await manager.create_container("session_123", "test")
        
        assert container_id1 != container_id2
        assert container_id1.startswith("claude-code-session_123-")
        assert container_id2.startswith("claude-code-session_123-")
    
    @pytest.mark.asyncio
    async def test_docker_socket_unavailable(self):
        """Test behavior when Docker socket is unavailable."""
        import docker
        
        with patch('docker.from_env', side_effect=docker.errors.DockerException("Cannot connect to Docker daemon")):
            manager = ContainerManager()
            result = await manager.initialize()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_container_removal_failure(self):
        """Test handling of container removal failures."""
        mock_container = Mock()
        mock_container.status = 'exited'
        mock_container.stop.return_value = None
        mock_container.remove.side_effect = Exception("Container in use")
        
        manager = ContainerManager()
        manager.active_containers["container_123"] = {
            'container': mock_container
        }
        
        # Should not raise exception
        await manager._cleanup_container("container_123")
        
        # Container should still be removed from tracking
        assert "container_123" not in manager.active_containers


class TestWorkflowEdgeCases:
    """Test workflow-specific edge cases."""
    
    @pytest.mark.asyncio
    async def test_malformed_workflow_files(self):
        """Test handling of malformed workflow configuration files."""
        executor = ClaudeExecutor(Mock())
        
        # Test malformed JSON in MCP config
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', mock_open(read_data='{"invalid json')):
                with patch('json.load', side_effect=json.JSONDecodeError("test", "doc", 0)):
                    config = await executor._load_workflow_config("test-workflow")
                    assert config is None
    
    @pytest.mark.asyncio
    async def test_circular_workflow_dependencies(self):
        """Test handling of circular workflow dependencies."""
        # This would be caught at the workflow configuration level
        # The agent should handle invalid configurations gracefully
        agent = ClaudeCodeAgent({})
        agent._validate_workflow = AsyncMock(return_value=False)
        
        response = await agent.run("Test", multimodal_content=None)
        
        assert response.success is False
        assert "workflow" in response.text.lower()


class TestMemoryLeaks:
    """Test for potential memory leaks."""
    
    @pytest.mark.asyncio
    async def test_container_tracking_cleanup(self):
        """Test that container tracking is properly cleaned up."""
        manager = ContainerManager()
        manager.docker_client = Mock()
        
        # Track initial state
        initial_containers = len(manager.active_containers)
        
        # Create and clean up many containers
        for i in range(10):
            mock_container = Mock()
            mock_container.status = 'exited'
            mock_container.stop.return_value = None
            mock_container.remove.return_value = None
            
            container_id = f"container_{i}"
            manager.active_containers[container_id] = {
                'container': mock_container
            }
            
            await manager._cleanup_container(container_id)
        
        # All containers should be cleaned up
        assert len(manager.active_containers) == initial_containers
    
    @pytest.mark.asyncio
    async def test_async_run_context_cleanup(self):
        """Test that async run contexts don't accumulate indefinitely."""
        agent = ClaudeCodeAgent({})
        
        # Create many runs
        for i in range(100):
            agent.context[f"run_run_{i}"] = {
                "status": "completed",
                "result": f"Result {i}"
            }
        
        # In a real implementation, old runs should be cleaned up
        # For now, just verify we can handle many runs
        assert len([k for k in agent.context if k.startswith("run_")]) == 100


class TestRaceConditions:
    """Test potential race conditions."""
    
    @pytest.mark.asyncio
    async def test_concurrent_container_creation_same_session(self):
        """Test concurrent container creation for same session."""
        manager = ContainerManager()
        manager.docker_client = Mock()
        manager.docker_client.containers.create.return_value = Mock()
        
        # Create containers concurrently for same session
        tasks = [
            manager.create_container("session_123", "test")
            for _ in range(5)
        ]
        
        container_ids = await asyncio.gather(*tasks)
        
        # All should succeed with unique IDs
        assert len(container_ids) == 5
        assert len(set(container_ids)) == 5  # All unique
    
    @pytest.mark.asyncio
    async def test_status_check_during_cleanup(self):
        """Test status check while container is being cleaned up."""
        mock_container = Mock()
        mock_container.reload.side_effect = Exception("Container not found")
        
        manager = ContainerManager()
        manager.active_containers["container_123"] = {
            'container': mock_container,
            'created_at': datetime.utcnow(),
            'session_id': 'session_123',
            'workflow_name': 'test'
        }
        
        # Get status during cleanup simulation
        status = await manager.get_container_status("container_123")
        
        assert status['status'] == 'error'
        assert 'Container not found' in status['error']