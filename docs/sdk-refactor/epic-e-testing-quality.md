# Epic E - Testing & Quality Gates

## Owner: @guardian-workflow
## Branch: feature/sdk-migration (after Epic B-D)
## Priority: FIFTH - Run after core implementation

## Objective
Comprehensive testing suite to ensure SDK executor maintains full parity with CLI executor, including performance benchmarks.

## Detailed Implementation Steps

### E1. Unit Tests for SDK Executor

Create `/tests/test_sdk_executor.py`:

```python
import pytest
import asyncio
import json
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from src.agents.claude_code.sdk_executor import ClaudeSDKExecutor
from src.agents.claude_code.cli_executor import CLIResult

class TestClaudeSDKExecutor:
    """Comprehensive unit tests for SDK executor."""
    
    @pytest.fixture
    def mock_env_manager(self):
        """Mock environment manager."""
        mgr = Mock()
        mgr.as_dict.return_value = {
            'CLAUDE_WORKSPACE': '/test/workspace',
            'CLAUDE_SESSION_ID': 'test-123'
        }
        return mgr
    
    @pytest.fixture
    def executor(self, mock_env_manager):
        """Create executor instance."""
        return ClaudeSDKExecutor(mock_env_manager)
    
    @pytest.mark.asyncio
    async def test_basic_execution(self, executor, tmp_path):
        """Test basic prompt execution."""
        with patch('claude_code.query') as mock_query:
            # Mock SDK response
            mock_query.return_value = self._async_generator([
                {'role': 'assistant', 'content': 'Hello!'},
                {'role': 'assistant', 'content': '2+2 equals 4'}
            ])
            
            result = await executor.execute(
                "What is 2+2?",
                workspace=tmp_path
            )
            
            assert result.success
            assert len(result.messages) == 2
            assert result.exit_code == 0
    
    @pytest.mark.asyncio
    async def test_execute_until_first_response(self, executor, tmp_path):
        """Test early return functionality."""
        messages = [
            {'role': 'system', 'content': 'Thinking...'},
            {'role': 'assistant', 'content': 'First response'},
            {'role': 'assistant', 'content': 'Second response'},
        ]
        
        with patch('claude_code.query') as mock_query:
            mock_query.return_value = self._async_generator(messages)
            
            consumed, task = await executor.execute_until_first_response(
                "Test prompt",
                workspace=tmp_path
            )
            
            # Should stop after first assistant content
            assert len(consumed) == 2
            assert consumed[-1]['content'] == 'First response'
            
            # Continuation should get remaining
            remaining = await task
            assert len(remaining) == 3  # All messages
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, executor, tmp_path):
        """Test execution timeout."""
        async def slow_generator():
            await asyncio.sleep(2)
            yield {'role': 'assistant', 'content': 'Too late'}
        
        with patch('claude_code.query') as mock_query:
            mock_query.return_value = slow_generator()
            
            result = await executor.execute(
                "Slow query",
                workspace=tmp_path,
                timeout=0.5
            )
            
            assert not result.success
            assert result.error == "Execution timed out"
            assert result.execution_time < 1.0
    
    @pytest.mark.asyncio
    async def test_system_prompt_loading(self, executor, tmp_path):
        """Test prompt.md loads as system_prompt."""
        prompt_content = "You are a test assistant."
        (tmp_path / "prompt.md").write_text(prompt_content)
        
        with patch('claude_code.ClaudeCodeOptions') as MockOptions:
            options_instance = MockOptions.return_value
            executor._build_options(tmp_path)
            
            # Verify system_prompt was set, not append_system_prompt
            assert options_instance.system_prompt == prompt_content
    
    @staticmethod
    async def _async_generator(items):
        """Helper to create async generator."""
        for item in items:
            yield item
```

### E2. Contract Tests with Real CLI

Create `/tests/test_sdk_contract.py`:

```python
@pytest.mark.e2e
class TestSDKContract:
    """End-to-end tests comparing SDK with real CLI."""
    
    @pytest.fixture
    def test_workspace(self, tmp_path):
        """Create test workspace with files."""
        workspace = tmp_path / "test_project"
        workspace.mkdir()
        
        # Create test files
        (workspace / "main.py").write_text("""
def hello():
    return "Hello, World!"

if __name__ == "__main__":
    print(hello())
        """)
        
        (workspace / "prompt.md").write_text(
            "You are a Python code reviewer. Be concise."
        )
        
        (workspace / "allowed_tools.json").write_text(
            json.dumps(["Read", "Edit", "Write"])
        )
        
        return workspace
    
    @pytest.mark.asyncio
    async def test_code_review_task(self, test_workspace):
        """Test realistic code review task."""
        env_mgr = CLIEnvironmentManager()
        executor = ClaudeSDKExecutor(env_mgr)
        
        result = await executor.execute(
            "Review the main.py file and suggest improvements",
            workspace=test_workspace,
            max_tokens=1000
        )
        
        assert result.success
        assert any('main.py' in str(msg) for msg in result.messages)
        assert result.execution_time < 30.0  # Reasonable timeout
```

### E3. Performance Benchmarks

Create `/tests/test_sdk_performance.py`:

```python
import time
import statistics
from dataclasses import dataclass

@dataclass
class BenchmarkResult:
    name: str
    min_time: float
    max_time: float
    avg_time: float
    std_dev: float
    iterations: int

class TestPerformance:
    """Performance comparison between CLI and SDK executors."""
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_startup_overhead(self, benchmark_workspace):
        """Measure executor initialization overhead."""
        iterations = 10
        sdk_times = []
        cli_times = []
        
        for _ in range(iterations):
            # SDK executor
            start = time.perf_counter()
            sdk_executor = ClaudeSDKExecutor(Mock())
            sdk_times.append(time.perf_counter() - start)
            
            # CLI executor (if still available)
            start = time.perf_counter()
            cli_executor = ClaudeCLIExecutor(Mock())
            cli_times.append(time.perf_counter() - start)
        
        sdk_result = self._calculate_stats("SDK Init", sdk_times)
        cli_result = self._calculate_stats("CLI Init", cli_times)
        
        self._report_benchmark([sdk_result, cli_result])
        
        # SDK should not be significantly slower
        assert sdk_result.avg_time < cli_result.avg_time * 1.5
    
    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_execution_performance(self, benchmark_workspace):
        """Compare execution performance."""
        prompts = [
            "What is 2+2?",
            "List the files in the current directory",
            "Read the main.py file and explain what it does"
        ]
        
        sdk_executor = ClaudeSDKExecutor(Mock())
        
        results = []
        for prompt in prompts:
            times = []
            for _ in range(5):
                start = time.perf_counter()
                result = await sdk_executor.execute(
                    prompt,
                    workspace=benchmark_workspace
                )
                times.append(time.perf_counter() - start)
            
            results.append(self._calculate_stats(f"SDK: {prompt[:20]}...", times))
        
        self._report_benchmark(results)
    
    def _calculate_stats(self, name: str, times: list[float]) -> BenchmarkResult:
        """Calculate benchmark statistics."""
        return BenchmarkResult(
            name=name,
            min_time=min(times),
            max_time=max(times),
            avg_time=statistics.mean(times),
            std_dev=statistics.stdev(times) if len(times) > 1 else 0,
            iterations=len(times)
        )
    
    def _report_benchmark(self, results: list[BenchmarkResult]):
        """Generate benchmark report."""
        print("\n=== Performance Benchmark Results ===")
        for r in results:
            print(f"\n{r.name}:")
            print(f"  Iterations: {r.iterations}")
            print(f"  Min: {r.min_time:.3f}s")
            print(f"  Max: {r.max_time:.3f}s")
            print(f"  Avg: {r.avg_time:.3f}s")
            print(f"  Std: {r.std_dev:.3f}s")
```

### E4. CI Integration

Update `.github/workflows/tests.yml`:

```yaml
# Add SDK-specific test job
  test-sdk:
    name: SDK Executor Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -e .[dev]
          pip install claude-code-sdk>=0.0.10
      
      - name: Run SDK unit tests
        run: |
          pytest tests/test_sdk_executor.py -v
          pytest tests/test_file_loading.py -v
      
      - name: Run contract tests (if CLI available)
        run: |
          pytest tests/test_sdk_contract.py -v -m e2e || echo "Skipping e2e tests"
      
      - name: Run performance benchmarks
        run: |
          pytest tests/test_sdk_performance.py -v -m benchmark --benchmark-only
```

### E5. Regression Test Suite

Create `/tests/test_sdk_regression.py`:

```python
class TestSDKRegression:
    """Ensure SDK maintains all CLI functionality."""
    
    @pytest.mark.asyncio
    async def test_session_resume(self, tmp_path):
        """Test session continuation works."""
        executor = ClaudeSDKExecutor(Mock())
        
        # First execution
        result1 = await executor.execute(
            "Create a test.txt file with 'Hello'",
            workspace=tmp_path
        )
        session_id = result1.session_id
        
        # Resume session
        result2 = await executor.execute(
            "What's in test.txt?",
            workspace=tmp_path,
            resume_session_id=session_id
        )
        
        assert result2.success
        assert 'Hello' in str(result2.messages)
    
    @pytest.mark.asyncio
    async def test_mcp_server_integration(self, tmp_path):
        """Test MCP server configuration loads."""
        mcp_config = {
            "servers": {
                "test-server": {
                    "command": "test-mcp-server",
                    "args": ["--port", "8080"]
                }
            }
        }
        
        (tmp_path / ".mcp.json").write_text(json.dumps(mcp_config))
        
        executor = ClaudeSDKExecutor(Mock())
        options = executor._build_options(tmp_path)
        
        assert options.mcp_servers == mcp_config["servers"]
```

## Success Criteria
- [ ] All unit tests pass (>95% coverage)
- [ ] Contract tests validate SDK matches CLI behavior
- [ ] Performance benchmarks show acceptable overhead (<50% slower)
- [ ] CI pipeline runs all SDK tests
- [ ] Regression tests catch any missing features
- [ ] No flaky tests in the suite

## Test Execution Plan
```bash
# Run all SDK tests
pytest tests/test_sdk_*.py -v

# Run with coverage
pytest tests/test_sdk_*.py --cov=src/agents/claude_code/sdk_executor --cov-report=html

# Run benchmarks
pytest tests/test_sdk_performance.py -m benchmark --benchmark-compare

# Run e2e tests (requires Claude CLI)
pytest -m e2e
```

## Files to Create
- `/tests/test_sdk_executor.py`
- `/tests/test_sdk_contract.py`
- `/tests/test_sdk_performance.py`
- `/tests/test_sdk_regression.py`
- `/.github/workflows/tests.yml` (update)