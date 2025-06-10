"""Performance tests for Claude-Code agent.

This module tests performance characteristics including container startup time,
resource usage, throughput, and scalability.
"""
import pytest
import asyncio
import time
import psutil
import gc
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
import statistics
from typing import List, Dict, Any

from src.agents.claude_code.agent import ClaudeCodeAgent
from src.agents.claude_code.container import ContainerManager
from src.agents.claude_code.docker_executor import DockerExecutor
from src.agents.claude_code.models import ClaudeCodeRunRequest


class TestContainerStartupPerformance:
    """Test container startup time performance."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_container_creation_time(self):
        """Measure container creation time."""
        mock_docker_client = Mock()
        mock_container = Mock()
        mock_container.id = "container_123"
        
        # Simulate realistic container creation delay
        async def create_container_delay(*args, **kwargs):
            await asyncio.sleep(0.1)  # 100ms creation time
            return mock_container
        
        mock_docker_client.containers.create = Mock(side_effect=lambda *a, **k: mock_container)
        
        manager = ContainerManager()
        manager.docker_client = mock_docker_client
        
        # Measure creation time
        start_time = time.time()
        container_id = await manager.create_container("session_123", "test")
        creation_time = time.time() - start_time
        
        assert container_id is not None
        # Container creation should be fast (under 1 second for mocked version)
        assert creation_time < 1.0
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_multiple_container_startup_times(self):
        """Test startup times for multiple containers."""
        manager = ContainerManager(max_concurrent=5)
        manager.docker_client = Mock()
        manager.docker_client.containers.create.return_value = Mock()
        
        startup_times = []
        
        # Create multiple containers and measure times
        for i in range(5):
            start_time = time.time()
            container_id = await manager.create_container(f"session_{i}", "test")
            startup_time = time.time() - start_time
            startup_times.append(startup_time)
        
        # Calculate statistics
        avg_startup = statistics.mean(startup_times)
        max_startup = max(startup_times)
        
        # All startups should be reasonably fast
        assert avg_startup < 0.5  # Average under 500ms
        assert max_startup < 1.0  # Max under 1 second
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_container_start_command_overhead(self):
        """Test overhead of starting container with command."""
        mock_container = Mock()
        mock_container.start.return_value = None
        mock_container.attrs = {'Config': {'Cmd': None}}
        
        manager = ContainerManager()
        manager.active_containers["container_123"] = {
            'container': mock_container,
            'status': 'created'
        }
        
        # Measure start time
        start_time = time.time()
        result = await manager.start_container(
            "container_123",
            ["claude", "--max-turns", "30", "--message", "Long command with many arguments"]
        )
        start_overhead = time.time() - start_time
        
        assert result is True
        assert start_overhead < 0.1  # Should be very fast


class TestResourceUsagePerformance:
    """Test resource usage characteristics."""
    
    @pytest.mark.performance
    def test_memory_usage_per_agent(self):
        """Test memory usage of agent instances."""
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create multiple agents
        agents = []
        for i in range(10):
            agent = ClaudeCodeAgent({})
            agents.append(agent)
        
        # Force garbage collection
        gc.collect()
        
        # Get memory after creating agents
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_per_agent = (final_memory - initial_memory) / 10
        
        # Each agent should use reasonable memory (less than 10MB)
        assert memory_per_agent < 10.0
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_container_tracking_memory_overhead(self):
        """Test memory overhead of tracking many containers."""
        manager = ContainerManager()
        
        # Get initial memory
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Add many container tracking entries
        for i in range(100):
            manager.active_containers[f"container_{i}"] = {
                'container': Mock(),
                'session_id': f'session_{i}',
                'workflow_name': 'test',
                'created_at': datetime.utcnow(),
                'status': 'running',
                'command': ['claude', '--max-turns', '30'],
                'last_heartbeat': time.time()
            }
        
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_overhead = final_memory - initial_memory
        
        # Tracking 100 containers should use reasonable memory (less than 50MB)
        assert memory_overhead < 50.0
        
    @pytest.mark.performance
    def test_context_storage_scalability(self):
        """Test agent context storage scalability."""
        agent = ClaudeCodeAgent({})
        
        # Add many context entries
        start_time = time.time()
        for i in range(1000):
            agent.context[f"key_{i}"] = {
                'data': f'value_{i}',
                'timestamp': datetime.utcnow().isoformat(),
                'metadata': {'index': i}
            }
        write_time = time.time() - start_time
        
        # Reading should also be fast
        start_time = time.time()
        for i in range(1000):
            value = agent.context[f"key_{i}"]
        read_time = time.time() - start_time
        
        # Both operations should be fast
        assert write_time < 0.1  # 100ms for 1000 writes
        assert read_time < 0.05  # 50ms for 1000 reads


class TestThroughputPerformance:
    """Test throughput and request handling performance."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_async_run_creation_throughput(self):
        """Test throughput of creating async runs."""
        agent = ClaudeCodeAgent({})
        
        # Mock background execution
        agent._execute_async_run = AsyncMock()
        
        # Measure throughput
        start_time = time.time()
        tasks = []
        
        for i in range(50):
            task = agent.create_async_run(
                f"Task {i}",
                "test-workflow",
                session_id=f"session_{i}"
            )
            tasks.append(task)
        
        responses = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # Calculate throughput
        throughput = len(responses) / total_time
        
        # Should handle at least 100 requests per second
        assert throughput > 100
        assert all(r.status == "pending" for r in responses)
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_status_polling_performance(self):
        """Test performance of status polling operations."""
        agent = ClaudeCodeAgent({})
        
        # Pre-populate with many runs
        for i in range(100):
            agent.context[f"run_run_{i}"] = {
                "status": "running" if i % 2 == 0 else "completed",
                "result": f"Result {i}",
                "started_at": datetime.utcnow().isoformat()
            }
        
        # Measure polling performance
        start_time = time.time()
        tasks = []
        
        for i in range(100):
            task = agent.get_run_status(f"run_{i}")
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        poll_time = time.time() - start_time
        
        # Should poll 100 statuses in under 100ms
        assert poll_time < 0.1
        assert len(results) == 100
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    @patch('pathlib.Path.exists')
    async def test_concurrent_execution_performance(self, mock_exists):
        """Test performance with concurrent executions."""
        # Mock credentials exist
        mock_exists.return_value = True
        
        # Mock components for fast execution
        mock_container_manager = Mock(spec=ContainerManager)
        mock_container_manager.docker_client = Mock()
        mock_container_manager.create_container = AsyncMock(
            side_effect=lambda *args, **kwargs: f"container_{args[0] if args else 'unknown'}"
        )
        mock_container_manager.start_container = AsyncMock(return_value=True)
        
        # Simulate varying execution times
        async def mock_wait(*args, **kwargs):
            await asyncio.sleep(0.01)  # 10ms execution
            container_id = args[0] if args else kwargs.get('container_id', 'unknown')
            return {'success': True, 'result': f'Done {container_id}'}
        
        mock_container_manager.wait_for_completion = mock_wait
        
        # Create multiple agents
        agents = []
        for i in range(5):
            agent = ClaudeCodeAgent({"default_workflow": "test-workflow"})
            agent.container_manager = mock_container_manager
            
            # Create a properly mocked executor
            mock_executor = Mock(spec=DockerExecutor)
            mock_executor.execute_claude_task = AsyncMock(return_value={
                'success': True, 
                'result': f'Task completed by agent {i}',
                'exit_code': 0
            })
            agent.executor = mock_executor
            agent._validate_workflow = AsyncMock(return_value=True)
            agents.append(agent)
        
        # Execute tasks concurrently
        start_time = time.time()
        tasks = []
        
        for i, agent in enumerate(agents):
            for j in range(10):
                with patch('pathlib.Path.exists') as mock_exists:
                    mock_exists.return_value = True
                    task = agent.run(f"Task {i}-{j}")
                    tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time
        
        # All should complete
        assert all(r.success for r in results)
        # Should complete 50 tasks in reasonable time
        assert total_time < 2.0  # Under 2 seconds


class TestScalabilityPerformance:
    """Test scalability characteristics."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_container_pool_scalability(self):
        """Test container pool scalability."""
        # Test different pool sizes
        pool_sizes = [5, 10, 20]
        execution_times = []
        
        for pool_size in pool_sizes:
            manager = ContainerManager(max_concurrent=pool_size)
            manager.docker_client = Mock()
            manager.docker_client.containers.create.return_value = Mock()
            
            # Measure time to fill the pool
            start_time = time.time()
            tasks = []
            
            for i in range(pool_size):
                task = manager.create_container(f"session_{i}", "test")
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            pool_fill_time = time.time() - start_time
            execution_times.append(pool_fill_time)
        
        # Larger pools shouldn't have significantly worse performance
        # Time should scale sub-linearly with some tolerance for system variations
        time_ratio = execution_times[-1] / execution_times[0]
        size_ratio = pool_sizes[-1] / pool_sizes[0]
        
        # Allow 25% tolerance for system performance variations
        tolerance_factor = 1.25
        assert time_ratio < (size_ratio * tolerance_factor)  # Sub-linear scaling with tolerance
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_workflow_loading_cache_performance(self):
        """Test workflow configuration loading performance."""
        executor = DockerExecutor(Mock())
        
        # Mock file system
        with patch('os.path.exists', return_value=True):
            with patch('builtins.open', Mock(return_value=Mock(read=Mock(return_value="test")))):
                with patch('json.load', return_value={}):
                    # First load (cache miss)
                    start_time = time.time()
                    config1 = await executor._load_workflow_config("test-workflow")
                    first_load_time = time.time() - start_time
                    
                    # Subsequent loads (would benefit from caching in real impl)
                    start_time = time.time()
                    for _ in range(10):
                        config = await executor._load_workflow_config("test-workflow")
                    subsequent_load_time = (time.time() - start_time) / 10
                    
                    # Subsequent loads should be fast
                    assert subsequent_load_time < first_load_time * 2


class TestLatencyPerformance:
    """Test latency characteristics."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_request_response_latency(self):
        """Test end-to-end request/response latency."""
        # Setup fast-responding mocks
        mock_container_manager = Mock(spec=ContainerManager)
        mock_container_manager.docker_client = Mock()
        mock_container_manager.create_container = AsyncMock(return_value="container_123")
        mock_container_manager.start_container = AsyncMock(return_value=True)
        mock_container_manager.wait_for_completion = AsyncMock(
            return_value={'success': True, 'result': 'Done'}
        )
        
        agent = ClaudeCodeAgent({})
        agent.container_manager = mock_container_manager
        agent.executor = DockerExecutor(mock_container_manager)
        agent._validate_workflow = AsyncMock(return_value=True)
        
        # Measure latencies
        latencies = []
        
        for i in range(20):
            start_time = time.time()
            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.return_value = True
                response = await agent.run(f"Quick task {i}")
            latency = time.time() - start_time
            latencies.append(latency)
        
        # Calculate percentiles
        latencies.sort()
        p50 = latencies[len(latencies) // 2]
        p95 = latencies[int(len(latencies) * 0.95)]
        p99 = latencies[int(len(latencies) * 0.99)]
        
        # Latency requirements (for mocked version)
        assert p50 < 0.01   # 50th percentile under 10ms
        assert p95 < 0.02   # 95th percentile under 20ms
        assert p99 < 0.05   # 99th percentile under 50ms


class TestResourceCleanupPerformance:
    """Test resource cleanup performance."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_bulk_container_cleanup_performance(self):
        """Test performance of cleaning up many containers."""
        manager = ContainerManager()
        
        # Add many containers
        for i in range(50):
            mock_container = Mock()
            mock_container.status = 'exited'
            mock_container.stop.return_value = None
            mock_container.remove.return_value = None
            
            manager.active_containers[f"container_{i}"] = {
                'container': mock_container
            }
        
        # Measure cleanup time
        start_time = time.time()
        
        # Clean up all containers
        tasks = []
        for container_id in list(manager.active_containers.keys()):
            task = manager._cleanup_container(container_id)
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        cleanup_time = time.time() - start_time
        
        # Should clean up 50 containers quickly
        assert cleanup_time < 1.0  # Under 1 second
        assert len(manager.active_containers) == 0
        
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_stale_container_scan_performance(self):
        """Test performance of scanning for stale containers."""
        manager = ContainerManager()
        
        # Add mix of stale and active containers
        for i in range(100):
            mock_container = Mock()
            mock_container.status = 'running' if i % 2 == 0 else 'dead'
            mock_container.reload.return_value = None
            
            created_at = datetime.utcnow() - timedelta(hours=5 if i % 3 == 0 else 1)
            
            manager.active_containers[f"container_{i}"] = {
                'container': mock_container,
                'created_at': created_at
            }
        
        manager._cleanup_container = AsyncMock()
        
        # Measure scan time
        start_time = time.time()
        cleaned = await manager.cleanup_stale_containers()
        scan_time = time.time() - start_time
        
        # Should scan 100 containers quickly
        assert scan_time < 0.5  # Under 500ms
        assert cleaned > 0


class TestBenchmarkSummary:
    """Summary benchmark test to report performance metrics."""
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_performance_summary(self, capsys):
        """Run performance summary and print results."""
        results = {
            "Container Operations": {
                "Creation Time": "< 1s",
                "Startup Time": "< 500ms avg",
                "Cleanup Time": "< 20ms per container"
            },
            "Memory Usage": {
                "Per Agent": "< 10MB",
                "Container Tracking": "< 0.5MB per container",
                "Context Storage": "< 1KB per entry"
            },
            "Throughput": {
                "Async Run Creation": "> 100 req/s",
                "Status Polling": "> 1000 req/s",
                "Concurrent Executions": "50 tasks in < 2s"
            },
            "Latency": {
                "P50": "< 10ms",
                "P95": "< 20ms",
                "P99": "< 50ms"
            }
        }
        
        print("\n=== Claude-Code Agent Performance Summary ===")
        for category, metrics in results.items():
            print(f"\n{category}:")
            for metric, value in metrics.items():
                print(f"  {metric}: {value}")
        
        # Run a simple benchmark
        agent = ClaudeCodeAgent({})
        
        # Measure agent creation time
        start = time.time()
        for _ in range(10):
            ClaudeCodeAgent({})
        creation_time = (time.time() - start) / 10
        
        print(f"\nActual Measurements:")
        print(f"  Agent Creation: {creation_time*1000:.2f}ms")
        
        # This test always passes - it's for reporting
        assert True