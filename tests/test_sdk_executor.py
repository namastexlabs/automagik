"""Tests for ClaudeSDKExecutor."""

import pytest
import asyncio
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add local SDK to path if available
local_sdk_path = Path(__file__).parent.parent / "src" / "vendors" / "claude-code-sdk" / "src"
if local_sdk_path.exists():
    sys.path.insert(0, str(local_sdk_path))

from src.agents.claude_code.sdk_executor import ClaudeSDKExecutor
from src.agents.claude_code.cli_environment import CLIEnvironmentManager
from claude_code_sdk import UserMessage, AssistantMessage, SystemMessage, ResultMessage, TextBlock, ClaudeCodeOptions


@pytest.fixture
def mock_env_manager():
    """Create mock environment manager."""
    env_mgr = MagicMock(spec=CLIEnvironmentManager)
    # Mock the as_dict method properly
    env_mgr.as_dict = MagicMock(return_value={"ENV_VAR": "test"})
    return env_mgr


@pytest.fixture
def sdk_executor(mock_env_manager):
    """Create SDK executor instance."""
    return ClaudeSDKExecutor(mock_env_manager)


@pytest.fixture
def temp_workspace():
    """Create temporary workspace directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.mark.asyncio
async def test_basic_execution(sdk_executor, temp_workspace):
    """Test basic prompt execution."""
    # Mock the query function
    mock_messages = [
        UserMessage(content="What is 2+2?"),
        AssistantMessage(content=[TextBlock(text="2+2 equals 4")]),
        ResultMessage(
            subtype="completed",
            duration_ms=1000,
            duration_api_ms=800,
            is_error=False,
            num_turns=1,
            session_id="test-session",
            result="4"
        )
    ]
    
    with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
        # Create async generator
        async def mock_generator(*args, **kwargs):
            for msg in mock_messages:
                yield msg
        
        mock_query.side_effect = lambda prompt, options: mock_generator(prompt, options)
        
        result = await sdk_executor.execute(
            "What is 2+2?",
            workspace=temp_workspace
        )
        
        assert result.success
        assert result.exit_code == 0
        assert len(result.streaming_messages) == 3
        assert any(msg['role'] == 'assistant' for msg in result.streaming_messages)
        assert "4" in result.result


@pytest.mark.asyncio
async def test_system_prompt_loading(sdk_executor, temp_workspace):
    """Test prompt.md loads as system_prompt."""
    # Create prompt.md
    prompt_content = "You are a helpful assistant."
    (temp_workspace / "prompt.md").write_text(prompt_content)
    
    with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
        async def mock_generator(prompt, options=None):
            # Verify system_prompt was set correctly
            assert options is not None
            assert options.system_prompt == prompt_content
            # Not append_system_prompt
            assert options.append_system_prompt is None
            yield AssistantMessage(content=[TextBlock(text="Test response")])
        
        mock_query.side_effect = lambda prompt, options: mock_generator(prompt, options)
        
        result = await sdk_executor.execute(
            "Test prompt",
            workspace=temp_workspace
        )
        
        assert result.success


@pytest.mark.asyncio
async def test_mcp_config_loading(sdk_executor, temp_workspace):
    """Test .mcp.json loading."""
    mcp_config = {
        "servers": {
            "test-server": {
                "command": "test-cmd",
                "args": ["arg1", "arg2"]
            }
        }
    }
    (temp_workspace / ".mcp.json").write_text(json.dumps(mcp_config))
    
    with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
        async def mock_generator(prompt, options=None):
            # Verify MCP servers were loaded
            assert options is not None
            assert len(options.mcp_servers) == 1
            assert "test-server" in options.mcp_servers
            yield AssistantMessage(content=[TextBlock(text="Test response")])
        
        mock_query.side_effect = lambda prompt, options: mock_generator(prompt, options)
        
        result = await sdk_executor.execute(
            "Test prompt",
            workspace=temp_workspace
        )
        
        assert result.success


@pytest.mark.asyncio
async def test_allowed_tools_loading(sdk_executor, temp_workspace):
    """Test allowed_tools.json loading."""
    allowed_tools = ["Bash", "Read", "Write", "CustomTool"]
    (temp_workspace / "allowed_tools.json").write_text(json.dumps(allowed_tools))
    
    with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
        async def mock_generator(prompt, options=None):
            # Verify allowed tools were loaded
            assert options is not None
            assert options.allowed_tools == allowed_tools
            yield AssistantMessage(content=[TextBlock(text="Test response")])
        
        mock_query.side_effect = lambda prompt, options: mock_generator(prompt, options)
        
        result = await sdk_executor.execute(
            "Test prompt",
            workspace=temp_workspace
        )
        
        assert result.success


@pytest.mark.asyncio
async def test_default_allowed_tools(sdk_executor, temp_workspace):
    """Test default allowed tools when no file exists."""
    with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
        async def mock_generator(prompt, options=None):
            # Verify default tools were set
            assert options is not None
            expected_tools = ["Bash", "LS", "Read", "Write", "Edit", "Glob", "Grep", "Task"]
            assert options.allowed_tools == expected_tools
            yield AssistantMessage(content=[TextBlock(text="Test response")])
        
        mock_query.side_effect = lambda prompt, options: mock_generator(prompt, options)
        
        result = await sdk_executor.execute(
            "Test prompt",
            workspace=temp_workspace
        )
        
        assert result.success


@pytest.mark.asyncio
async def test_timeout_handling(sdk_executor, temp_workspace):
    """Test timeout handling."""
    with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
        async def mock_generator(*args, **kwargs):
            # Simulate long-running operation
            await asyncio.sleep(2)
            yield AssistantMessage(content=[TextBlock(text="Test response")])
        
        mock_query.side_effect = lambda prompt, options: mock_generator(prompt, options)
        
        result = await sdk_executor.execute(
            "Test prompt",
            workspace=temp_workspace,
            timeout=0.1  # Very short timeout
        )
        
        assert not result.success
        assert result.exit_code == 1
        assert "timed out" in result.error.lower()


@pytest.mark.asyncio
async def test_execute_until_first_response(sdk_executor, temp_workspace):
    """Test execute_until_first_response method."""
    mock_messages = [
        UserMessage(content="Test prompt"),
        SystemMessage(subtype="info", data={"message": "Processing..."}),
        AssistantMessage(content=[TextBlock(text="First response")]),
        AssistantMessage(content=[TextBlock(text="Second response")]),
        ResultMessage(
            subtype="completed",
            duration_ms=2000,
            duration_api_ms=1500,
            is_error=False,
            num_turns=2,
            session_id="test-session",
            result="Complete"
        )
    ]
    
    with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
        async def mock_generator(*args, **kwargs):
            for msg in mock_messages:
                yield msg
        
        mock_query.side_effect = lambda prompt, options: mock_generator(prompt, options)
        
        consumed, continuation_task = await sdk_executor.execute_until_first_response(
            "Test prompt",
            workspace=temp_workspace
        )
        
        # Should consume up to and including first assistant message
        assert len(consumed) == 3
        assert consumed[0]['role'] == 'user'
        assert consumed[1]['role'] == 'system'
        assert consumed[2]['role'] == 'assistant'
        assert consumed[2]['content'] == "First response"
        
        # Continue to get remaining messages
        all_messages = await continuation_task
        assert len(all_messages) == 5
        assert all_messages[3]['content'] == "Second response"
        assert all_messages[4]['role'] == 'result'


@pytest.mark.asyncio
async def test_session_resumption(sdk_executor, temp_workspace):
    """Test session resumption with resume parameter."""
    session_id = "test-session-123"
    
    with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
        async def mock_generator(prompt, options=None):
            # Verify resume was set correctly
            assert options is not None
            assert options.resume == session_id
            yield AssistantMessage(content=[TextBlock(text="Resumed session")])
        
        mock_query.side_effect = lambda prompt, options: mock_generator(prompt, options)
        
        result = await sdk_executor.execute(
            "Continue conversation",
            workspace=temp_workspace,
            resume_session_id=session_id
        )
        
        assert result.success
        assert "Resumed session" in result.result


@pytest.mark.asyncio
async def test_model_selection(sdk_executor, temp_workspace):
    """Test model parameter."""
    with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
        async def mock_generator(prompt, options=None):
            # Verify model was set
            assert options is not None
            assert options.model == "claude-3-sonnet"
            yield AssistantMessage(content=[TextBlock(text="Test response")])
        
        mock_query.side_effect = lambda prompt, options: mock_generator(prompt, options)
        
        result = await sdk_executor.execute(
            "Test prompt",
            workspace=temp_workspace,
            model="claude-3-sonnet"
        )
        
        assert result.success


@pytest.mark.asyncio
async def test_max_turns_configuration(sdk_executor, temp_workspace):
    """Test max_turns parameter."""
    with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
        async def mock_generator(prompt, options=None):
            # Verify max_turns was set
            assert options is not None
            assert options.max_turns == 5
            yield AssistantMessage(content=[TextBlock(text="Test response")])
        
        mock_query.side_effect = lambda prompt, options: mock_generator(prompt, options)
        
        result = await sdk_executor.execute(
            "Test prompt",
            workspace=temp_workspace,
            max_turns=5
        )
        
        assert result.success


@pytest.mark.asyncio
async def test_error_handling(sdk_executor, temp_workspace):
    """Test error handling during execution."""
    with patch('src.agents.claude_code.sdk_executor.query') as mock_query:
        # Mock query to raise the error directly
        mock_query.side_effect = RuntimeError("Test error")
        
        result = await sdk_executor.execute(
            "Test prompt",
            workspace=temp_workspace
        )
        
        assert not result.success
        assert result.exit_code == 1
        assert "Test error" in result.error
        assert "Test error" in result.result


@pytest.mark.asyncio
async def test_message_conversion(sdk_executor, temp_workspace):
    """Test message type conversion."""
    # Test direct conversion method
    user_msg = UserMessage(content="User test")
    converted = sdk_executor._convert_message(user_msg)
    assert converted['role'] == 'user'
    assert converted['content'] == "User test"
    assert 'timestamp' in converted
    
    assistant_msg = AssistantMessage(content=[TextBlock(text="Assistant test")])
    converted = sdk_executor._convert_message(assistant_msg)
    assert converted['role'] == 'assistant'
    assert converted['content'] == "Assistant test"
    
    system_msg = SystemMessage(subtype="info", data={"message": "System test"})
    converted = sdk_executor._convert_message(system_msg)
    assert converted['role'] == 'system'
    assert converted['content'] == "System test"
    
    result_msg = ResultMessage(
        subtype="completed",
        duration_ms=100,
        duration_api_ms=80,
        is_error=False,
        num_turns=1,
        session_id="test",
        result="Result test"
    )
    converted = sdk_executor._convert_message(result_msg)
    assert converted['role'] == 'result'
    assert converted['result'] == "Result test"
    assert converted['success'] is True  # Should be based on is_error


@pytest.mark.asyncio
async def test_result_text_extraction(sdk_executor):
    """Test result text extraction from messages."""
    messages = [
        {'role': 'user', 'content': 'Test'},
        {'role': 'assistant', 'content': 'First response'},
        {'role': 'system', 'content': 'System message'},
        {'role': 'assistant', 'content': 'Second response'},
        {'role': 'result', 'result': 'Final result'}
    ]
    
    result_text = sdk_executor._extract_result_text(messages)
    
    # Should combine assistant content and result
    assert "First response" in result_text
    assert "Second response" in result_text
    assert "Final result" in result_text
    # Should not include system or user messages
    assert "Test" not in result_text
    assert "System message" not in result_text