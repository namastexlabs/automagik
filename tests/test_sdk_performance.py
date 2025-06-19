"""Performance benchmarks for SDK executor vs CLI executor.

These tests measure and compare the performance characteristics of both executors
to ensure the SDK doesn't introduce significant overhead.
"""

import pytest
import asyncio
import time
import statistics
import tempfile
import json
from pathlib import Path
from typing import List, Dict, Any, Tuple
# Optional plotting dependencies
try:
    import matplotlib.pyplot as plt
    import numpy as np
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False

from src.agents.claude_code.sdk_executor import SDKExecutor
from src.agents.claude_code.cli_executor import CLIExecutor


class PerformanceMetrics:
    """Container for performance metrics."""
    
    def __init__(self, name: str):
        self.name = name
        self.startup_times: List[float] = []
        self.execution_times: List[float] = []
        self.memory_usage: List[float] = []
        self.total_times: List[float] = []
    
    def add_measurement(self, startup_time: float, execution_time: float, memory_mb: float):
        """Add a measurement to the metrics."""
        self.startup_times.append(startup_time)
        self.execution_times.append(execution_time)
        self.memory_usage.append(memory_mb)
        self.total_times.append(startup_time + execution_time)
    
    def get_stats(self) -> Dict[str, Dict[str, float]]:
        """Calculate statistics for all metrics."""
        return {
            "startup": self._calculate_stats(self.startup_times),
            "execution": self._calculate_stats(self.execution_times),
            "total": self._calculate_stats(self.total_times),
            "memory": self._calculate_stats(self.memory_usage)
        }
    
    def _calculate_stats(self, values: List[float]) -> Dict[str, float]:
        """Calculate statistical measures for a list of values."""
        if not values:
            return {"mean": 0, "median": 0, "std": 0, "min": 0, "max": 0}
        
        stats = {
            "mean": statistics.mean(values),
            "median": statistics.median(values),
            "std": statistics.stdev(values) if len(values) > 1 else 0,
            "min": min(values),
            "max": max(values)
        }
        
        if HAS_PLOTTING:
            stats.update({
                "p95": np.percentile(values, 95) if values else 0,
                "p99": np.percentile(values, 99) if values else 0
            })
        else:
            stats.update({
                "p95": sorted(values)[int(len(values) * 0.95)] if values else 0,
                "p99": sorted(values)[int(len(values) * 0.99)] if values else 0
            })
        
        return stats


class TestSDKPerformance:
    """Performance benchmark tests for SDK vs CLI executors."""
    
    @pytest.fixture
    def benchmark_workspace(self):
        """Create a workspace with various test scenarios."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create test files of various sizes
            # Small file (1KB)
            (workspace / "small.py").write_text("# Small file\n" * 50)
            
            # Medium file (10KB)
            (workspace / "medium.py").write_text("""
def process_data(data):
    # Process the data
    result = []
    for item in data:
        if item % 2 == 0:
            result.append(item * 2)
        else:
            result.append(item * 3)
    return result

# Generate some test data
""" * 100)
            
            # Large file (100KB)
            large_content = """
class DataProcessor:
    def __init__(self):
        self.data = []
        
    def add_data(self, item):
        self.data.append(item)
        
    def process(self):
        return [self._transform(item) for item in self.data]
        
    def _transform(self, item):
        # Complex transformation logic
        return item ** 2 + item * 3 + 1
""" * 500
            (workspace / "large.py").write_text(large_content)
            
            # Create multiple files for directory operations
            for i in range(20):
                (workspace / f"file_{i}.txt").write_text(f"Content of file {i}")
            
            # Standard files
            (workspace / "prompt.md").write_text("You are a helpful code assistant.")
            (workspace / "allowed_tools.json").write_text(json.dumps([
                "read_file", "write_file", "list_directory", "run_command"
            ]))
            
            yield workspace
    
    async def measure_executor_performance(
        self, 
        executor_class, 
        working_dir: str,
        query: str,
        iterations: int = 5
    ) -> Tuple[float, float, float]:
        """Measure performance for a single executor run."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        # Measure startup time
        start_time = time.perf_counter()
        executor = executor_class(
            working_dir=working_dir,
            model="claude-3-haiku-20240307",
            max_turns=5,
            timeout=30
        )
        await executor.initialize()
        startup_time = time.perf_counter() - start_time
        
        # Measure execution time
        start_time = time.perf_counter()
        result = await executor.execute([{"role": "user", "content": query}])
        execution_time = time.perf_counter() - start_time
        
        # Measure memory usage
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # Cleanup
        await executor.cleanup()
        
        return startup_time, execution_time, memory_mb
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_startup_performance(self, benchmark_workspace):
        """Compare startup times between SDK and CLI executors."""
        sdk_metrics = PerformanceMetrics("SDK")
        cli_metrics = PerformanceMetrics("CLI")
        
        iterations = 10
        
        for i in range(iterations):
            # Measure SDK
            startup, execution, memory = await self.measure_executor_performance(
                SDKExecutor,
                str(benchmark_workspace),
                "Say hello",
                1
            )
            sdk_metrics.add_measurement(startup, execution, memory)
            
            # Measure CLI
            startup, execution, memory = await self.measure_executor_performance(
                CLIExecutor,
                str(benchmark_workspace),
                "Say hello",
                1
            )
            cli_metrics.add_measurement(startup, execution, memory)
            
            # Small delay between iterations
            await asyncio.sleep(0.1)
        
        # Calculate statistics
        sdk_stats = sdk_metrics.get_stats()
        cli_stats = cli_metrics.get_stats()
        
        # SDK startup should not be more than 50% slower than CLI
        sdk_mean_startup = sdk_stats["startup"]["mean"]
        cli_mean_startup = cli_stats["startup"]["mean"]
        
        startup_ratio = sdk_mean_startup / cli_mean_startup if cli_mean_startup > 0 else 1
        
        print(f"\nStartup Performance:")
        print(f"SDK: {sdk_mean_startup:.3f}s (±{sdk_stats['startup']['std']:.3f}s)")
        print(f"CLI: {cli_mean_startup:.3f}s (±{cli_stats['startup']['std']:.3f}s)")
        print(f"Ratio: {startup_ratio:.2f}x")
        
        assert startup_ratio < 1.5, f"SDK startup is {startup_ratio:.2f}x slower than CLI (max allowed: 1.5x)"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_execution_performance_simple(self, benchmark_workspace):
        """Test execution performance for simple queries."""
        queries = [
            "List all files in the directory",
            "Read the content of small.py",
            "Count the number of lines in medium.py",
            "What does the large.py file contain?"
        ]
        
        sdk_metrics = PerformanceMetrics("SDK")
        cli_metrics = PerformanceMetrics("CLI")
        
        for query in queries:
            for i in range(3):  # 3 iterations per query
                # Measure SDK
                startup, execution, memory = await self.measure_executor_performance(
                    SDKExecutor,
                    str(benchmark_workspace),
                    query,
                    1
                )
                sdk_metrics.add_measurement(startup, execution, memory)
                
                # Measure CLI
                startup, execution, memory = await self.measure_executor_performance(
                    CLIExecutor,
                    str(benchmark_workspace),
                    query,
                    1
                )
                cli_metrics.add_measurement(startup, execution, memory)
        
        # Calculate statistics
        sdk_stats = sdk_metrics.get_stats()
        cli_stats = cli_metrics.get_stats()
        
        # Check execution time ratio
        sdk_mean_exec = sdk_stats["execution"]["mean"]
        cli_mean_exec = cli_stats["execution"]["mean"]
        exec_ratio = sdk_mean_exec / cli_mean_exec if cli_mean_exec > 0 else 1
        
        print(f"\nSimple Query Execution Performance:")
        print(f"SDK: {sdk_mean_exec:.3f}s (±{sdk_stats['execution']['std']:.3f}s)")
        print(f"CLI: {cli_mean_exec:.3f}s (±{cli_stats['execution']['std']:.3f}s)")
        print(f"Ratio: {exec_ratio:.2f}x")
        
        assert exec_ratio < 1.5, f"SDK execution is {exec_ratio:.2f}x slower than CLI (max allowed: 1.5x)"
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_execution_performance_complex(self, benchmark_workspace):
        """Test execution performance for complex multi-step queries."""
        complex_query = """
        Please perform the following tasks:
        1. List all Python files in the directory
        2. Read the large.py file and count the number of classes
        3. Create a summary file called 'analysis.md' with your findings
        4. List the directory again to confirm the file was created
        """
        
        sdk_metrics = PerformanceMetrics("SDK")
        cli_metrics = PerformanceMetrics("CLI")
        
        iterations = 5
        
        for i in range(iterations):
            # Clean up any previous analysis.md
            analysis_file = benchmark_workspace / "analysis.md"
            if analysis_file.exists():
                analysis_file.unlink()
            
            # Measure SDK
            startup, execution, memory = await self.measure_executor_performance(
                SDKExecutor,
                str(benchmark_workspace),
                complex_query,
                1
            )
            sdk_metrics.add_measurement(startup, execution, memory)
            
            # Clean up
            if analysis_file.exists():
                analysis_file.unlink()
            
            # Measure CLI
            startup, execution, memory = await self.measure_executor_performance(
                CLIExecutor,
                str(benchmark_workspace),
                complex_query,
                1
            )
            cli_metrics.add_measurement(startup, execution, memory)
        
        # Calculate statistics
        sdk_stats = sdk_metrics.get_stats()
        cli_stats = cli_metrics.get_stats()
        
        # Check total time ratio
        sdk_mean_total = sdk_stats["total"]["mean"]
        cli_mean_total = cli_stats["total"]["mean"]
        total_ratio = sdk_mean_total / cli_mean_total if cli_mean_total > 0 else 1
        
        print(f"\nComplex Query Total Performance:")
        print(f"SDK: {sdk_mean_total:.3f}s (±{sdk_stats['total']['std']:.3f}s)")
        print(f"CLI: {cli_mean_total:.3f}s (±{cli_stats['total']['std']:.3f}s)")
        print(f"Ratio: {total_ratio:.2f}x")
        
        assert total_ratio < 1.5, f"SDK total time is {total_ratio:.2f}x slower than CLI (max allowed: 1.5x)"
    
    @pytest.mark.asyncio
    async def test_memory_usage(self, benchmark_workspace):
        """Compare memory usage between SDK and CLI executors."""
        sdk_metrics = PerformanceMetrics("SDK")
        cli_metrics = PerformanceMetrics("CLI")
        
        # Test with multiple file operations
        memory_query = """
        Read all Python files in the directory and provide a summary of each.
        """
        
        iterations = 5
        
        for i in range(iterations):
            # Measure SDK
            startup, execution, memory = await self.measure_executor_performance(
                SDKExecutor,
                str(benchmark_workspace),
                memory_query,
                1
            )
            sdk_metrics.add_measurement(startup, execution, memory)
            
            # Measure CLI
            startup, execution, memory = await self.measure_executor_performance(
                CLIExecutor,
                str(benchmark_workspace),
                memory_query,
                1
            )
            cli_metrics.add_measurement(startup, execution, memory)
        
        # Calculate statistics
        sdk_stats = sdk_metrics.get_stats()
        cli_stats = cli_metrics.get_stats()
        
        # Check memory usage
        sdk_mean_memory = sdk_stats["memory"]["mean"]
        cli_mean_memory = cli_stats["memory"]["mean"]
        memory_ratio = sdk_mean_memory / cli_mean_memory if cli_mean_memory > 0 else 1
        
        print(f"\nMemory Usage:")
        print(f"SDK: {sdk_mean_memory:.1f} MB (±{sdk_stats['memory']['std']:.1f} MB)")
        print(f"CLI: {cli_mean_memory:.1f} MB (±{cli_stats['memory']['std']:.1f} MB)")
        print(f"Ratio: {memory_ratio:.2f}x")
        
        # SDK shouldn't use significantly more memory
        assert memory_ratio < 2.0, f"SDK uses {memory_ratio:.2f}x more memory than CLI (max allowed: 2.0x)"
    
    @pytest.mark.asyncio
    async def test_concurrent_execution(self, benchmark_workspace):
        """Test performance under concurrent load."""
        async def run_query(executor_class, working_dir: str, query_id: int):
            """Run a single query and return timing."""
            start = time.perf_counter()
            executor = executor_class(
                working_dir=working_dir,
                model="claude-3-haiku-20240307",
                max_turns=5,
                timeout=30
            )
            await executor.initialize()
            
            query = f"Read file_{query_id}.txt and tell me what it contains"
            result = await executor.execute([{"role": "user", "content": query}])
            
            await executor.cleanup()
            return time.perf_counter() - start
        
        # Test with 5 concurrent requests
        concurrent_count = 5
        
        # SDK concurrent execution
        sdk_start = time.perf_counter()
        sdk_tasks = [
            run_query(SDKExecutor, str(benchmark_workspace), i) 
            for i in range(concurrent_count)
        ]
        sdk_times = await asyncio.gather(*sdk_tasks)
        sdk_total = time.perf_counter() - sdk_start
        
        # CLI concurrent execution
        cli_start = time.perf_counter()
        cli_tasks = [
            run_query(CLIExecutor, str(benchmark_workspace), i) 
            for i in range(concurrent_count)
        ]
        cli_times = await asyncio.gather(*cli_tasks)
        cli_total = time.perf_counter() - cli_start
        
        print(f"\nConcurrent Execution ({concurrent_count} requests):")
        print(f"SDK Total: {sdk_total:.3f}s, Avg: {statistics.mean(sdk_times):.3f}s")
        print(f"CLI Total: {cli_total:.3f}s, Avg: {statistics.mean(cli_times):.3f}s")
        print(f"Ratio: {sdk_total/cli_total:.2f}x")
        
        # SDK should handle concurrent load reasonably well
        assert sdk_total / cli_total < 2.0, f"SDK concurrent performance is {sdk_total/cli_total:.2f}x slower than CLI"
    
    def generate_performance_report(
        self, 
        sdk_metrics: PerformanceMetrics,
        cli_metrics: PerformanceMetrics,
        output_file: str = "performance_report.html"
    ):
        """Generate an HTML performance report with charts."""
        sdk_stats = sdk_metrics.get_stats()
        cli_stats = cli_metrics.get_stats()
        
        html_content = f"""
        <html>
        <head>
            <title>SDK vs CLI Performance Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .metric {{ margin: 20px 0; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .pass {{ color: green; }}
                .fail {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>SDK vs CLI Performance Comparison</h1>
            
            <h2>Summary</h2>
            <table>
                <tr>
                    <th>Metric</th>
                    <th>SDK (mean ± std)</th>
                    <th>CLI (mean ± std)</th>
                    <th>Ratio</th>
                    <th>Status</th>
                </tr>
                <tr>
                    <td>Startup Time</td>
                    <td>{sdk_stats['startup']['mean']:.3f}s ± {sdk_stats['startup']['std']:.3f}s</td>
                    <td>{cli_stats['startup']['mean']:.3f}s ± {cli_stats['startup']['std']:.3f}s</td>
                    <td>{sdk_stats['startup']['mean']/cli_stats['startup']['mean']:.2f}x</td>
                    <td class="{'pass' if sdk_stats['startup']['mean']/cli_stats['startup']['mean'] < 1.5 else 'fail'}">
                        {'PASS' if sdk_stats['startup']['mean']/cli_stats['startup']['mean'] < 1.5 else 'FAIL'}
                    </td>
                </tr>
                <tr>
                    <td>Execution Time</td>
                    <td>{sdk_stats['execution']['mean']:.3f}s ± {sdk_stats['execution']['std']:.3f}s</td>
                    <td>{cli_stats['execution']['mean']:.3f}s ± {cli_stats['execution']['std']:.3f}s</td>
                    <td>{sdk_stats['execution']['mean']/cli_stats['execution']['mean']:.2f}x</td>
                    <td class="{'pass' if sdk_stats['execution']['mean']/cli_stats['execution']['mean'] < 1.5 else 'fail'}">
                        {'PASS' if sdk_stats['execution']['mean']/cli_stats['execution']['mean'] < 1.5 else 'FAIL'}
                    </td>
                </tr>
                <tr>
                    <td>Memory Usage</td>
                    <td>{sdk_stats['memory']['mean']:.1f} MB ± {sdk_stats['memory']['std']:.1f} MB</td>
                    <td>{cli_stats['memory']['mean']:.1f} MB ± {cli_stats['memory']['std']:.1f} MB</td>
                    <td>{sdk_stats['memory']['mean']/cli_stats['memory']['mean']:.2f}x</td>
                    <td class="{'pass' if sdk_stats['memory']['mean']/cli_stats['memory']['mean'] < 2.0 else 'fail'}">
                        {'PASS' if sdk_stats['memory']['mean']/cli_stats['memory']['mean'] < 2.0 else 'FAIL'}
                    </td>
                </tr>
            </table>
            
            <h2>Performance Criteria</h2>
            <ul>
                <li>✓ SDK startup time must be < 1.5x slower than CLI</li>
                <li>✓ SDK execution time must be < 1.5x slower than CLI</li>
                <li>✓ SDK memory usage must be < 2.0x higher than CLI</li>
            </ul>
        </body>
        </html>
        """
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"\nPerformance report generated: {output_file}")