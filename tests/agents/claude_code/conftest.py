"""Pytest configuration for Claude-Code agent tests.

This module provides shared fixtures and configuration for all Claude-Code tests.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../'))


@pytest.fixture
def mock_docker_client():
    """Provide a mocked Docker client."""
    mock_client = Mock()
    mock_client.ping.return_value = True
    mock_client.images.get.return_value = Mock()  # Image exists
    mock_client.containers.create.return_value = Mock(id="test_container")
    return mock_client


@pytest.fixture
def mock_container_manager():
    """Provide a mocked ContainerManager."""
    from src.agents.claude_code.container import ContainerManager
    
    manager = Mock(spec=ContainerManager)
    manager.docker_client = Mock()
    manager.create_container = AsyncMock(return_value="container_123")
    manager.start_container = AsyncMock(return_value=True)
    manager.wait_for_completion = AsyncMock(return_value={
        'success': True,
        'exit_code': 0,
        'result': 'Test completed'
    })
    manager.active_containers = {}
    return manager


@pytest.fixture
def mock_executor(mock_container_manager):
    """Provide a mocked ClaudeExecutor."""
    from src.agents.claude_code.executor import ClaudeExecutor
    
    executor = ClaudeExecutor(mock_container_manager)
    executor.execute_claude_task = AsyncMock(return_value={
        'success': True,
        'result': 'Task completed',
        'container_id': 'container_123',
        'execution_time': 10.0
    })
    return executor


@pytest.fixture
def claude_code_agent(mock_container_manager, mock_executor):
    """Provide a ClaudeCodeAgent instance with mocked dependencies."""
    from src.agents.claude_code.agent import ClaudeCodeAgent
    
    with patch('src.agents.claude_code.agent.ContainerManager', return_value=mock_container_manager):
        with patch('src.agents.claude_code.agent.ClaudeExecutor', return_value=mock_executor):
            agent = ClaudeCodeAgent({})
            agent._validate_workflow = AsyncMock(return_value=True)
            return agent


@pytest.fixture
def mock_settings():
    """Provide mocked settings with claude-code enabled."""
    with patch('src.agents.claude_code.agent.settings') as mock_settings:
        mock_settings.AM_ENABLE_CLAUDE_CODE = True
        yield mock_settings


@pytest.fixture
def sample_request():
    """Provide a sample ClaudeCodeRunRequest."""
    from src.agents.claude_code.models import ClaudeCodeRunRequest
    
    return ClaudeCodeRunRequest(
        message="Fix the bug in session controller",
        workflow_name="fix",
        session_id="test_session_123",
        max_turns=30,
        git_branch="test-branch"
    )


@pytest.fixture
def workflow_config():
    """Provide a sample workflow configuration."""
    return {
        'name': 'test-workflow',
        'path': '/path/to/workflow',
        'prompt': 'Test workflow prompt',
        'mcp_config': {'test': 'config'},
        'allowed_tools': ['tool1', 'tool2']
    }


@pytest.fixture
async def async_test_timeout():
    """Provide a timeout for async tests to prevent hanging."""
    timeout = 5.0  # 5 seconds default timeout
    
    async def run_with_timeout(coro):
        return await asyncio.wait_for(coro, timeout=timeout)
    
    return run_with_timeout


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment between tests."""
    # Store original env
    original_env = os.environ.copy()
    
    yield
    
    # Restore original env
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def temp_workflow_dir(tmp_path):
    """Create a temporary workflow directory structure."""
    workflow_dir = tmp_path / "test_workflow"
    workflow_dir.mkdir()
    
    # Create required files
    (workflow_dir / "prompt.md").write_text("# Test Workflow\\nTest prompt content")
    (workflow_dir / "allowed_tools.json").write_text('["tool1", "tool2"]')
    (workflow_dir / ".mcp.json").write_text('{"test": "config"}')
    
    return str(workflow_dir)