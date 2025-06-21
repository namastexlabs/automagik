"""Tests for Environment Manager Bridge functionality.

This module tests the CLIEnvironmentManager.as_dict() method and
the SDK environment injection capabilities.
"""

import pytest
import asyncio
import os
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from src.agents.claude_code.cli_environment import CLIEnvironmentManager
from src.agents.claude_code.sdk_transport import (
    EnvironmentAwareTransport, 
    SDKEnvironmentInjector
)


class TestCLIEnvironmentManagerAsDict:
    """Test the as_dict() method of CLIEnvironmentManager."""
    
    def test_as_dict_basic(self, tmp_path):
        """Test environment manager returns correct dict with basic values."""
        env_mgr = CLIEnvironmentManager(
            workspace_root=tmp_path,
            workflow_name="test-workflow",
            session_id="test-123"
        )
        
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        
        env_dict = env_mgr.as_dict(workspace)
        
        assert env_dict['CLAUDE_WORKSPACE'] == str(workspace)
        assert env_dict['CLAUDE_WORKFLOW'] == 'test-workflow'
        assert env_dict['CLAUDE_SESSION_ID'] == 'test-123'
        assert env_dict['CLAUDE_WORKSPACE_ROOT'] == str(tmp_path)
        assert env_dict['CLAUDE_TEMP_DIR'] == str(workspace / '.claude-temp')
    
    def test_as_dict_with_git_info(self, tmp_path):
        """Test environment dict includes git information when available."""
        # Create mock git info
        git_info = Mock()
        git_info.repo_path = "/path/to/repo"
        git_info.current_branch = "feature-branch"
        git_info.current_commit = "abc123def"
        
        env_mgr = CLIEnvironmentManager(
            workspace_root=tmp_path,
            git_info=git_info
        )
        
        env_dict = env_mgr.as_dict(tmp_path)
        
        assert env_dict['CLAUDE_GIT_REPO'] == "/path/to/repo"
        assert env_dict['CLAUDE_GIT_BRANCH'] == "feature-branch"
        assert env_dict['CLAUDE_GIT_COMMIT'] == "abc123def"
    
    def test_as_dict_with_auth_tokens(self, tmp_path):
        """Test environment dict includes auth tokens."""
        auth_tokens = {
            "github": "ghp_token123",
            "api": "api_key_456"
        }
        
        env_mgr = CLIEnvironmentManager(
            workspace_root=tmp_path,
            auth_tokens=auth_tokens
        )
        
        env_dict = env_mgr.as_dict(tmp_path)
        
        assert env_dict['CLAUDE_AUTH_GITHUB'] == "ghp_token123"
        assert env_dict['CLAUDE_AUTH_API'] == "api_key_456"
    
    def test_as_dict_with_mcp_endpoints(self, tmp_path):
        """Test environment dict includes MCP endpoints as JSON."""
        mcp_endpoints = {
            "server1": "http://localhost:8001",
            "server2": "http://localhost:8002"
        }
        
        env_mgr = CLIEnvironmentManager(
            workspace_root=tmp_path,
            mcp_endpoints=mcp_endpoints
        )
        
        env_dict = env_mgr.as_dict(tmp_path)
        
        assert 'CLAUDE_MCP_SERVERS' in env_dict
        parsed_mcp = json.loads(env_dict['CLAUDE_MCP_SERVERS'])
        assert parsed_mcp == mcp_endpoints
    
    def test_as_dict_with_feature_flags(self, tmp_path):
        """Test environment dict includes feature flags."""
        env_mgr = CLIEnvironmentManager(
            workspace_root=tmp_path,
            enable_citations=True,
            enable_artifacts=False
        )
        
        env_dict = env_mgr.as_dict(tmp_path)
        
        assert env_dict['CLAUDE_ENABLE_CITATIONS'] == 'true'
        assert env_dict['CLAUDE_ENABLE_ARTIFACTS'] == 'false'
    
    def test_as_dict_with_all_options(self, tmp_path):
        """Test environment dict with all options set."""
        git_info = Mock()
        git_info.repo_path = "/repo"
        git_info.current_branch = "main"
        git_info.current_commit = "commit123"
        
        env_mgr = CLIEnvironmentManager(
            workspace_root=tmp_path,
            session_id="session-456",
            workflow_name="epic-workflow",
            workflow_run_id="run-789",
            api_base_url="https://api.example.com",
            auth_tokens={"token": "secret"},
            mcp_endpoints={"mcp": "http://mcp.local"},
            enable_citations=True,
            enable_artifacts=True,
            git_info=git_info
        )
        
        workspace = tmp_path / "test-workspace"
        workspace.mkdir()
        
        env_dict = env_mgr.as_dict(workspace)
        
        # Verify all environment variables are present
        expected_keys = [
            'CLAUDE_WORKSPACE',
            'CLAUDE_SESSION_ID',
            'CLAUDE_GIT_REPO',
            'CLAUDE_GIT_BRANCH',
            'CLAUDE_GIT_COMMIT',
            'CLAUDE_WORKFLOW',
            'CLAUDE_WORKFLOW_RUN_ID',
            'CLAUDE_API_BASE',
            'CLAUDE_AUTH_TOKEN',
            'CLAUDE_MCP_SERVERS',
            'CLAUDE_ENABLE_CITATIONS',
            'CLAUDE_ENABLE_ARTIFACTS',
            'CLAUDE_WORKSPACE_ROOT',
            'CLAUDE_TEMP_DIR'
        ]
        
        for key in expected_keys:
            assert key in env_dict, f"Missing expected key: {key}"
    
    def test_as_dict_empty_values(self, tmp_path):
        """Test environment dict handles empty/None values correctly."""
        env_mgr = CLIEnvironmentManager(
            workspace_root=tmp_path,
            session_id=None,
            workflow_name=None
        )
        
        env_dict = env_mgr.as_dict(tmp_path)
        
        assert env_dict['CLAUDE_SESSION_ID'] == ''
        assert 'CLAUDE_WORKFLOW' not in env_dict  # Should not include if None


class TestEnvironmentAwareTransport:
    """Test the EnvironmentAwareTransport class."""
    
    def test_transport_init(self):
        """Test transport initialization."""
        custom_env = {"TEST_VAR": "test_value"}
        transport = EnvironmentAwareTransport(custom_env)
        
        assert transport.custom_env == custom_env
        assert transport.original_env == {}
    
    def test_inject_restore_environment(self):
        """Test environment injection and restoration."""
        # Store original value if TEST_VAR exists
        original_test_var = os.environ.get('TEST_VAR')
        
        try:
            # Set initial value
            os.environ['TEST_VAR'] = 'original'
            
            # Create transport with custom env
            transport = EnvironmentAwareTransport({"TEST_VAR": "injected"})
            
            # Inject environment
            transport.inject_environment()
            assert os.environ['TEST_VAR'] == 'injected'
            
            # Restore environment
            transport.restore_environment()
            assert os.environ['TEST_VAR'] == 'original'
            
        finally:
            # Clean up
            if original_test_var is None:
                os.environ.pop('TEST_VAR', None)
            else:
                os.environ['TEST_VAR'] = original_test_var
    
    def test_inject_new_variable(self):
        """Test injecting a new environment variable."""
        # Ensure variable doesn't exist
        unique_var = 'CLAUDE_TEST_UNIQUE_VAR_12345'
        os.environ.pop(unique_var, None)
        
        try:
            transport = EnvironmentAwareTransport({unique_var: "new_value"})
            
            # Inject
            transport.inject_environment()
            assert os.environ[unique_var] == "new_value"
            
            # Restore
            transport.restore_environment()
            assert unique_var not in os.environ
            
        finally:
            # Clean up just in case
            os.environ.pop(unique_var, None)
    
    def test_context_manager(self):
        """Test transport as context manager."""
        original_value = os.environ.get('CLAUDE_TEST_CTX')
        
        try:
            os.environ['CLAUDE_TEST_CTX'] = 'original'
            
            transport = EnvironmentAwareTransport({"CLAUDE_TEST_CTX": "context"})
            
            # Outside context
            assert os.environ['CLAUDE_TEST_CTX'] == 'original'
            
            # Inside context
            with transport:
                assert os.environ['CLAUDE_TEST_CTX'] == 'context'
            
            # After context
            assert os.environ['CLAUDE_TEST_CTX'] == 'original'
            
        finally:
            if original_value is None:
                os.environ.pop('CLAUDE_TEST_CTX', None)
            else:
                os.environ['CLAUDE_TEST_CTX'] = original_value
    
    @pytest.mark.asyncio
    async def test_spawn_process(self):
        """Test spawning process with custom environment."""
        transport = EnvironmentAwareTransport({"CLAUDE_TEST_SPAWN": "spawned"})
        
        # Create a simple test script
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("""
import os
print(f"CLAUDE_TEST_SPAWN={os.environ.get('CLAUDE_TEST_SPAWN', 'NOT_SET')}")
""")
            script_path = f.name
        
        try:
            # Spawn process
            process = await transport.spawn_process(
                ['python', script_path]
            )
            
            stdout, stderr = await process.communicate()
            output = stdout.decode().strip()
            
            assert "CLAUDE_TEST_SPAWN=spawned" in output
            
        finally:
            os.unlink(script_path)


class TestSDKEnvironmentInjector:
    """Test the SDKEnvironmentInjector helper class."""
    
    def test_create_transport(self, tmp_path):
        """Test creating transport from environment manager."""
        env_mgr = CLIEnvironmentManager(
            workspace_root=tmp_path,
            workflow_name="test-workflow"
        )
        
        injector = SDKEnvironmentInjector(env_mgr)
        transport = injector.create_transport(tmp_path)
        
        assert isinstance(transport, EnvironmentAwareTransport)
        assert 'CLAUDE_WORKFLOW' in transport.custom_env
        assert transport.custom_env['CLAUDE_WORKFLOW'] == 'test-workflow'
    
    @pytest.mark.asyncio
    async def test_execute_with_env(self, tmp_path):
        """Test executing function with environment injection."""
        env_mgr = CLIEnvironmentManager(
            workspace_root=tmp_path,
            workflow_name="async-test"
        )
        
        injector = SDKEnvironmentInjector(env_mgr)
        
        # Mock async function that checks environment
        async def test_function():
            return os.environ.get('CLAUDE_WORKFLOW')
        
        # Store original
        original = os.environ.get('CLAUDE_WORKFLOW')
        
        try:
            # Execute with environment
            result = await injector.execute_with_env(
                tmp_path,
                test_function
            )
            
            assert result == 'async-test'
            
            # Verify environment was restored
            assert os.environ.get('CLAUDE_WORKFLOW') == original
            
        finally:
            if original is None:
                os.environ.pop('CLAUDE_WORKFLOW', None)
            else:
                os.environ['CLAUDE_WORKFLOW'] = original


@pytest.mark.asyncio
async def test_env_injection_integration(tmp_path):
    """Integration test: environment variables are injected into subprocess."""
    # Create test script that prints env var
    test_script = tmp_path / "test_env.py"
    test_script.write_text("""
import os
print(f"CLAUDE_WORKFLOW={os.environ.get('CLAUDE_WORKFLOW', 'NOT_SET')}")
print(f"CLAUDE_SESSION_ID={os.environ.get('CLAUDE_SESSION_ID', 'NOT_SET')}")
""")
    
    # Create environment manager
    env_mgr = CLIEnvironmentManager(
        workspace_root=tmp_path,
        workflow_name="integration-test",
        session_id="session-integration"
    )
    
    # Get environment dict
    env_dict = env_mgr.as_dict(tmp_path)
    
    # Create transport and spawn process
    transport = EnvironmentAwareTransport(env_dict)
    
    process = await transport.spawn_process(
        ['python', str(test_script)],
        cwd=str(tmp_path)
    )
    
    stdout, stderr = await process.communicate()
    output = stdout.decode()
    
    assert "CLAUDE_WORKFLOW=integration-test" in output
    assert "CLAUDE_SESSION_ID=session-integration" in output


def test_environment_persistence():
    """Test that environment changes don't persist between transports."""
    var_name = 'CLAUDE_TEST_PERSIST'
    original = os.environ.get(var_name)
    
    try:
        # First transport
        transport1 = EnvironmentAwareTransport({var_name: "value1"})
        with transport1:
            assert os.environ[var_name] == "value1"
        
        # After first transport
        assert os.environ.get(var_name) == original
        
        # Second transport
        transport2 = EnvironmentAwareTransport({var_name: "value2"})
        with transport2:
            assert os.environ[var_name] == "value2"
        
        # After second transport
        assert os.environ.get(var_name) == original
        
    finally:
        if original is None:
            os.environ.pop(var_name, None)
        else:
            os.environ[var_name] = original


def test_multiple_environment_variables():
    """Test injecting multiple environment variables at once."""
    vars_to_test = {
        'CLAUDE_TEST_VAR1': 'value1',
        'CLAUDE_TEST_VAR2': 'value2',
        'CLAUDE_TEST_VAR3': 'value3'
    }
    
    # Store originals
    originals = {k: os.environ.get(k) for k in vars_to_test}
    
    try:
        transport = EnvironmentAwareTransport(vars_to_test)
        
        # Inject all
        transport.inject_environment()
        
        # Verify all injected
        for key, value in vars_to_test.items():
            assert os.environ[key] == value
        
        # Restore all
        transport.restore_environment()
        
        # Verify all restored
        for key, original in originals.items():
            if original is None:
                assert key not in os.environ
            else:
                assert os.environ[key] == original
                
    finally:
        # Clean up
        for key, original in originals.items():
            if original is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original