"""Regression test for MCPServerStdio constructor parameter issue.

This test ensures that MCPServerStdio constructor calls correctly split
command arrays into command and args parameters, preventing the issue:
"MCPServerStdio.__init__() missing 1 required positional argument: 'command'"
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from pydantic_ai.mcp import MCPServerStdio

from src.mcp.client import MCPManager
from src.mcp.exceptions import MCPError


class TestMCPConstructorRegression:
    """Test MCPServerStdio constructor parameter handling."""

    @pytest.fixture
    def mock_mcp_config(self):
        """Create a mock MCP config for testing."""
        config = Mock()
        config.name = "test-server"
        config.get_server_type.return_value = "stdio"
        config.config = {
            "command": ["python", "-m", "test_module"],
            "environment": {"TEST_VAR": "test_value"},
            "timeout": 30000
        }
        return config

    @pytest.fixture
    def mcp_manager(self):
        """Create MCPManager instance for testing."""
        return MCPManager()

    @patch('src.mcp.client.MCPServerStdio')
    async def test_mcp_server_stdio_constructor_parameters(self, mock_stdio_class, mcp_manager, mock_mcp_config):
        """Test that MCPServerStdio is called with correct command and args parameters."""
        # Setup
        mock_server_instance = AsyncMock()
        mock_stdio_class.return_value = mock_server_instance
        
        # Execute
        await mcp_manager._create_and_start_server(mock_mcp_config)
        
        # Verify MCPServerStdio was called with correct parameters
        mock_stdio_class.assert_called_once()
        call_args = mock_stdio_class.call_args
        
        # Check positional arguments
        assert call_args.kwargs['command'] == "python"  # First element as string
        assert call_args.kwargs['args'] == ["-m", "test_module"]  # Rest as list
        assert call_args.kwargs['env'] == {"TEST_VAR": "test_value"}
        assert call_args.kwargs['timeout'] == 30.0  # Converted from ms to seconds
        
        # Verify server was stored (not started - PydanticAI servers are context managers)
        # Note: PydanticAI MCP servers don't have persistent start/stop - they're context managers

    @patch('src.mcp.client.MCPServerStdio')
    async def test_mcp_server_single_command_no_args(self, mock_stdio_class, mcp_manager, mock_mcp_config):
        """Test command array with single element (no arguments)."""
        # Setup - single command, no arguments
        mock_mcp_config.config["command"] = ["python"]
        mock_server_instance = AsyncMock()
        mock_stdio_class.return_value = mock_server_instance
        
        # Execute
        await mcp_manager._create_and_start_server(mock_mcp_config)
        
        # Verify
        call_args = mock_stdio_class.call_args
        assert call_args.kwargs['command'] == "python"
        assert call_args.kwargs['args'] == []  # Empty args list

    async def test_mcp_server_empty_command_raises_error(self, mcp_manager, mock_mcp_config):
        """Test that empty command array raises appropriate error."""
        # Setup - empty command
        mock_mcp_config.config["command"] = []
        
        # Execute and verify error
        with pytest.raises(MCPError, match="'command' is required for stdio servers"):
            await mcp_manager._create_and_start_server(mock_mcp_config)

    async def test_mcp_server_missing_command_raises_error(self, mcp_manager, mock_mcp_config):
        """Test that missing command key raises appropriate error."""
        # Setup - no command key
        del mock_mcp_config.config["command"]
        
        # Execute and verify error
        with pytest.raises(MCPError, match="'command' is required for stdio servers"):
            await mcp_manager._create_and_start_server(mock_mcp_config)

    @patch('src.mcp.client.MCPServerStdio')
    async def test_mcp_server_complex_command_args(self, mock_stdio_class, mcp_manager, mock_mcp_config):
        """Test complex command with multiple arguments."""
        # Setup - complex command with multiple args
        mock_mcp_config.config["command"] = ["python", "-m", "uvicorn", "app:main", "--host", "0.0.0.0", "--port", "8000"]
        mock_server_instance = AsyncMock()
        mock_stdio_class.return_value = mock_server_instance
        
        # Execute
        await mcp_manager._create_and_start_server(mock_mcp_config)
        
        # Verify correct splitting
        call_args = mock_stdio_class.call_args
        assert call_args.kwargs['command'] == "python"
        assert call_args.kwargs['args'] == ["-m", "uvicorn", "app:main", "--host", "0.0.0.0", "--port", "8000"]

    def test_constructor_signature_compliance(self):
        """Test that our understanding of MCPServerStdio constructor is correct."""
        import inspect
        from pydantic_ai.mcp import MCPServerStdio
        
        # Get constructor signature
        sig = inspect.signature(MCPServerStdio.__init__)
        params = list(sig.parameters.keys())
        
        # Verify expected parameters exist
        assert 'command' in params, "MCPServerStdio should have 'command' parameter"
        assert 'args' in params, "MCPServerStdio should have 'args' parameter"
        
        # Verify command is required (no default value)
        command_param = sig.parameters['command']
        assert command_param.default == inspect.Parameter.empty, "'command' parameter should be required"