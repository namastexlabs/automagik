"""Regression tests for SDK executor functionality.

These tests ensure that all features continue to work correctly as the SDK evolves,
particularly focusing on edge cases and integration scenarios.
"""

import pytest
import asyncio
import tempfile
import json
import os
from pathlib import Path
from typing import Dict, Any, List
import uuid

from src.agents.claude_code.sdk_executor import SDKExecutor
from src.agents.claude_code.models import ExecutorResult, ToolCapability


class TestSDKRegression:
    """Regression test suite for SDK executor."""
    
    @pytest.fixture
    async def regression_workspace(self):
        """Create a comprehensive test workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create directory structure
            (workspace / "src").mkdir()
            (workspace / "tests").mkdir()
            (workspace / "docs").mkdir()
            (workspace / ".mcp").mkdir()
            
            # Create various test files
            (workspace / "src" / "main.py").write_text("""
import os
import sys

def main():
    print("Hello from main!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
""")
            
            (workspace / "src" / "utils.py").write_text("""
def format_output(data):
    return f"Formatted: {data}"

def parse_input(raw_input):
    return raw_input.strip().split(',')
""")
            
            # Create test with syntax error
            (workspace / "src" / "broken.py").write_text("""
def broken_function():
    print("This has a syntax error"
    # Missing closing parenthesis
""")
            
            # Create prompt.md with complex instructions
            (workspace / "prompt.md").write_text("""
You are an advanced AI coding assistant with the following capabilities:
1. Code analysis and review
2. Bug detection and fixing
3. Performance optimization
4. Test generation

Always follow best practices and explain your reasoning.
When encountering errors, provide helpful suggestions.
""")
            
            # Create complex allowed_tools.json
            allowed_tools = [
                "read_file",
                "write_file",
                "list_directory",
                "run_command",
                "search_files",
                "replace_in_file"
            ]
            (workspace / "allowed_tools.json").write_text(json.dumps(allowed_tools))
            
            # Create MCP configuration
            mcp_config = {
                "servers": {
                    "test-server": {
                        "command": "python",
                        "args": ["-m", "test_mcp_server"],
                        "env": {
                            "TEST_MODE": "true"
                        }
                    }
                }
            }
            (workspace / ".mcp.json").write_text(json.dumps(mcp_config, indent=2))
            
            # Create a large file for stress testing
            large_content = "x" * 10000 + "\n"
            (workspace / "large_file.txt").write_text(large_content * 100)
            
            # Create binary file
            (workspace / "binary_file.bin").write_bytes(bytes(range(256)) * 10)
            
            yield workspace
    
    @pytest.mark.asyncio
    async def test_session_resumption(self, regression_workspace):
        """Test that sessions can be properly resumed."""
        session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        # First session - partial work
        executor1 = SDKExecutor(
            working_dir=str(regression_workspace),
            session_id=session_id,
            model="claude-3-haiku-20240307"
        )
        await executor1.initialize()
        
        # Execute first part
        result1 = await executor1.execute([
            {"role": "user", "content": "Create a new file called session_test.py with a hello function"}
        ])
        assert result1.success
        assert (regression_workspace / "session_test.py").exists()
        
        # Store conversation state
        conversation_state = executor1.get_conversation_state()
        await executor1.cleanup()
        
        # Resume session
        executor2 = SDKExecutor(
            working_dir=str(regression_workspace),
            session_id=session_id,
            model="claude-3-haiku-20240307"
        )
        await executor2.initialize()
        executor2.set_conversation_state(conversation_state)
        
        # Continue work
        result2 = await executor2.execute([
            {"role": "user", "content": "Add a goodbye function to session_test.py"}
        ])
        assert result2.success
        
        # Verify both functions exist
        content = (regression_workspace / "session_test.py").read_text()
        assert "hello" in content
        assert "goodbye" in content
        
        await executor2.cleanup()
    
    @pytest.mark.asyncio
    async def test_mcp_config_loading(self, regression_workspace):
        """Test MCP configuration loading and handling."""
        executor = SDKExecutor(
            working_dir=str(regression_workspace),
            model="claude-3-haiku-20240307"
        )
        await executor.initialize()
        
        # Verify MCP config was loaded
        assert hasattr(executor, 'mcp_config')
        assert executor.mcp_config is not None
        assert "servers" in executor.mcp_config
        assert "test-server" in executor.mcp_config["servers"]
        
        # Test execution with MCP awareness
        result = await executor.execute([
            {"role": "user", "content": "What MCP servers are configured?"}
        ])
        assert result.success
        # Should mention the test server
        assert "test-server" in result.text or "mcp" in result.text.lower()
        
        await executor.cleanup()
    
    @pytest.mark.asyncio
    async def test_error_recovery(self, regression_workspace):
        """Test error handling and recovery mechanisms."""
        executor = SDKExecutor(
            working_dir=str(regression_workspace),
            model="claude-3-haiku-20240307"
        )
        await executor.initialize()
        
        # Test syntax error detection
        result = await executor.execute([
            {"role": "user", "content": "Check the broken.py file for syntax errors and fix them"}
        ])
        assert result.success
        
        # Should identify and potentially fix the syntax error
        assert "syntax" in result.text.lower() or "error" in result.text.lower()
        
        # Test file not found
        result = await executor.execute([
            {"role": "user", "content": "Read the file nonexistent_file.xyz"}
        ])
        assert result.success  # Execution succeeds even if file doesn't exist
        assert "not found" in result.text.lower() or "doesn't exist" in result.text.lower()
        
        await executor.cleanup()
    
    @pytest.mark.asyncio
    async def test_large_file_handling(self, regression_workspace):
        """Test handling of large files."""
        executor = SDKExecutor(
            working_dir=str(regression_workspace),
            model="claude-3-haiku-20240307",
            timeout=60  # Longer timeout for large files
        )
        await executor.initialize()
        
        # Test reading large file
        result = await executor.execute([
            {"role": "user", "content": "How many lines are in large_file.txt?"}
        ])
        assert result.success
        assert "100" in result.text or "hundred" in result.text.lower()
        
        # Test creating large output
        result = await executor.execute([
            {"role": "user", "content": "Create a file called generated_large.txt with 50 lines of 'Test line N'"}
        ])
        assert result.success
        assert (regression_workspace / "generated_large.txt").exists()
        
        await executor.cleanup()
    
    @pytest.mark.asyncio
    async def test_binary_file_handling(self, regression_workspace):
        """Test handling of binary files."""
        executor = SDKExecutor(
            working_dir=str(regression_workspace),
            model="claude-3-haiku-20240307"
        )
        await executor.initialize()
        
        # Test binary file detection
        result = await executor.execute([
            {"role": "user", "content": "What type of file is binary_file.bin?"}
        ])
        assert result.success
        assert "binary" in result.text.lower()
        
        await executor.cleanup()
    
    @pytest.mark.asyncio
    async def test_complex_multi_file_operation(self, regression_workspace):
        """Test complex operations involving multiple files."""
        executor = SDKExecutor(
            working_dir=str(regression_workspace),
            model="claude-3-haiku-20240307",
            max_turns=10
        )
        await executor.initialize()
        
        complex_request = """
        Please do the following:
        1. Analyze all Python files in the src directory
        2. Create a documentation file docs/api.md with function descriptions
        3. Create a test file tests/test_utils.py for the utils module
        4. Run the main.py file and capture its output
        """
        
        result = await executor.execute([
            {"role": "user", "content": complex_request}
        ])
        assert result.success
        
        # Verify files were created
        assert (regression_workspace / "docs" / "api.md").exists()
        assert (regression_workspace / "tests" / "test_utils.py").exists()
        
        # Verify content quality
        api_content = (regression_workspace / "docs" / "api.md").read_text()
        assert "format_output" in api_content
        assert "parse_input" in api_content
        
        test_content = (regression_workspace / "tests" / "test_utils.py").read_text()
        assert "test_" in test_content
        assert "assert" in test_content
        
        await executor.cleanup()
    
    @pytest.mark.asyncio
    async def test_timeout_handling(self, regression_workspace):
        """Test timeout handling for long-running operations."""
        executor = SDKExecutor(
            working_dir=str(regression_workspace),
            model="claude-3-haiku-20240307",
            timeout=5  # Short timeout
        )
        await executor.initialize()
        
        # Request that might take longer
        result = await executor.execute([
            {"role": "user", "content": "Count to 1000000 and tell me when you're done"}
        ])
        
        # Should handle timeout gracefully
        assert result.success or "timeout" in str(result.error).lower()
        
        await executor.cleanup()
    
    @pytest.mark.asyncio
    async def test_special_characters_handling(self, regression_workspace):
        """Test handling of special characters in filenames and content."""
        executor = SDKExecutor(
            working_dir=str(regression_workspace),
            model="claude-3-haiku-20240307"
        )
        await executor.initialize()
        
        # Test special characters in filenames
        result = await executor.execute([
            {"role": "user", "content": 'Create a file called "test-file_v2.0 (beta).txt" with some content'}
        ])
        assert result.success
        
        # Test unicode content
        result = await executor.execute([
            {"role": "user", "content": "Create a file unicode_test.txt with content: Hello 世界 🌍"}
        ])
        assert result.success
        assert (regression_workspace / "unicode_test.txt").exists()
        
        content = (regression_workspace / "unicode_test.txt").read_text(encoding='utf-8')
        assert "世界" in content
        assert "🌍" in content
        
        await executor.cleanup()
    
    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self, regression_workspace):
        """Test handling of concurrent file operations."""
        executor = SDKExecutor(
            working_dir=str(regression_workspace),
            model="claude-3-haiku-20240307"
        )
        await executor.initialize()
        
        # Request multiple file operations
        result = await executor.execute([{
            "role": "user",
            "content": """
            Simultaneously:
            1. Read all Python files in src/
            2. Create summaries for each in docs/
            3. Count total lines of code
            4. List all files created
            """
        }])
        assert result.success
        
        # Verify summaries were created
        docs_files = list((regression_workspace / "docs").glob("*.md"))
        assert len(docs_files) >= 2  # At least main.py and utils.py summaries
        
        await executor.cleanup()
    
    @pytest.mark.asyncio
    async def test_environment_variable_handling(self, regression_workspace):
        """Test environment variable handling in command execution."""
        executor = SDKExecutor(
            working_dir=str(regression_workspace),
            model="claude-3-haiku-20240307"
        )
        await executor.initialize()
        
        # Create a script that uses environment variables
        script_content = """
import os
print(f"HOME: {os.environ.get('HOME', 'not set')}")
print(f"USER: {os.environ.get('USER', 'not set')}")
print(f"CUSTOM_VAR: {os.environ.get('CUSTOM_VAR', 'not set')}")
"""
        (regression_workspace / "env_test.py").write_text(script_content)
        
        result = await executor.execute([
            {"role": "user", "content": "Run env_test.py and show me the output"}
        ])
        assert result.success
        assert "HOME:" in result.text
        
        await executor.cleanup()
    
    @pytest.mark.asyncio
    async def test_max_turns_enforcement(self, regression_workspace):
        """Test that max_turns is properly enforced."""
        executor = SDKExecutor(
            working_dir=str(regression_workspace),
            model="claude-3-haiku-20240307",
            max_turns=2  # Very limited turns
        )
        await executor.initialize()
        
        # Request that would normally take multiple turns
        result = await executor.execute([{
            "role": "user",
            "content": """
            1. List all files
            2. Read each Python file
            3. Create documentation for each
            4. Create tests for each
            5. Run all tests
            """
        }])
        
        # Should complete within turn limit
        assert result.success or result.reached_turn_limit
        
        await executor.cleanup()
    
    @pytest.mark.asyncio
    async def test_custom_tools_configuration(self, regression_workspace):
        """Test custom tool configuration handling."""
        # Create custom allowed_tools.json with limited tools
        limited_tools = ["read_file", "list_directory"]
        (regression_workspace / "allowed_tools.json").write_text(json.dumps(limited_tools))
        
        executor = SDKExecutor(
            working_dir=str(regression_workspace),
            model="claude-3-haiku-20240307"
        )
        await executor.initialize()
        
        # Try to use a disallowed tool
        result = await executor.execute([
            {"role": "user", "content": "Create a new file called test.txt"}
        ])
        assert result.success
        
        # Should indicate it cannot write files
        assert "can't" in result.text.lower() or "cannot" in result.text.lower() or "unable" in result.text.lower()
        
        await executor.cleanup()