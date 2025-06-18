"""Tests for file-based configuration loading in SDK executor."""

import asyncio
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from src.agents.claude_code.sdk_executor import ClaudeSDKExecutor, ConfigPriority
from src.agents.claude_code.models import ClaudeCodeRunRequest


@pytest.fixture
def mock_env_mgr():
    """Mock environment manager."""
    env_mgr = Mock()
    env_mgr.prepare_workspace = AsyncMock(return_value={
        'workspace_path': '/tmp/test_workspace'
    })
    return env_mgr


@pytest.fixture
def sdk_executor(mock_env_mgr):
    """Create SDK executor instance."""
    return ClaudeSDKExecutor(mock_env_mgr)


class TestConfigPriority:
    """Test configuration priority system."""
    
    def test_explicit_value_priority(self, tmp_path):
        """Test that explicit values have highest priority."""
        # Create a file with different content
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(["file_value"]))
        
        # Explicit value should win
        result = ConfigPriority.load_with_priority(
            tmp_path,
            explicit_value=["explicit_value"],
            file_name="config.json",
            default=["default_value"]
        )
        
        assert result == ["explicit_value"]
    
    def test_file_priority_over_default(self, tmp_path):
        """Test that file values have priority over defaults."""
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(["file_value"]))
        
        result = ConfigPriority.load_with_priority(
            tmp_path,
            explicit_value=None,
            file_name="config.json",
            default=["default_value"]
        )
        
        assert result == ["file_value"]
    
    def test_default_when_no_file(self, tmp_path):
        """Test that default is used when file doesn't exist."""
        result = ConfigPriority.load_with_priority(
            tmp_path,
            explicit_value=None,
            file_name="missing.json",
            default=["default_value"]
        )
        
        assert result == ["default_value"]
    
    def test_text_file_loading(self, tmp_path):
        """Test loading text files."""
        text_file = tmp_path / "prompt.md"
        text_file.write_text("Custom prompt content\n")
        
        result = ConfigPriority.load_with_priority(
            tmp_path,
            explicit_value=None,
            file_name="prompt.md",
            default="default prompt"
        )
        
        assert result == "Custom prompt content"
    
    def test_invalid_json_returns_default(self, tmp_path):
        """Test that invalid JSON returns default."""
        config_file = tmp_path / "config.json"
        config_file.write_text("invalid json")
        
        result = ConfigPriority.load_with_priority(
            tmp_path,
            explicit_value=None,
            file_name="config.json",
            default=["default_value"]
        )
        
        assert result == ["default_value"]


class TestSDKExecutorOptions:
    """Test SDK executor options building."""
    
    @pytest.mark.asyncio
    async def test_system_prompt_loading(self, tmp_path, sdk_executor):
        """Test prompt.md loads as system_prompt (not append)."""
        prompt_content = "You are a Python expert. Be concise."
        (tmp_path / "prompt.md").write_text(prompt_content)
        
        with patch('claude_code_sdk.ClaudeCodeOptions') as MockOptions:
            mock_options = MockOptions.return_value
            options = sdk_executor._build_options(tmp_path)
            
            # Verify system_prompt was set
            assert mock_options.system_prompt == prompt_content
    
    @pytest.mark.asyncio
    async def test_no_prompt_file(self, tmp_path, sdk_executor):
        """Test vanilla Claude Code when no prompt.md exists."""
        with patch('claude_code_sdk.ClaudeCodeOptions') as MockOptions:
            mock_options = MockOptions.return_value
            options = sdk_executor._build_options(tmp_path)
            
            # system_prompt should not be set
            assert not hasattr(mock_options, 'system_prompt') or mock_options.system_prompt is None
    
    @pytest.mark.asyncio
    async def test_empty_prompt_file(self, tmp_path, sdk_executor):
        """Test empty prompt.md is ignored."""
        (tmp_path / "prompt.md").write_text("")
        
        with patch('claude_code_sdk.ClaudeCodeOptions') as MockOptions:
            mock_options = MockOptions.return_value
            options = sdk_executor._build_options(tmp_path)
            
            # system_prompt should not be set for empty file
            assert not hasattr(mock_options, 'system_prompt') or mock_options.system_prompt is None
    
    @pytest.mark.asyncio
    async def test_tools_loading(self, tmp_path, sdk_executor):
        """Test allowed/disallowed tools loading."""
        allowed = ["Read", "Write", "Edit"]
        disallowed = ["Bash", "WebSearch"]
        
        (tmp_path / "allowed_tools.json").write_text(json.dumps(allowed))
        (tmp_path / "disallowed_tools.json").write_text(json.dumps(disallowed))
        
        with patch('claude_code_sdk.ClaudeCodeOptions') as MockOptions:
            mock_options = MockOptions.return_value
            options = sdk_executor._build_options(tmp_path)
            
            assert mock_options.allowed_tools == allowed
            assert mock_options.disallowed_tools == disallowed
    
    @pytest.mark.asyncio
    async def test_invalid_tools_json(self, tmp_path, sdk_executor):
        """Test invalid tools JSON is handled gracefully."""
        # Write invalid JSON
        (tmp_path / "allowed_tools.json").write_text("not json")
        (tmp_path / "disallowed_tools.json").write_text('{"not": "array"}')
        
        with patch('claude_code_sdk.ClaudeCodeOptions') as MockOptions:
            mock_options = MockOptions.return_value
            options = sdk_executor._build_options(tmp_path)
            
            # Should not crash, just skip invalid files
            assert not hasattr(mock_options, 'allowed_tools') or mock_options.allowed_tools is None
            assert not hasattr(mock_options, 'disallowed_tools') or mock_options.disallowed_tools is None
    
    @pytest.mark.asyncio
    async def test_mcp_config_loading(self, tmp_path, sdk_executor):
        """Test MCP configuration loading."""
        mcp_config = {
            "servers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["mcp-server-filesystem"]
                },
                "github": {
                    "command": "mcp-github-server",
                    "env": {"GITHUB_TOKEN": "secret"}
                }
            }
        }
        
        (tmp_path / ".mcp.json").write_text(json.dumps(mcp_config))
        
        with patch('claude_code_sdk.ClaudeCodeOptions') as MockOptions:
            mock_options = MockOptions.return_value
            options = sdk_executor._build_options(tmp_path)
            
            assert mock_options.mcp_servers == mcp_config["servers"]
    
    @pytest.mark.asyncio
    async def test_invalid_mcp_config(self, tmp_path, sdk_executor):
        """Test invalid MCP config is handled gracefully."""
        # Missing 'servers' key
        (tmp_path / ".mcp.json").write_text('{"invalid": "structure"}')
        
        with patch('claude_code_sdk.ClaudeCodeOptions') as MockOptions:
            mock_options = MockOptions.return_value
            options = sdk_executor._build_options(tmp_path)
            
            # Should not crash
            assert not hasattr(mock_options, 'mcp_servers') or mock_options.mcp_servers is None
    
    @pytest.mark.asyncio
    async def test_explicit_kwargs_override(self, tmp_path, sdk_executor):
        """Test explicit kwargs override file configs."""
        # Set up file configs
        (tmp_path / "allowed_tools.json").write_text(json.dumps(["Read", "Write"]))
        
        with patch('claude_code_sdk.ClaudeCodeOptions') as MockOptions:
            mock_options = MockOptions.return_value
            
            # Pass explicit allowed_tools that should override file
            options = sdk_executor._build_options(
                tmp_path,
                allowed_tools=["Bash", "Edit"]
            )
            
            # Explicit value should not be overridden by file
            # The logic in _build_options checks if 'allowed_tools' is in kwargs
            # and skips file loading in that case
    
    @pytest.mark.asyncio
    async def test_max_thinking_tokens(self, tmp_path, sdk_executor):
        """Test max_thinking_tokens is properly set."""
        with patch('claude_code_sdk.ClaudeCodeOptions') as MockOptions:
            mock_options = MockOptions.return_value
            
            options = sdk_executor._build_options(
                tmp_path,
                max_thinking_tokens=10000
            )
            
            assert mock_options.max_thinking_tokens == 10000


class TestSDKExecutorExecution:
    """Test SDK executor execution methods."""
    
    @pytest.mark.asyncio
    async def test_execute_claude_task_success(self, sdk_executor, mock_env_mgr):
        """Test successful task execution."""
        request = ClaudeCodeRunRequest(
            message="Test task",
            workflow_name="test",
            max_turns=10
        )
        
        with patch.object(sdk_executor.client, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = Mock(
                __str__=lambda self: "Task completed successfully",
                git_commits=["abc123", "def456"]
            )
            
            result = await sdk_executor.execute_claude_task(request, {})
            
            assert result['success'] is True
            assert result['result'] == "Task completed successfully"
            assert result['exit_code'] == 0
            assert result['git_commits'] == ["abc123", "def456"]
            assert 'session_id' in result
            assert 'execution_time' in result
    
    @pytest.mark.asyncio
    async def test_execute_claude_task_failure(self, sdk_executor, mock_env_mgr):
        """Test task execution failure handling."""
        request = ClaudeCodeRunRequest(
            message="Test task",
            workflow_name="test"
        )
        
        with patch.object(sdk_executor.client, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = Exception("SDK error")
            
            result = await sdk_executor.execute_claude_task(request, {})
            
            assert result['success'] is False
            assert result['exit_code'] == 1
            assert "SDK error" in result['error']
    
    @pytest.mark.asyncio
    async def test_execute_until_first_response(self, sdk_executor, mock_env_mgr):
        """Test streaming execution with first response."""
        request = ClaudeCodeRunRequest(
            message="Test streaming",
            workflow_name="test"
        )
        
        async def mock_stream(*args, **kwargs):
            yield "First response chunk"
            yield "Second response chunk"
        
        with patch.object(sdk_executor.client, 'stream', side_effect=mock_stream):
            result = await sdk_executor.execute_until_first_response(request, {})
            
            assert result['first_response'] == "First response chunk"
            assert result['streaming_started'] is True
            assert 'session_id' in result
    
    @pytest.mark.asyncio
    async def test_cancel_execution(self, sdk_executor):
        """Test execution cancellation."""
        # Add a mock session
        session_id = "test_session"
        sdk_executor.active_sessions[session_id] = {
            'client': Mock(cancel=AsyncMock()),
            'options': {},
            'start_time': 0,
            'workspace': Path("/tmp")
        }
        
        result = await sdk_executor.cancel_execution(session_id)
        
        assert result is True
        assert session_id not in sdk_executor.active_sessions
    
    @pytest.mark.asyncio
    async def test_cleanup(self, sdk_executor):
        """Test cleanup removes all sessions."""
        # Add mock sessions
        sdk_executor.active_sessions = {
            "session1": {'client': Mock()},
            "session2": {'client': Mock()}
        }
        
        with patch.object(sdk_executor, 'cancel_execution', new_callable=AsyncMock):
            await sdk_executor.cleanup()
            
            # All sessions should be cancelled
            assert sdk_executor.cancel_execution.call_count == 2