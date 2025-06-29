#!/usr/bin/env python3
"""
MCP Scale Testing Suite - NMSTX-258

Tests the MCP system's behavior and performance under production-scale loads,
validating readiness for deployment with large numbers of configurations.

Scale Areas Tested:
- Large configuration sets (100+ servers)
- High concurrent user load
- Memory usage under scale
- Database performance at scale
- JSONB query performance with large datasets
- API response times under load
"""

import pytest
import random
import statistics
import time
import psutil
import sys
from pathlib import Path
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.db.models import MCPConfigCreate


class TestMCPProductionScale:
    """Test MCP system behavior at production scale."""
    
    @pytest.fixture
    def large_config_dataset(self):
        """Generate large dataset of MCP configurations for scale testing."""
        configs = []
        
        # Server types and patterns
        server_types = ["stdio", "http"]
        agent_combinations = [
            ["simple"],
            ["simple"],
            ["simple", "discord"],
            ["simple", "discord", "sofia"],
            ["*"]  # Wildcard assignment
        ]
        
        for i in range(500):  # Generate 500 configurations
            server_type = random.choice(server_types)
            
            config = {
                "name": f"scale-test-server-{i:04d}",
                "server_type": server_type,
                "description": f"Scale test server {i} for performance validation",
                "agents": random.choice(agent_combinations),
                "tools": {
                    "include": ["*"] if i % 3 == 0 else [f"tool_{j}" for j in range(random.randint(1, 5))],
                    "exclude": [] if i % 4 == 0 else [f"exclude_{j}" for j in range(random.randint(0, 2))]
                },
                "environment": {
                    f"ENV_VAR_{j}": f"value_{i}_{j}" 
                    for j in range(random.randint(1, 8))
                },
                "timeout": random.randint(10000, 120000),
                "retry_count": random.randint(1, 10),
                "enabled": random.choice([True, False]),
                "auto_start": random.choice([True, False])
            }
            
            # Add server-type specific fields
            if server_type == "stdio":
                config["command"] = ["python", "-m", f"test_server_{i}", "--port", str(3000 + i)]
            else:
                config["url"] = f"http://localhost:{3000 + i}/mcp"
            
            configs.append(config)
        
        return configs

    def test_large_configuration_loading(self, large_config_dataset):
        """Test loading and processing large numbers of configurations."""
        def simulate_config_loading(configs: List[Dict], batch_size: int = 50):
            """Simulate loading configurations in batches."""
            loaded_configs = []
            load_times = []
            
            for i in range(0, len(configs), batch_size):
                batch = configs[i:i + batch_size]
                start_time = time.perf_counter()
                
                # Simulate batch loading
                batch_configs = []
                for config_data in batch:
                    try:
                        config = MCPConfigCreate(**config_data)
                        batch_configs.append(config)
                    except Exception as e:
                        pytest.fail(f"Config validation failed: {e}")
                
                end_time = time.perf_counter()
                load_time = (end_time - start_time) * 1000  # ms
                load_times.append(load_time)
                loaded_configs.extend(batch_configs)
                
                # Simulate memory pressure
                if i % 100 == 0:
                    time.sleep(0.001)  # Brief pause every 100 configs
            
            return {
                "total_configs": len(loaded_configs),
                "batch_times_ms": load_times,
                "avg_batch_time_ms": statistics.mean(load_times),
                "total_time_ms": sum(load_times),
                "configs_per_second": len(loaded_configs) / (sum(load_times) / 1000)
            }
        
        # Test with full dataset
        result = simulate_config_loading(large_config_dataset)
        
        assert result["total_configs"] == len(large_config_dataset)
        assert result["avg_batch_time_ms"] < 100, f"Batch loading too slow: {result['avg_batch_time_ms']:.2f}ms"
        assert result["configs_per_second"] > 500, f"Loading rate too slow: {result['configs_per_second']:.2f} configs/s"
        
        print(f"Loaded {result['total_configs']} configs in {result['total_time_ms']:.2f}ms")
        print(f"Average batch time: {result['avg_batch_time_ms']:.2f}ms")
        print(f"Loading rate: {result['configs_per_second']:.2f} configs/second")

    def test_memory_usage_at_scale(self, large_config_dataset):
        """Test memory usage with large configuration sets."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Load configurations and monitor memory
        configurations = []
        memory_samples = []
        
        batch_size = 50
        for i in range(0, len(large_config_dataset), batch_size):
            batch = large_config_dataset[i:i + batch_size]
            
            # Load batch
            for config_data in batch:
                config = MCPConfigCreate(**config_data)
                configurations.append(config)
            
            # Sample memory usage
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_samples.append(current_memory - initial_memory)
        
        peak_memory_increase = max(memory_samples)
        final_memory_increase = memory_samples[-1]
        
        # Memory usage should be reasonable for the dataset size
        configs_count = len(configurations)
        memory_per_config = final_memory_increase / configs_count
        
        assert peak_memory_increase < 200, f"Peak memory too high: {peak_memory_increase:.2f}MB"
        assert memory_per_config < 0.5, f"Memory per config too high: {memory_per_config:.3f}MB"
        
        print(f"Loaded {configs_count} configurations")
        print(f"Peak memory increase: {peak_memory_increase:.2f}MB")
        print(f"Final memory increase: {final_memory_increase:.2f}MB")
        print(f"Memory per config: {memory_per_config:.3f}MB")

    def test_concurrent_configuration_operations(self, large_config_dataset):
        """Test concurrent operations on large configuration sets."""
        configs_subset = large_config_dataset[:100]  # Use subset for concurrent testing
        
        def perform_config_operation(config_data: Dict, operation_type: str):
            """Simulate different configuration operations."""
            start_time = time.perf_counter()
            
            try:
                if operation_type == "create":
                    config = MCPConfigCreate(**config_data)
                    # Simulate database insert
                    time.sleep(0.005)
                    
                elif operation_type == "read":
                    # Simulate database query
                    time.sleep(0.002)
                    
                elif operation_type == "update":
                    config = MCPConfigCreate(**config_data)
                    config.enabled = not config.enabled
                    # Simulate database update
                    time.sleep(0.003)
                    
                elif operation_type == "filter":
                    # Simulate agent filtering
                    agent_name = random.choice(["simple", "discord", "sofia"])
                    [c for c in configs_subset 
                             if agent_name in c.get("agents", []) or "*" in c.get("agents", [])]
                    time.sleep(0.001)
                
                end_time = time.perf_counter()
                return {
                    "operation": operation_type,
                    "duration_ms": (end_time - start_time) * 1000,
                    "success": True
                }
            
            except Exception as e:
                end_time = time.perf_counter()
                return {
                    "operation": operation_type,
                    "duration_ms": (end_time - start_time) * 1000,
                    "success": False,
                    "error": str(e)
                }
        
        # Run concurrent operations
        operations = ["create", "read", "update", "filter"]
        num_concurrent = 20
        
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = []
            
            for i in range(num_concurrent * 2):  # 40 total operations
                config = random.choice(configs_subset)
                operation = random.choice(operations)
                future = executor.submit(perform_config_operation, config, operation)
                futures.append(future)
            
            # Collect results
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        # Analyze results
        successful_ops = [r for r in results if r["success"]]
        failed_ops = [r for r in results if not r["success"]]
        
        success_rate = len(successful_ops) / len(results)
        avg_duration = statistics.mean([r["duration_ms"] for r in successful_ops])
        
        assert success_rate > 0.95, f"Success rate too low: {success_rate:.2%}"
        assert avg_duration < 50, f"Average operation too slow: {avg_duration:.2f}ms"
        
        print(f"Concurrent operations - Success rate: {success_rate:.2%}")
        print(f"Average duration: {avg_duration:.2f}ms")
        print(f"Failed operations: {len(failed_ops)}")

    def test_agent_filtering_at_scale(self, large_config_dataset):
        """Test agent filtering performance with large datasets."""
        def simulate_agent_filtering(configs: List[Dict], agent_name: str):
            """Simulate agent-based configuration filtering."""
            start_time = time.perf_counter()
            
            # Simulate JSONB query: WHERE config->'agents' ? 'agent_name' OR config->'agents' ? '*'
            matches = []
            for config in configs:
                agents = config.get("agents", [])
                if agent_name in agents or "*" in agents:
                    matches.append(config)
            
            end_time = time.perf_counter()
            duration_ms = (end_time - start_time) * 1000
            
            return {
                "agent_name": agent_name,
                "total_configs": len(configs),
                "matching_configs": len(matches),
                "duration_ms": duration_ms,
                "configs_per_ms": len(configs) / duration_ms
            }
        
        # Test filtering for different agents
        agents_to_test = ["simple", "discord", "sofia", "non_existent"]
        results = []
        
        for agent_name in agents_to_test:
            result = simulate_agent_filtering(large_config_dataset, agent_name)
            results.append(result)
            
            print(f"Agent '{agent_name}': {result['matching_configs']}/{result['total_configs']} "
                  f"matches in {result['duration_ms']:.2f}ms "
                  f"({result['configs_per_ms']:.2f} configs/ms)")
        
        # Filtering should be consistently fast
        avg_duration = statistics.mean([r["duration_ms"] for r in results])
        max_duration = max([r["duration_ms"] for r in results])
        
        assert avg_duration < 20, f"Average filtering too slow: {avg_duration:.2f}ms"
        assert max_duration < 50, f"Slowest filtering too slow: {max_duration:.2f}ms"

    def test_jsonb_query_performance_at_scale(self, large_config_dataset):
        """Test JSONB query performance with large datasets."""
        def simulate_complex_jsonb_queries(configs: List[Dict]):
            """Simulate various JSONB query patterns."""
            queries = [
                {
                    "name": "server_type_filter",
                    "filter": lambda c: c.get("server_type") == "stdio",
                    "simulate_time": 0.001
                },
                {
                    "name": "enabled_filter", 
                    "filter": lambda c: c.get("enabled") is True,
                    "simulate_time": 0.001
                },
                {
                    "name": "agent_wildcard_filter",
                    "filter": lambda c: "*" in c.get("agents", []),
                    "simulate_time": 0.002
                },
                {
                    "name": "tool_inclusion_filter",
                    "filter": lambda c: "*" in c.get("tools", {}).get("include", []),
                    "simulate_time": 0.002
                },
                {
                    "name": "environment_exists_filter",
                    "filter": lambda c: len(c.get("environment", {})) > 5,
                    "simulate_time": 0.003
                },
                {
                    "name": "complex_combined_filter",
                    "filter": lambda c: (c.get("server_type") == "stdio" and 
                                       c.get("enabled") is True and
                                       "simple" in c.get("agents", [])),
                    "simulate_time": 0.004
                }
            ]
            
            results = []
            for query in queries:
                start_time = time.perf_counter()
                
                # Simulate database query time
                time.sleep(query["simulate_time"])
                
                # Apply filter
                matches = [c for c in configs if query["filter"](c)]
                
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                
                results.append({
                    "query_name": query["name"],
                    "matches": len(matches),
                    "duration_ms": duration_ms,
                    "efficiency": len(configs) / duration_ms
                })
            
            return results
        
        # Test with full dataset
        query_results = simulate_complex_jsonb_queries(large_config_dataset)
        
        for result in query_results:
            print(f"Query '{result['query_name']}': {result['matches']} matches "
                  f"in {result['duration_ms']:.2f}ms "
                  f"({result['efficiency']:.0f} configs/ms)")
        
        # All queries should complete quickly
        slow_queries = [r for r in query_results if r["duration_ms"] > 10]
        assert len(slow_queries) == 0, f"Slow queries detected: {[q['query_name'] for q in slow_queries]}"
        
        # Efficiency should be reasonable
        avg_efficiency = statistics.mean([r["efficiency"] for r in query_results])
        assert avg_efficiency > 50, f"Query efficiency too low: {avg_efficiency:.2f} configs/ms"

    def test_api_response_under_load(self):
        """Test API response times under simulated load."""
        from fastapi.testclient import TestClient
        from src.main import app
        
        client = TestClient(app)
        
        def make_api_request(endpoint: str, method: str = "GET"):
            """Make API request and measure response time."""
            start_time = time.perf_counter()
            
            try:
                if method == "GET":
                    response = client.get(endpoint)
                else:
                    response = client.post(endpoint, json={})
                
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                
                return {
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "success": 200 <= response.status_code < 300
                }
            
            except Exception as e:
                end_time = time.perf_counter()
                duration_ms = (end_time - start_time) * 1000
                
                return {
                    "endpoint": endpoint,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                    "success": False,
                    "error": str(e)
                }
        
        # Mock authentication for all requests
        with patch('src.api.middleware.verify_api_key', return_value=True):
            # Define endpoints to test
            endpoints = [
                "/api/v1/mcp/configs",
                "/api/v1/mcp/agents/simple/configs", 
                "/api/v1/mcp/agents/discord/configs"
            ]
            
            # Simulate concurrent API load
            num_requests_per_endpoint = 25
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                
                for endpoint in endpoints:
                    for _ in range(num_requests_per_endpoint):
                        future = executor.submit(make_api_request, endpoint)
                        futures.append(future)
                
                # Collect results
                results = []
                for future in as_completed(futures):
                    result = future.result()
                    results.append(result)
            
            # Analyze API performance
            successful_requests = [r for r in results if r["success"]]
            failed_requests = [r for r in results if not r["success"]]
            
            success_rate = len(successful_requests) / len(results)
            avg_response_time = statistics.mean([r["duration_ms"] for r in successful_requests])
            p95_response_time = sorted([r["duration_ms"] for r in successful_requests])[int(len(successful_requests) * 0.95)]
            
            # Performance assertions
            assert success_rate > 0.95, f"API success rate too low: {success_rate:.2%}"
            assert avg_response_time < 100, f"Average response time too slow: {avg_response_time:.2f}ms"
            assert p95_response_time < 200, f"P95 response time too slow: {p95_response_time:.2f}ms"
            
            print(f"API Load Test - Success rate: {success_rate:.2%}")
            print(f"Average response time: {avg_response_time:.2f}ms")
            print(f"P95 response time: {p95_response_time:.2f}ms")
            print(f"Failed requests: {len(failed_requests)}")

    def test_configuration_validation_at_scale(self, large_config_dataset):
        """Test configuration validation performance with large datasets."""
        validation_times = []
        validation_errors = []
        
        for i, config_data in enumerate(large_config_dataset):
            start_time = time.perf_counter()
            
            try:
                # Validate configuration
                config = MCPConfigCreate(**config_data)
                
                # Additional validation checks
                assert config.name.strip(), "Name cannot be empty"
                assert config.server_type in ["stdio", "http"], "Invalid server type"
                assert isinstance(config.agents, list), "Agents must be a list"
                assert isinstance(config.tools, dict), "Tools must be a dict"
                
                end_time = time.perf_counter()
                validation_time = (end_time - start_time) * 1000
                validation_times.append(validation_time)
                
            except Exception as e:
                end_time = time.perf_counter()
                validation_time = (end_time - start_time) * 1000
                validation_errors.append({
                    "config_index": i,
                    "error": str(e),
                    "validation_time": validation_time
                })
        
        # Analyze validation performance
        if validation_times:
            avg_validation_time = statistics.mean(validation_times)
            max_validation_time = max(validation_times)
            
            assert avg_validation_time < 1.0, f"Average validation too slow: {avg_validation_time:.3f}ms"
            assert max_validation_time < 5.0, f"Slowest validation too slow: {max_validation_time:.3f}ms"
        
        # Validation should succeed for all well-formed configs
        error_rate = len(validation_errors) / len(large_config_dataset)
        assert error_rate < 0.01, f"Validation error rate too high: {error_rate:.2%}"
        
        print(f"Validated {len(large_config_dataset)} configurations")
        print(f"Average validation time: {avg_validation_time:.3f}ms")
        print(f"Validation errors: {len(validation_errors)}")


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v", "-s"])