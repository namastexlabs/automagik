"""Unit tests for ContainerManager implementation.

This module tests the Docker container lifecycle management including
initialization, container creation, execution, and cleanup.
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock, call
from datetime import datetime, timedelta
import json
import time

from src.agents.claude_code.container import ContainerManager, DOCKER_AVAILABLE


class TestContainerManagerInitialization:
    """Test ContainerManager initialization."""
    
    def test_init_without_docker(self):
        """Test initialization when Docker library is not available."""
        with patch('src.agents.claude_code.container.DOCKER_AVAILABLE', False):
            with pytest.raises(RuntimeError) as exc_info:
                ContainerManager()
            assert "Docker Python library not available" in str(exc_info.value)
    
    @patch('src.agents.claude_code.container.DOCKER_AVAILABLE', True)
    def test_init_with_defaults(self):
        """Test initialization with default values."""
        manager = ContainerManager()
        
        assert manager.docker_image == "claude-code-agent:latest"
        assert manager.container_timeout == 7200
        assert manager.max_concurrent == 10
        assert manager.docker_client is None
        assert len(manager.active_containers) == 0
        
    @patch('src.agents.claude_code.container.DOCKER_AVAILABLE', True)
    def test_init_with_custom_values(self):
        """Test initialization with custom values."""
        manager = ContainerManager(
            docker_image="custom-image:v2",
            container_timeout=3600,
            max_concurrent=5
        )
        
        assert manager.docker_image == "custom-image:v2"
        assert manager.container_timeout == 3600
        assert manager.max_concurrent == 5
        assert manager.container_semaphore._value == 5


class TestContainerManagerDockerInitialization:
    """Test Docker client initialization."""
    
    @pytest.mark.asyncio
    @patch('docker.from_env')
    async def test_initialize_success(self, mock_from_env):
        """Test successful Docker client initialization."""
        # Mock Docker client
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.images.get.return_value = Mock()  # Image exists
        mock_from_env.return_value = mock_client
        
        manager = ContainerManager()
        result = await manager.initialize()
        
        assert result is True
        assert manager.docker_client == mock_client
        mock_client.ping.assert_called_once()
        
    @pytest.mark.asyncio
    @patch('docker.from_env')
    async def test_initialize_docker_exception(self, mock_from_env):
        """Test initialization with Docker exception."""
        from docker.errors import DockerException
        mock_from_env.side_effect = DockerException("Docker not running")
        
        manager = ContainerManager()
        result = await manager.initialize()
        
        assert result is False
        assert manager.docker_client is None
        
    @pytest.mark.asyncio
    @patch('docker.from_env')
    async def test_initialize_unexpected_exception(self, mock_from_env):
        """Test initialization with unexpected exception."""
        mock_from_env.side_effect = Exception("Unexpected error")
        
        manager = ContainerManager()
        result = await manager.initialize()
        
        assert result is False
        
    @pytest.mark.asyncio
    @patch('docker.from_env')
    async def test_ensure_image_exists_found(self, mock_from_env):
        """Test when Docker image exists."""
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.images.get.return_value = Mock()  # Image exists
        mock_from_env.return_value = mock_client
        
        manager = ContainerManager()
        result = await manager.initialize()
        
        assert result is True
        mock_client.images.get.assert_called_once_with("claude-code-agent:latest")
        
    @pytest.mark.asyncio
    @patch('docker.from_env')
    @patch('os.path.exists')
    async def test_ensure_image_build(self, mock_exists, mock_from_env):
        """Test building Docker image when not found."""
        from docker.errors import ImageNotFound
        
        # Mock Docker client
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.images.get.side_effect = ImageNotFound("Image not found")
        
        # Mock successful build
        mock_build_result = (Mock(), [{'stream': 'Building...\n'}])
        mock_client.images.build.return_value = mock_build_result
        mock_from_env.return_value = mock_client
        
        # Mock Dockerfile exists
        mock_exists.return_value = True
        
        manager = ContainerManager()
        result = await manager.initialize()
        
        assert result is True
        mock_client.images.build.assert_called_once()
        build_args = mock_client.images.build.call_args[1]
        assert build_args['tag'] == "claude-code-agent:latest"
        assert build_args['rm'] is True
        
    @pytest.mark.asyncio
    @patch('docker.from_env')
    @patch('os.path.exists')
    async def test_ensure_image_build_no_dockerfile(self, mock_exists, mock_from_env):
        """Test error when Dockerfile not found."""
        from docker.errors import ImageNotFound
        
        # Mock Docker client
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.images.get.side_effect = ImageNotFound("Image not found")
        mock_from_env.return_value = mock_client
        
        # Mock Dockerfile doesn't exist
        mock_exists.return_value = False
        
        manager = ContainerManager()
        
        with pytest.raises(RuntimeError) as exc_info:
            await manager.initialize()
        assert "Dockerfile not found" in str(exc_info.value)


class TestContainerCreation:
    """Test container creation functionality."""
    
    @pytest.mark.asyncio
    @patch('docker.from_env')
    async def test_create_container_success(self, mock_from_env):
        """Test successful container creation."""
        # Mock Docker client and container
        mock_container = Mock()
        mock_container.id = "container_12345"
        
        mock_client = Mock()
        mock_client.containers.create.return_value = mock_container
        mock_from_env.return_value = mock_client
        
        manager = ContainerManager()
        manager.docker_client = mock_client
        
        container_id = await manager.create_container(
            session_id="session_123",
            workflow_name="test-workflow"
        )
        
        assert container_id.startswith("claude-code-session_123-")
        assert container_id in manager.active_containers
        assert manager.active_containers[container_id]['session_id'] == "session_123"
        assert manager.active_containers[container_id]['workflow_name'] == "test-workflow"
        assert manager.active_containers[container_id]['status'] == "created"
        
        # Verify container creation call
        mock_client.containers.create.assert_called_once()
        create_args = mock_client.containers.create.call_args[1]
        assert create_args['image'] == "claude-code-agent:latest"
        assert create_args['environment']['SESSION_ID'] == "session_123"
        assert create_args['environment']['WORKFLOW_NAME'] == "test-workflow"
        
    @pytest.mark.asyncio
    @patch('docker.from_env')
    async def test_create_container_with_environment(self, mock_from_env):
        """Test container creation with custom environment."""
        mock_container = Mock()
        mock_client = Mock()
        mock_client.containers.create.return_value = mock_container
        mock_from_env.return_value = mock_client
        
        manager = ContainerManager()
        manager.docker_client = mock_client
        
        custom_env = {"CUSTOM_VAR": "value"}
        container_id = await manager.create_container(
            session_id="session_123",
            workflow_name="test",
            environment=custom_env
        )
        
        create_args = mock_client.containers.create.call_args[1]
        assert create_args['environment']['CUSTOM_VAR'] == "value"
        assert create_args['environment']['SESSION_ID'] == "session_123"
        
    @pytest.mark.asyncio
    @patch('docker.from_env')
    @patch('os.path.exists')
    async def test_create_container_with_workflow_volume(self, mock_exists, mock_from_env):
        """Test container creation with workflow volume mount."""
        mock_container = Mock()
        mock_client = Mock()
        mock_client.containers.create.return_value = mock_container
        mock_from_env.return_value = mock_client
        
        # Mock workflow directory exists
        mock_exists.return_value = True
        
        manager = ContainerManager()
        manager.docker_client = mock_client
        
        container_id = await manager.create_container(
            session_id="session_123",
            workflow_name="test-workflow"
        )
        
        create_args = mock_client.containers.create.call_args[1]
        volumes = create_args['volumes']
        
        # Check workspace volume
        assert any("claude-workspace-session_123" in vol for vol in volumes)
        
    @pytest.mark.asyncio
    @patch('docker.from_env')
    async def test_create_container_docker_client_not_initialized(self, mock_from_env):
        """Test container creation when Docker client not initialized."""
        mock_container = Mock()
        mock_client = Mock()
        mock_client.ping.return_value = True
        mock_client.images.get.return_value = Mock()
        mock_client.containers.create.return_value = mock_container
        mock_from_env.return_value = mock_client
        
        manager = ContainerManager()
        # docker_client is None, should initialize
        
        container_id = await manager.create_container(
            session_id="session_123",
            workflow_name="test"
        )
        
        assert manager.docker_client is not None
        assert container_id in manager.active_containers
        
    @pytest.mark.asyncio
    @patch('docker.from_env')
    async def test_create_container_exception(self, mock_from_env):
        """Test container creation with exception."""
        mock_client = Mock()
        mock_client.containers.create.side_effect = Exception("Docker error")
        mock_from_env.return_value = mock_client
        
        manager = ContainerManager()
        manager.docker_client = mock_client
        
        # Verify semaphore is acquired and released
        initial_value = manager.container_semaphore._value
        
        with pytest.raises(Exception):
            await manager.create_container(
                session_id="session_123",
                workflow_name="test"
            )
        
        # Semaphore should be released
        assert manager.container_semaphore._value == initial_value
        
    @pytest.mark.asyncio
    async def test_create_container_concurrency_limit(self):
        """Test container creation respects concurrency limit."""
        manager = ContainerManager(max_concurrent=2)
        manager.docker_client = Mock()
        
        # Acquire all semaphore slots
        await manager.container_semaphore.acquire()
        await manager.container_semaphore.acquire()
        
        # Next creation should wait (we'll timeout to test)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                manager.create_container("session_123", "test"),
                timeout=0.1
            )


class TestContainerExecution:
    """Test container execution functionality."""
    
    @pytest.mark.asyncio
    async def test_start_container_success(self):
        """Test successful container start."""
        mock_container = Mock()
        mock_container.start.return_value = None
        mock_container.attrs = {'Config': {'Cmd': None}}
        
        manager = ContainerManager()
        manager.active_containers["container_123"] = {
            'container': mock_container,
            'status': 'created'
        }
        
        result = await manager.start_container(
            "container_123",
            ["claude", "--max-turns", "30"]
        )
        
        assert result is True
        mock_container.start.assert_called_once()
        assert manager.active_containers["container_123"]['status'] == 'running'
        assert manager.active_containers["container_123"]['command'] == ["claude", "--max-turns", "30"]
        
    @pytest.mark.asyncio
    async def test_start_container_not_found(self):
        """Test starting non-existent container."""
        manager = ContainerManager()
        
        result = await manager.start_container(
            "container_999",
            ["claude", "--max-turns", "30"]
        )
        
        assert result is False
        
    @pytest.mark.asyncio
    async def test_start_container_exception(self):
        """Test container start with exception."""
        mock_container = Mock()
        mock_container.start.side_effect = Exception("Start failed")
        mock_container.attrs = {'Config': {'Cmd': None}}
        
        manager = ContainerManager()
        manager.active_containers["container_123"] = {
            'container': mock_container,
            'status': 'created'
        }
        manager._cleanup_container = AsyncMock()
        
        result = await manager.start_container(
            "container_123",
            ["claude", "--max-turns", "30"]
        )
        
        assert result is False
        manager._cleanup_container.assert_called_once_with("container_123")


class TestContainerWaitForCompletion:
    """Test waiting for container completion."""
    
    @pytest.mark.asyncio
    async def test_wait_for_completion_success(self):
        """Test successful container completion."""
        mock_container = Mock()
        mock_container.status = 'running'
        mock_container.attrs = {'State': {'ExitCode': 0}}
        mock_container.logs.return_value = b'Execution logs\n{"result": "Task completed", "session_id": "123"}'
        
        # Mock reload to simulate status change
        statuses = ['running', 'running', 'exited']
        mock_container.reload.side_effect = lambda: setattr(mock_container, 'status', statuses.pop(0))
        
        manager = ContainerManager()
        manager.active_containers["container_123"] = {
            'container': mock_container,
            'started_at': datetime.utcnow()
        }
        manager._cleanup_container = AsyncMock()
        
        result = await manager.wait_for_completion("container_123")
        
        assert result['success'] is True
        assert result['exit_code'] == 0
        assert result['result'] == "Task completed"
        assert 'execution_time' in result
        manager._cleanup_container.assert_called_once_with("container_123")
        
    @pytest.mark.asyncio
    async def test_wait_for_completion_container_not_found(self):
        """Test waiting for non-existent container."""
        manager = ContainerManager()
        
        result = await manager.wait_for_completion("container_999")
        
        assert result['success'] is False
        assert "not found" in result['error']
        assert result['exit_code'] == -1
        
    @pytest.mark.asyncio
    async def test_wait_for_completion_timeout(self):
        """Test container execution timeout."""
        mock_container = Mock()
        mock_container.status = 'running'
        mock_container.reload.return_value = None  # Status doesn't change
        
        # Use a very short timeout for testing
        manager = ContainerManager(container_timeout=0.1)  # 0.1 second timeout
        manager.active_containers["container_123"] = {
            'container': mock_container,
            'started_at': datetime.utcnow()
        }
        manager._kill_container = AsyncMock()
        manager._cleanup_container = AsyncMock()
        
        # The timeout will naturally occur due to the short timeout
        result = await manager.wait_for_completion("container_123")
        
        assert result['success'] is False
        assert "timed out" in result['error']
        assert result['timeout'] is True
        manager._kill_container.assert_called_once_with("container_123")
        
    @pytest.mark.asyncio
    async def test_wait_for_completion_failed_exit(self):
        """Test container with non-zero exit code."""
        mock_container = Mock()
        mock_container.status = 'exited'
        mock_container.attrs = {'State': {'ExitCode': 1}}
        mock_container.logs.return_value = b'Error logs'
        mock_container.reload.return_value = None
        
        manager = ContainerManager()
        manager.active_containers["container_123"] = {
            'container': mock_container,
            'started_at': datetime.utcnow()
        }
        manager._cleanup_container = AsyncMock()
        
        result = await manager.wait_for_completion("container_123")
        
        assert result['success'] is False
        assert result['exit_code'] == 1
        assert "exited with code 1" in result['error']
        
    @pytest.mark.asyncio
    async def test_wait_for_completion_json_extraction(self):
        """Test JSON result extraction from logs."""
        logs_content = """
        Starting execution...
        Processing task...
        {"result": "Fixed bug", "session_id": "sess_123", "exit_code": 0}
        Completed
        """
        
        mock_container = Mock()
        mock_container.status = 'exited'
        mock_container.attrs = {'State': {'ExitCode': 0}}
        mock_container.logs.return_value = logs_content.encode('utf-8')
        mock_container.reload.return_value = None
        
        manager = ContainerManager()
        manager.active_containers["container_123"] = {
            'container': mock_container,
            'started_at': datetime.utcnow()
        }
        manager._cleanup_container = AsyncMock()
        
        result = await manager.wait_for_completion("container_123")
        
        assert result['success'] is True
        assert result['result'] == "Fixed bug"
        assert result['session_id'] == "sess_123"
        assert result['claude_exit_code'] == 0


class TestContainerCleanup:
    """Test container cleanup functionality."""
    
    @pytest.mark.asyncio
    async def test_kill_container(self):
        """Test killing a container."""
        mock_container = Mock()
        
        manager = ContainerManager()
        manager.active_containers["container_123"] = {
            'container': mock_container
        }
        
        await manager._kill_container("container_123")
        
        mock_container.kill.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_kill_container_not_found(self):
        """Test killing non-existent container."""
        manager = ContainerManager()
        
        # Should not raise exception
        await manager._kill_container("container_999")
        
    @pytest.mark.asyncio
    async def test_cleanup_container(self):
        """Test cleaning up a container."""
        mock_container = Mock()
        mock_container.status = 'running'
        
        manager = ContainerManager()
        manager.active_containers["container_123"] = {
            'container': mock_container
        }
        
        # Track semaphore value
        initial_value = manager.container_semaphore._value
        await manager.container_semaphore.acquire()  # Simulate container using slot
        
        await manager._cleanup_container("container_123")
        
        mock_container.stop.assert_called_once_with(timeout=10)
        mock_container.remove.assert_called_once()
        assert "container_123" not in manager.active_containers
        assert manager.container_semaphore._value == initial_value  # Released
        
    @pytest.mark.asyncio
    async def test_cleanup_container_already_stopped(self):
        """Test cleaning up already stopped container."""
        mock_container = Mock()
        mock_container.status = 'exited'
        
        manager = ContainerManager()
        manager.active_containers["container_123"] = {
            'container': mock_container
        }
        
        await manager._cleanup_container("container_123")
        
        mock_container.stop.assert_not_called()
        mock_container.remove.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_cleanup_container_exception(self):
        """Test cleanup with exceptions."""
        mock_container = Mock()
        mock_container.status = 'running'
        mock_container.stop.side_effect = Exception("Stop failed")
        mock_container.remove.side_effect = Exception("Remove failed")
        
        manager = ContainerManager()
        manager.active_containers["container_123"] = {
            'container': mock_container
        }
        
        # Should not raise exception
        await manager._cleanup_container("container_123")
        
        # Container should still be removed from tracking
        assert "container_123" not in manager.active_containers


class TestContainerStatus:
    """Test container status functionality."""
    
    @pytest.mark.asyncio
    async def test_get_container_status(self):
        """Test getting container status."""
        mock_container = Mock()
        mock_container.status = 'running'
        mock_container.reload.return_value = None
        
        created_at = datetime.utcnow()
        manager = ContainerManager()
        manager.active_containers["container_123"] = {
            'container': mock_container,
            'created_at': created_at,
            'session_id': 'session_123',
            'workflow_name': 'test'
        }
        
        status = await manager.get_container_status("container_123")
        
        assert status['status'] == 'running'
        assert status['session_id'] == 'session_123'
        assert status['workflow_name'] == 'test'
        mock_container.reload.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_get_container_status_not_found(self):
        """Test getting status of non-existent container."""
        manager = ContainerManager()
        
        status = await manager.get_container_status("container_999")
        
        assert status['status'] == 'not_found'
        
    @pytest.mark.asyncio
    async def test_list_active_containers(self):
        """Test listing active containers."""
        mock_container1 = Mock()
        mock_container1.status = 'running'
        mock_container1.reload.return_value = None
        
        mock_container2 = Mock()
        mock_container2.status = 'exited'
        mock_container2.reload.return_value = None
        
        manager = ContainerManager()
        manager.active_containers = {
            "container_1": {
                'container': mock_container1,
                'created_at': datetime.utcnow(),
                'session_id': 'session_1',
                'workflow_name': 'test1'
            },
            "container_2": {
                'container': mock_container2,
                'created_at': datetime.utcnow(),
                'started_at': datetime.utcnow(),
                'session_id': 'session_2',
                'workflow_name': 'test2'
            }
        }
        
        containers = await manager.list_active_containers()
        
        assert len(containers) == 2
        assert containers[0]['container_id'] == "container_1"
        assert containers[0]['status'] == 'running'
        assert containers[1]['container_id'] == "container_2"
        assert containers[1]['status'] == 'exited'
        assert containers[1]['started_at'] is not None


class TestContainerStaleCleaning:
    """Test stale container cleanup."""
    
    @pytest.mark.asyncio
    async def test_cleanup_stale_containers(self):
        """Test cleaning up stale containers."""
        mock_container_old = Mock()
        mock_container_old.status = 'running'
        mock_container_old.reload.return_value = None
        
        mock_container_dead = Mock()
        mock_container_dead.status = 'dead'
        mock_container_dead.reload.return_value = None
        
        mock_container_recent = Mock()
        mock_container_recent.status = 'running'
        mock_container_recent.reload.return_value = None
        
        manager = ContainerManager()
        manager.active_containers = {
            "container_old": {
                'container': mock_container_old,
                'created_at': datetime.utcnow() - timedelta(hours=4)  # Too old
            },
            "container_dead": {
                'container': mock_container_dead,
                'created_at': datetime.utcnow()
            },
            "container_recent": {
                'container': mock_container_recent,
                'created_at': datetime.utcnow()  # Recent
            }
        }
        
        manager._cleanup_container = AsyncMock()
        
        count = await manager.cleanup_stale_containers()
        
        assert count == 2
        assert manager._cleanup_container.call_count == 2
        manager._cleanup_container.assert_any_call("container_old")
        manager._cleanup_container.assert_any_call("container_dead")
        
    @pytest.mark.asyncio
    async def test_cleanup_stale_containers_exception(self):
        """Test stale cleanup with exceptions."""
        mock_container = Mock()
        mock_container.reload.side_effect = Exception("Reload failed")
        
        manager = ContainerManager()
        manager.active_containers = {
            "container_error": {
                'container': mock_container,
                'created_at': datetime.utcnow()
            }
        }
        
        manager._cleanup_container = AsyncMock()
        
        count = await manager.cleanup_stale_containers()
        
        assert count == 1
        manager._cleanup_container.assert_called_once_with("container_error")


class TestContainerManagerCleanup:
    """Test overall manager cleanup."""
    
    @pytest.mark.asyncio
    @patch('docker.from_env')
    async def test_cleanup(self, mock_from_env):
        """Test manager cleanup."""
        mock_client = Mock()
        mock_from_env.return_value = mock_client
        
        mock_container1 = Mock()
        mock_container2 = Mock()
        
        manager = ContainerManager()
        manager.docker_client = mock_client
        manager.active_containers = {
            "container_1": {'container': mock_container1},
            "container_2": {'container': mock_container2}
        }
        
        manager._cleanup_container = AsyncMock()
        
        await manager.cleanup()
        
        assert manager._cleanup_container.call_count == 2
        mock_client.close.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_cleanup_no_docker_client(self):
        """Test cleanup when Docker client not initialized."""
        manager = ContainerManager()
        
        # Should not raise exception
        await manager.cleanup()
        
    @pytest.mark.asyncio
    @patch('docker.from_env')
    async def test_cleanup_docker_close_exception(self, mock_from_env):
        """Test cleanup with Docker client close exception."""
        mock_client = Mock()
        mock_client.close.side_effect = Exception("Close failed")
        mock_from_env.return_value = mock_client
        
        manager = ContainerManager()
        manager.docker_client = mock_client
        
        # Should not raise exception
        await manager.cleanup()


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_concurrent_container_creation(self):
        """Test creating multiple containers concurrently."""
        manager = ContainerManager(max_concurrent=3)
        manager.docker_client = Mock()
        manager.docker_client.containers.create.return_value = Mock()
        
        # Create multiple containers concurrently
        tasks = [
            manager.create_container(f"session_{i}", "test")
            for i in range(3)
        ]
        
        container_ids = await asyncio.gather(*tasks)
        
        assert len(container_ids) == 3
        assert len(manager.active_containers) == 3
        
    @pytest.mark.asyncio
    async def test_container_status_reload_exception(self):
        """Test container status with reload exception."""
        mock_container = Mock()
        mock_container.reload.side_effect = Exception("Docker connection lost")
        
        manager = ContainerManager()
        manager.active_containers["container_123"] = {
            'container': mock_container,
            'created_at': datetime.utcnow(),
            'session_id': 'session_123',
            'workflow_name': 'test'
        }
        
        status = await manager.get_container_status("container_123")
        
        assert status['status'] == 'error'
        assert 'Docker connection lost' in status['error']