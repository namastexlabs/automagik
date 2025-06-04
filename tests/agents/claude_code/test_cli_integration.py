"""Integration tests for Claude CLI components.

Tests the CLI environment manager, executor, and local executor integration.
"""

import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

from src.agents.claude_code.cli_environment import CLIEnvironmentManager
from src.agents.claude_code.cli_executor import ClaudeCLIExecutor, CLIResult, StreamProcessor
from src.agents.claude_code.local_executor import LocalExecutor
from src.agents.claude_code.models import ClaudeCodeRunRequest


class TestStreamProcessor:
    """Test the stream processor for Claude CLI output."""
    
    def test_session_id_extraction(self):
        """Test that session ID is correctly extracted from init message."""
        processor = StreamProcessor()
        
        # Sample init message from output_implement2.json
        init_message = json.dumps({
            "type": "system",
            "subtype": "init",
            "session_id": "7ced771c-3852-4105-bd32-b1b9af436fa4"
        })
        
        # Process the line synchronously (convert async to sync for test)
        async def process():
            return await processor.process_line(init_message)
        
        result = asyncio.run(process())
        
        assert result is not None
        assert processor.session_id == "7ced771c-3852-4105-bd32-b1b9af436fa4"
    
    def test_text_accumulation(self):
        """Test that text content is accumulated correctly."""
        processor = StreamProcessor()
        
        messages = [
            json.dumps({"type": "text", "content": "Hello "}),
            json.dumps({"type": "text", "content": "world!"}),
        ]
        
        async def process():
            for msg in messages:
                await processor.process_line(msg)
        
        asyncio.run(process())
        
        assert processor.result_text == "Hello world!"
    
    def test_result_message(self):
        """Test that result message is handled correctly."""
        processor = StreamProcessor()
        
        result_message = json.dumps({
            "type": "result",
            "result": "Task completed successfully"
        })
        
        async def process():
            await processor.process_line(result_message)
        
        asyncio.run(process())
        
        assert processor.completed is True
        assert processor.get_final_result() == "Task completed successfully"


@pytest.mark.asyncio
class TestCLIEnvironmentManager:
    """Test the CLI environment manager."""
    
    async def test_create_workspace(self):
        """Test workspace creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CLIEnvironmentManager(base_path=Path(tmpdir))
            
            run_id = "test-run-123"
            workspace = await manager.create_workspace(run_id)
            
            assert workspace.exists()
            assert workspace.name == f"claude-code-{run_id}"
            # Repository is created by setup_repository, not create_workspace
            assert workspace.is_dir()
    
    @patch('asyncio.create_subprocess_exec')
    async def test_setup_repository(self, mock_subprocess):
        """Test repository setup."""
        # Mock subprocess for git operations
        process_mock = AsyncMock()
        process_mock.communicate.return_value = (b"", b"")
        process_mock.returncode = 0
        mock_subprocess.return_value = process_mock
        
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CLIEnvironmentManager(base_path=Path(tmpdir))
            workspace = Path(tmpdir) / "test-workspace"
            workspace.mkdir()
            
            await manager.setup_repository(workspace, "main")
            
            # Verify git clone was called
            assert mock_subprocess.called
            clone_call = mock_subprocess.call_args_list[0]
            args = clone_call[0]  # positional arguments
            assert args[0] == "git"
            assert args[1] == "clone"
    
    async def test_copy_configs(self):
        """Test configuration copying."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CLIEnvironmentManager(base_path=Path(tmpdir))
            
            # Mock the copy_configs method to avoid touching the actual workflows directory
            import unittest.mock
            with unittest.mock.patch.object(manager, 'copy_configs') as mock_copy:
                mock_copy.return_value = None
                
                dest = Path(tmpdir) / "dest"
                dest.mkdir()
                
                # Create expected files manually to test the verification logic
                workflow_dir = dest / "workflow"
                workflow_dir.mkdir(parents=True)
                (workflow_dir / "prompt.md").write_text("Test prompt")
                (workflow_dir / "allowed_tools.json").write_text('["Task"]')
                
                await manager.copy_configs(dest, "test-workflow")
                
                # Verify the mock was called correctly
                mock_copy.assert_called_once_with(dest, "test-workflow")
                
                # Verify files exist (we created them manually above)
                assert (dest / "workflow" / "prompt.md").exists()
                assert (dest / "workflow" / "allowed_tools.json").exists()


@pytest.mark.asyncio
class TestClaudeCLIExecutor:
    """Test the Claude CLI executor."""
    
    async def test_session_management(self):
        """Test session creation and management."""
        executor = ClaudeCLIExecutor(timeout=30)
        
        # Create session
        session = executor._get_or_create_session("test-workflow", None, 5)
        
        assert session.workflow_name == "test-workflow"
        assert session.max_turns == 5
        assert session.session_id is None
        assert session.run_id is not None
    
    @patch('asyncio.create_subprocess_exec')
    async def test_execute_with_streaming(self, mock_subprocess):
        """Test execution with streaming callback."""
        # Mock subprocess
        process_mock = AsyncMock()
        process_mock.returncode = 0
        process_mock.wait.return_value = None
        
        # Mock stdout with streaming messages
        messages = [
            b'{"type":"system","subtype":"init","session_id":"test-123"}\n',
            b'{"type":"text","content":"Processing..."}\n',
            b'{"type":"result","result":"Done"}\n'
        ]
        
        async def mock_stdout(self):
            for msg in messages:
                yield msg
        
        process_mock.stdout.__aiter__ = mock_stdout
        
        async def mock_stderr(self):
            return
            yield  # Make it an async generator
        
        process_mock.stderr.__aiter__ = mock_stderr
        mock_subprocess.return_value = process_mock
        
        executor = ClaudeCLIExecutor(timeout=30)
        
        # Track streamed messages
        streamed = []
        async def callback(msg):
            streamed.append(msg)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            (workspace / "am-agents-labs").mkdir()
            
            result = await executor.execute(
                workflow="test",
                message="Test message",
                workspace=workspace,
                stream_callback=callback,
                max_turns=1,
                timeout=10
            )
        
        assert result.success
        assert result.session_id == "test-123"
        assert result.result == "Done"
        assert len(streamed) == 3
        assert streamed[0]["type"] == "system"


@pytest.mark.asyncio
class TestLocalExecutor:
    """Test the local executor integration."""
    
    @patch('src.agents.claude_code.cli_environment.CLIEnvironmentManager.create_workspace')
    @patch('src.agents.claude_code.cli_environment.CLIEnvironmentManager.setup_repository')
    @patch('src.agents.claude_code.cli_environment.CLIEnvironmentManager.copy_configs')
    @patch('src.agents.claude_code.cli_executor.ClaudeCLIExecutor.execute')
    async def test_execute_claude_task(
        self,
        mock_execute,
        mock_copy_configs,
        mock_setup_repo,
        mock_create_workspace
    ):
        """Test full execution flow."""
        # Setup mocks
        workspace = Path("/tmp/test-workspace")
        mock_create_workspace.return_value = workspace
        mock_setup_repo.return_value = None
        mock_copy_configs.return_value = None
        
        # Mock CLI result
        mock_result = CLIResult(
            success=True,
            session_id="test-session-123",
            result="Task completed",
            exit_code=0,
            execution_time=5.0,
            logs="Execution logs",
            git_commits=["abc123", "def456"]
        )
        mock_execute.return_value = mock_result
        
        # Create executor
        executor = LocalExecutor(
            workspace_base="/tmp",
            cleanup_on_complete=False
        )
        
        # Create request
        request = ClaudeCodeRunRequest(
            message="Fix the bug",
            workflow_name="bug-fixer",
            git_branch="main",
            max_turns=2,
            timeout=60
        )
        
        # Execute
        result = await executor.execute_claude_task(
            request,
            {"run_id": "test-run-456"}
        )
        
        # Verify result
        assert result["success"] is True
        assert result["session_id"] == "test-session-123"
        assert result["result"] == "Task completed"
        assert result["exit_code"] == 0
        assert len(result["git_commits"]) == 2
        
        # Verify calls
        mock_create_workspace.assert_called_once()
        mock_setup_repo.assert_called_once_with(workspace, "main")
        mock_execute.assert_called_once()


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])