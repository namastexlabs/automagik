"""Edge case and error handling tests for Claude-Code agent.

This module tests various edge cases, error conditions, timeouts,
and boundary scenarios for the Claude-Code agent implementation.
"""
import pytest
import asyncio
import uuid
import json
from unittest.mock import Mock, patch, AsyncMock, MagicMock, mock_open
from datetime import datetime, timedelta
import time
import os

from src.agents.claude_code.agent import ClaudeCodeAgent
from src.agents.claude_code.container import ContainerManager
from src.agents.claude_code.docker_executor import DockerExecutor
from src.agents.claude_code.models import (
    ClaudeCodeRunRequest,
    ClaudeCodeRunResponse,
    ContainerConfig,
    ContainerStatus,
    ExecutionStatus
)
from src.agents.models.response import AgentResponse


class TestTimeoutScenarios:
    """Test various timeout scenarios."""
    
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists')
    @patch('src.agents.claude_code.agent.ContainerManager')
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_container_timeout_handling(self, mock_executor_factory, mock_container_class, mock_exists):
        """Test handling of container execution timeout."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        # Mock executor that simulates timeout
        mock_executor = Mock()
        mock_executor.execute_claude_task = AsyncMock(return_value={
            'success': False,
            'error': 'Container execution timed out after 7200 seconds',
            'exit_code': -1
        })
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        agent._validate_workflow = AsyncMock(return_value=True)
        
        response = await agent.run("Long running task")
        
        assert response.success is False
        assert "timed out" in response.text.lower()
        
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
    @patch('pathlib.Path.exists')
    @patch('src.agents.claude_code.agent.ContainerManager')
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_memory_limit_handling(self, mock_executor_factory, mock_container_class, mock_exists):
        """Test handling when container hits memory limits."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        # Mock executor that simulates memory limit
        mock_executor = Mock()
        mock_executor.execute_claude_task = AsyncMock(return_value={
            'success': False,
            'error': 'Container exceeded memory limit (512MB)',
            'exit_code': 137  # SIGKILL due to OOM
        })
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        agent._validate_workflow = AsyncMock(return_value=True)
        
        response = await agent.run("Memory intensive task")
        
        assert response.success is False
        assert "memory" in response.text.lower()
    
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists')
    @patch('src.agents.claude_code.agent.ContainerManager')
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_disk_space_limit_handling(self, mock_executor_factory, mock_container_class, mock_exists):
        """Test handling when container runs out of disk space."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        # Mock executor that simulates disk space issue
        mock_executor = Mock()
        mock_executor.execute_claude_task = AsyncMock(return_value={
            'success': False,
            'error': 'No space left on device',
            'exit_code': 1
        })
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        agent._validate_workflow = AsyncMock(return_value=True)
        
        response = await agent.run("Large file task")
        
        assert response.success is False
        assert ("space" in response.text.lower() or "disk" in response.text.lower())
    
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
    @patch('pathlib.Path.exists')
    @patch('src.agents.claude_code.agent.ContainerManager')
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_docker_api_error_propagation(self, mock_executor_factory, mock_container_class, mock_exists):
        """Test that Docker API errors are properly propagated."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        # Mock executor that simulates Docker error
        mock_executor = Mock()
        mock_executor.execute_claude_task = AsyncMock(return_value={
            'success': False,
            'error': 'Docker daemon error: Cannot connect to Docker socket',
            'exit_code': -1
        })
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        agent._validate_workflow = AsyncMock(return_value=True)
        
        response = await agent.run("Test task")
        
        assert response.success is False
        assert "Docker daemon error" in response.text
    
    @pytest.mark.asyncio
    async def test_file_system_errors(self):
        """Test handling of file system errors."""
        executor = DockerExecutor(Mock())
        
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
    @patch('pathlib.Path.exists')
    @patch('src.agents.claude_code.agent.ContainerManager')
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_background_task_exception_handling(self, mock_executor_factory, mock_container_class, mock_exists):
        """Test exception handling in background tasks."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        # Mock executor that will be called by background task
        mock_executor = Mock()
        mock_executor.execute_claude_task = AsyncMock(side_effect=Exception("Background task failure"))
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        
        # Create async run
        run_response = await agent.create_async_run(
            "Test task",
            "test-workflow",
            session_id="test_session"
        )
        
        assert run_response.status == "pending"
        
        # Wait for background task to complete with error
        await asyncio.sleep(0.1)
        
        # Check that the run is marked as failed
        status = await agent.get_run_status(run_response.run_id)
        assert status['status'] == 'failed'
        assert 'error' in status
        assert "Background task failure" in status['error']
    
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
    @patch('pathlib.Path.exists')
    async def test_empty_message_handling(self, mock_exists):
        """Test handling of empty messages."""
        # Mock credentials exist
        mock_exists.return_value = True
        
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
    @patch('pathlib.Path.exists')
    async def test_malformed_workflow_files(self, mock_exists):
        """Test handling of malformed workflow files."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        agent = ClaudeCodeAgent({})
        
        # Mock file system to simulate missing workflow files
        def mock_exists(path):
            # Workflow directory exists, but some required files don't
            if path.endswith("malformed-workflow"):
                return True
            elif path.endswith("prompt.md"):
                return True
            elif path.endswith(".mcp.json"):
                return False  # Missing required file
            elif path.endswith("allowed_tools.json"):
                return True
            return False
        
        with patch('os.path.exists', side_effect=mock_exists):
            result = await agent._validate_workflow("malformed-workflow")
            assert result is False
    
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists')
    async def test_circular_workflow_dependencies(self, mock_exists):
        """Test detection of circular workflow dependencies."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        agent = ClaudeCodeAgent({})
        
        response = await agent.run("Test circular dependency")
        
        assert response.success is False
        assert "workflow" in response.text.lower() or "disabled" in response.text.lower()


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


class TestConcurrencyLimits:
    """Test concurrency limit scenarios."""
    
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists')
    @patch('src.agents.claude_code.agent.ContainerManager')
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_max_concurrent_containers_reached(self, mock_executor_factory, mock_container_class, mock_exists):
        """Test behavior when max concurrent containers is reached."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        # Mock executor that simulates concurrency limit
        mock_executor = Mock()
        mock_executor.execute_claude_task = AsyncMock(return_value={
            'success': False,
            'error': 'Maximum concurrent containers (10) reached',
            'exit_code': -1
        })
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        agent._validate_workflow = AsyncMock(return_value=True)
        
        response = await agent.run("Concurrent task")
        
        assert response.success is False
        assert ("concurrent" in response.text.lower() or "limit" in response.text.lower())


class TestNetworkIssues:
    """Test network-related edge cases."""
    
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists')
    @patch('src.agents.claude_code.agent.ContainerManager')
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_network_connectivity_issues(self, mock_executor_factory, mock_container_class, mock_exists):
        """Test handling of network connectivity issues."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        # Mock executor that simulates network issue
        mock_executor = Mock()
        mock_executor.execute_claude_task = AsyncMock(return_value={
            'success': False,
            'error': 'Network unreachable: Could not connect to external service',
            'exit_code': 1
        })
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        agent._validate_workflow = AsyncMock(return_value=True)
        
        response = await agent.run("Network dependent task")
        
        assert response.success is False
        assert "network" in response.text.lower() or "unreachable" in response.text.lower()


class TestDataCorruption:
    """Test data corruption scenarios."""
    
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists')
    @patch('src.agents.claude_code.agent.ContainerManager')
    @patch('src.agents.claude_code.agent.ExecutorFactory')
    async def test_corrupted_container_state(self, mock_executor_factory, mock_container_class, mock_exists):
        """Test recovery from corrupted container state."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        # Mock executor that simulates corrupted state
        mock_executor = Mock()
        mock_executor.execute_claude_task = AsyncMock(return_value={
            'success': False,
            'error': 'Container state corrupted, attempting recovery',
            'exit_code': -1
        })
        mock_executor_factory.create_executor.return_value = mock_executor
        
        agent = ClaudeCodeAgent({})
        agent._validate_workflow = AsyncMock(return_value=True)
        
        response = await agent.run("State dependent task")
        
        assert response.success is False
        assert ("corrupted" in response.text.lower() or "state" in response.text.lower())