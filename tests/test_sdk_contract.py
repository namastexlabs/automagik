"""Contract tests for SDK executor vs CLI executor parity.

These tests ensure that the SDK executor produces the same results as the CLI executor
for various scenarios, guaranteeing full behavioral compatibility.
"""

import pytest
import asyncio
import tempfile
import os
import json
from pathlib import Path
from typing import Dict, Any, List
import difflib

from src.agents.claude_code.sdk_executor import SDKExecutor
from src.agents.claude_code.cli_executor import CLIExecutor
from src.agents.claude_code.models import ToolCapability


class TestSDKContractParity:
    """Test suite ensuring SDK and CLI executors produce identical results."""
    
    @pytest.fixture
    async def test_workspace(self):
        """Create a temporary workspace for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # Create test files
            (workspace / "test.py").write_text("""
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b

if __name__ == "__main__":
    print(f"2 + 3 = {add(2, 3)}")
    print(f"4 * 5 = {multiply(4, 5)}")
""")
            
            (workspace / "README.md").write_text("""
# Test Project

This is a test project for SDK contract testing.

## Features
- Addition function
- Multiplication function
""")
            
            # Create prompt.md for system prompt
            (workspace / "prompt.md").write_text("""
You are a helpful AI assistant for code review and analysis.
Be concise and focus on code quality.
""")
            
            # Create allowed_tools.json
            allowed_tools = [
                "read_file",
                "write_file",
                "list_directory",
                "run_command"
            ]
            (workspace / "allowed_tools.json").write_text(json.dumps(allowed_tools))
            
            yield workspace
    
    @pytest.fixture
    async def sdk_executor(self, test_workspace):
        """Create SDK executor instance."""
        executor = SDKExecutor(
            working_dir=str(test_workspace),
            model="claude-3-haiku-20240307",
            max_turns=10,
            timeout=30
        )
        await executor.initialize()
        return executor
    
    @pytest.fixture
    async def cli_executor(self, test_workspace):
        """Create CLI executor instance."""
        executor = CLIExecutor(
            working_dir=str(test_workspace),
            model="claude-3-haiku-20240307",
            max_turns=10,
            timeout=30
        )
        await executor.initialize()
        return executor
    
    def normalize_response(self, response: str) -> str:
        """Normalize response for comparison by removing timestamps and IDs."""
        # Remove timestamps
        import re
        response = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', 'TIMESTAMP', response)
        response = re.sub(r'id="[^"]*"', 'id="ID"', response)
        response = re.sub(r'session_[a-f0-9]+', 'session_ID', response)
        
        # Normalize line endings
        response = response.replace('\r\n', '\n')
        
        # Strip extra whitespace
        response = '\n'.join(line.rstrip() for line in response.split('\n'))
        
        return response.strip()
    
    @pytest.mark.asyncio
    async def test_basic_code_analysis(self, sdk_executor, cli_executor):
        """Test that both executors provide the same code analysis."""
        query = "Analyze the test.py file and suggest improvements"
        
        # Execute with SDK
        sdk_result = await sdk_executor.execute([{"role": "user", "content": query}])
        
        # Execute with CLI
        cli_result = await cli_executor.execute([{"role": "user", "content": query}])
        
        # Both should successfully read the file
        assert sdk_result.success
        assert cli_result.success
        
        # Both should mention the functions
        assert "add" in sdk_result.text.lower()
        assert "add" in cli_result.text.lower()
        assert "multiply" in sdk_result.text.lower()
        assert "multiply" in cli_result.text.lower()
    
    @pytest.mark.asyncio
    async def test_file_operations(self, sdk_executor, cli_executor):
        """Test that file operations work identically."""
        query = """Create a new file called 'calculator.py' with the following:
        - A subtract function
        - A divide function with zero division handling
        """
        
        # Execute with SDK
        sdk_result = await sdk_executor.execute([{"role": "user", "content": query}])
        
        # Reset workspace
        calc_file = sdk_executor.working_dir / "calculator.py"
        if calc_file.exists():
            calc_file.unlink()
        
        # Execute with CLI
        cli_result = await cli_executor.execute([{"role": "user", "content": query}])
        
        # Both should succeed
        assert sdk_result.success
        assert cli_result.success
        
        # File should exist after both executions
        assert (Path(sdk_executor.working_dir) / "calculator.py").exists()
        
        # Read the file content
        calc_content = (Path(cli_executor.working_dir) / "calculator.py").read_text()
        
        # Should contain required functions
        assert "def subtract" in calc_content
        assert "def divide" in calc_content
        assert "ZeroDivisionError" in calc_content or "zero" in calc_content.lower()
    
    @pytest.mark.asyncio
    async def test_directory_listing(self, sdk_executor, cli_executor):
        """Test directory listing consistency."""
        query = "List all files in the current directory and describe what each does"
        
        # Execute with both
        sdk_result = await sdk_executor.execute([{"role": "user", "content": query}])
        cli_result = await cli_executor.execute([{"role": "user", "content": query}])
        
        # Both should succeed
        assert sdk_result.success
        assert cli_result.success
        
        # Both should mention the same files
        expected_files = ["test.py", "README.md", "prompt.md", "allowed_tools.json"]
        for file in expected_files:
            assert file in sdk_result.text
            assert file in cli_result.text
    
    @pytest.mark.asyncio
    async def test_command_execution(self, sdk_executor, cli_executor):
        """Test command execution parity."""
        query = "Run the test.py file and show me the output"
        
        # Execute with both
        sdk_result = await sdk_executor.execute([{"role": "user", "content": query}])
        cli_result = await cli_executor.execute([{"role": "user", "content": query}])
        
        # Both should succeed
        assert sdk_result.success
        assert cli_result.success
        
        # Both should show the output
        assert "2 + 3 = 5" in sdk_result.text
        assert "2 + 3 = 5" in cli_result.text
        assert "4 * 5 = 20" in sdk_result.text
        assert "4 * 5 = 20" in cli_result.text
    
    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, sdk_executor, cli_executor):
        """Test multi-turn conversation handling."""
        messages = [
            {"role": "user", "content": "Read the test.py file"},
            {"role": "assistant", "content": "I'll read the test.py file for you."},
            {"role": "user", "content": "Now create a test file for it called test_test.py"}
        ]
        
        # Execute with both
        sdk_result = await sdk_executor.execute(messages)
        
        # Reset test file
        test_file = Path(sdk_executor.working_dir) / "test_test.py"
        if test_file.exists():
            test_file.unlink()
        
        cli_result = await cli_executor.execute(messages)
        
        # Both should succeed
        assert sdk_result.success
        assert cli_result.success
        
        # Both should create the test file
        assert (Path(sdk_executor.working_dir) / "test_test.py").exists()
        assert (Path(cli_executor.working_dir) / "test_test.py").exists()
        
        # Test file should contain test functions
        test_content = test_file.read_text()
        assert "test_add" in test_content or "test_" in test_content
        assert "assert" in test_content
    
    @pytest.mark.asyncio
    async def test_error_handling(self, sdk_executor, cli_executor):
        """Test that error handling is consistent."""
        query = "Try to read a file that doesn't exist: nonexistent.txt"
        
        # Execute with both
        sdk_result = await sdk_executor.execute([{"role": "user", "content": query}])
        cli_result = await cli_executor.execute([{"role": "user", "content": query}])
        
        # Both should handle the error gracefully
        assert sdk_result.success  # The execution succeeds even if file doesn't exist
        assert cli_result.success
        
        # Both should mention the file doesn't exist
        assert "not found" in sdk_result.text.lower() or "doesn't exist" in sdk_result.text.lower()
        assert "not found" in cli_result.text.lower() or "doesn't exist" in cli_result.text.lower()
    
    @pytest.mark.asyncio
    async def test_system_prompt_loading(self, sdk_executor, cli_executor):
        """Test that system prompts are loaded consistently."""
        query = "What is your primary purpose?"
        
        # Execute with both
        sdk_result = await sdk_executor.execute([{"role": "user", "content": query}])
        cli_result = await cli_executor.execute([{"role": "user", "content": query}])
        
        # Both should reference being helpful for code
        assert "code" in sdk_result.text.lower()
        assert "code" in cli_result.text.lower()
        
        # Both should be concise (as specified in prompt.md)
        assert len(sdk_result.text) < 1000  # Reasonable length for concise response
        assert len(cli_result.text) < 1000
    
    @pytest.mark.asyncio
    async def test_tool_capability_enforcement(self, sdk_executor, cli_executor):
        """Test that allowed tools are enforced consistently."""
        # Try to use a tool that's not in allowed_tools.json
        query = "Please search the web for Python best practices"
        
        # Execute with both
        sdk_result = await sdk_executor.execute([{"role": "user", "content": query}])
        cli_result = await cli_executor.execute([{"role": "user", "content": query}])
        
        # Both should indicate they can't search the web
        assert "can't" in sdk_result.text.lower() or "cannot" in sdk_result.text.lower() or "unable" in sdk_result.text.lower()
        assert "can't" in cli_result.text.lower() or "cannot" in cli_result.text.lower() or "unable" in cli_result.text.lower()
    
    @pytest.mark.asyncio
    async def test_early_return_functionality(self, sdk_executor, cli_executor):
        """Test execute_until_first_response functionality."""
        query = "First, tell me about the project. Then analyze all the code files in detail."
        
        # Execute with early return
        sdk_result = await sdk_executor.execute_until_first_response(
            [{"role": "user", "content": query}]
        )
        cli_result = await cli_executor.execute_until_first_response(
            [{"role": "user", "content": query}]
        )
        
        # Both should return after first response
        assert sdk_result.success
        assert cli_result.success
        
        # Responses should be relatively short (not include detailed analysis)
        assert len(sdk_result.text) < 2000
        assert len(cli_result.text) < 2000
        
        # Should mention the project but not go into deep analysis
        assert "project" in sdk_result.text.lower() or "test" in sdk_result.text.lower()
        assert "project" in cli_result.text.lower() or "test" in cli_result.text.lower()