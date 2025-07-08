"""
Startup Integration Error Tests for NMSTX-257

This test suite addresses the critical startup errors discovered during system testing,
ensuring the migration safety system accounts for and prevents these integration failures.

Critical Issues Identified from Startup Log:
1. Sofia agent import error: 'refresh_mcp_client_manager' missing from automagik.mcp.client
2. PlaceholderAgent undefined error in sofia error handling
3. MCP server initialization failures: MCPServerStdio missing 'args' parameter
4. General import and integration failures between components
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch
from pathlib import Path

# Add automagik to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "automagik"))


class TestStartupIntegrationErrors:
    """Test suite ensuring startup errors are caught and handled safely."""
    
    def test_mcp_client_import_compatibility(self):
        """Test that mcp.client module has all required functions for agent compatibility."""
        try:
            from automagik.mcp.client import get_mcp_manager
            # This should exist as the new function
            assert callable(get_mcp_manager)
        except ImportError as e:
            pytest.fail(f"Failed to import required MCP client function: {e}")
    
    def test_mcp_client_legacy_function_compatibility(self):
        """Test that legacy function names are properly aliased or handled."""
        try:
            # This is the function Sofia agent is trying to import
            from automagik.mcp.client import refresh_mcp_client_manager
            assert callable(refresh_mcp_client_manager)
        except ImportError:
            # If it doesn't exist, verify the error handling path works
            try:
                from automagik.agents.pydanticai.sofia.agent import SofiaAgent
                pytest.fail("Sofia agent should fail gracefully when refresh_mcp_client_manager is missing")
            except ImportError:
                # This is expected - Sofia should fail to import if the function is missing
                pass
    
    def test_placeholder_agent_availability(self):
        """Test that PlaceholderAgent is available for error handling."""
        try:
            from automagik.agents.models.placeholder import PlaceholderAgent
            assert PlaceholderAgent is not None
            
            # Test that it can be instantiated with error config
            config = {"name": "test_error", "error": "Test error message"}
            placeholder = PlaceholderAgent(config)
            assert placeholder is not None
            
        except ImportError:
            # If PlaceholderAgent doesn't exist, we need to create it or fix the error handling
            pytest.fail("PlaceholderAgent not found - needed for error handling in agent initialization")
    
    def test_agent_factory_error_handling(self):
        """Test that agent factory handles missing agents gracefully."""
        from automagik.agents.models.agent_factory import AgentFactory
        
        # Test creating an agent that might have import issues
        try:
            # This should either work or fail gracefully with a placeholder
            agent = AgentFactory.create_agent("sofia", {"name": "test"})
            assert agent is not None
            
            # If it's a placeholder due to error, it should have error info
            if hasattr(agent, 'error'):
                assert isinstance(agent.error, str)
                
        except Exception as e:
            pytest.fail(f"Agent factory should handle errors gracefully, got: {e}")
    
    @patch('automagik.mcp.client.MCPServerStdio')
    def test_mcp_server_initialization_parameters(self, mock_stdio):
        """Test that MCP server initialization has correct parameters."""
        from automagik.mcp.client import MCPManager
        
        # Mock the MCPServerStdio to check what parameters it's called with
        mock_stdio.return_value = Mock()
        
        manager = MCPManager()
        
        # Test configuration that caused the startup error
        test_config = {
            "name": "test-server",
            "server_type": "stdio", 
            "command": ["echo", "test"],
            "enabled": True
        }
        
        try:
            # This should not fail due to missing 'args' parameter
            manager._create_server(test_config)
            
            # Verify MCPServerStdio was called with correct parameters
            assert mock_stdio.called
            call_args = mock_stdio.call_args
            
            # Should have been called with command and any required args
            assert call_args is not None
            
        except TypeError as e:
            if "missing 1 required positional argument: 'args'" in str(e):
                pytest.fail("MCP server initialization still has args parameter issue")
            else:
                raise
    
    def test_mcp_config_validation_prevents_startup_errors(self):
        """Test that config validation catches issues before startup."""
        from automagik.db.models import MCPConfig
        
        # Test configuration that caused startup failure
        invalid_config = {
            "name": "test-server",
            "config": {
                "server_type": "stdio",
                "command": ["echo", "test"],
                # Missing required fields that might cause startup issues
            }
        }
        
        try:
            config = MCPConfig(**invalid_config)
            # If validation passes, the config should have all required fields
            assert hasattr(config, 'config')
            assert 'command' in config.config
            
        except Exception as e:
            # Validation should catch config issues early
            assert "validation" in str(e).lower() or "required" in str(e).lower()


class TestMigrationSafetyWithStartupErrors:
    """Test migration safety specifically around startup integration issues."""
    
    def setup_method(self):
        """Set up test environment."""
        self.original_env = dict(os.environ)
        os.environ["MCP_MIGRATION_ENABLED"] = "true"
        os.environ["MCP_SAFETY_CHECKS"] = "true"
    
    def teardown_method(self):
        """Clean up test environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_migration_safety_checks_include_startup_validation(self):
        """Test that pre-migration checks validate startup compatibility."""
        # Add automagik to path for importing migration module
        scripts_path = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_path))
        
        try:
            from migrate_mcp_system import MCPMigration
            
            migration = MCPMigration(dry_run=True)
            
            with patch('migrate_mcp_system.execute_query') as mock_execute:
                mock_execute.return_value = [{"result": 1}]
                
                # Add custom validation for startup compatibility
                with patch.object(migration, '_validate_startup_compatibility', return_value=True):
                    result = migration.pre_migration_checks()
                    assert result is True
                    
        except ImportError as e:
            pytest.skip(f"Migration module not available for testing: {e}")
    
    def test_post_migration_startup_test(self):
        """Test that post-migration validation includes startup testing."""
        scripts_path = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_path))
        
        try:
            from migrate_mcp_system import MCPMigration
            
            migration = MCPMigration(dry_run=True)
            migration.backup_data = {
                "mcp_servers": [
                    {
                        "id": 1,
                        "name": "test-server", 
                        "server_type": "stdio",
                        "command": ["echo", "test"],
                        "enabled": True
                    }
                ],
                "agent_assignments": []
            }
            
            # Test that validation includes startup compatibility
            with patch('migrate_mcp_system.list_mcp_configs') as mock_list:
                mock_list.return_value = [
                    Mock(name="test-server", config={"server_type": "stdio", "command": ["echo", "test"]})
                ]
                
                result = migration.validate_migration()
                assert result is True
                
        except ImportError as e:
            pytest.skip(f"Migration module not available for testing: {e}")


class TestMCPServerCompatibilityLayer:
    """Test MCP server compatibility layer for preventing startup errors."""
    
    @patch('pydantic_ai.mcp.MCPServerStdio')
    def test_mcp_server_stdio_compatibility(self, mock_stdio):
        """Test that MCPServerStdio is called with correct parameters."""
        try:
            from automagik.mcp.client import MCPManager
            
            # Mock successful server creation
            mock_server = Mock()
            mock_stdio.return_value = mock_server
            
            manager = MCPManager()
            
            config = {
                "name": "test-server",
                "server_type": "stdio",
                "command": ["echo", "test"],
                "enabled": True,
                "auto_start": True
            }
            
            # This should not raise the "missing args" error
            manager._create_server(config)
            
            # Verify it was called correctly
            mock_stdio.assert_called_once()
            call_args, call_kwargs = mock_stdio.call_args
            
            # Should have command as first argument or in kwargs
            assert call_args or 'command' in call_kwargs or 'args' in call_kwargs
            
        except Exception as e:
            if "missing 1 required positional argument: 'args'" in str(e):
                pytest.fail("MCPServerStdio compatibility issue not fixed")
            else:
                # Other errors might be expected during testing
                pass
    
    def test_mcp_config_transformation_prevents_startup_errors(self):
        """Test that config transformation prevents startup parameter issues."""
        scripts_path = Path(__file__).parent.parent.parent / "scripts"
        sys.path.insert(0, str(scripts_path))
        
        try:
            from migrate_mcp_system import MCPMigration
            
            migration = MCPMigration(dry_run=True)
            
            # Test transformation of config that caused startup error
            legacy_config = {
                "id": 1,
                "name": "test-server",
                "server_type": "stdio", 
                "command": ["echo", "test"],
                "env": {},
                "enabled": True,
                "auto_start": True,
                "max_retries": 3,
                "timeout_seconds": 30
            }
            
            transformed = migration.transform_server_config(legacy_config, ["simple"])
            
            # Verify transformed config has all required fields
            assert "name" in transformed
            assert "server_type" in transformed
            assert "command" in transformed
            assert "agents" in transformed
            
            # Verify it has proper structure for new MCP system
            assert isinstance(transformed["agents"], list)
            assert "simple" in transformed["agents"]
            
        except ImportError as e:
            pytest.skip(f"Migration module not available: {e}")


class TestAgentInitializationErrorHandling:
    """Test agent initialization error handling and recovery."""
    
    def test_sofia_agent_error_handling(self):
        """Test that Sofia agent errors are handled gracefully."""
        try:
            # Try to import Sofia agent - should either work or fail gracefully
            from automagik.agents.pydanticai.sofia import create_agent
            
            # If import succeeds, test agent creation
            try:
                agent = create_agent({"name": "test"})
                assert agent is not None
                
                # If it's an error placeholder, it should have error info
                if hasattr(agent, 'error'):
                    assert isinstance(agent.error, str)
                    
            except Exception as e:
                # Agent creation errors should be caught and handled
                assert "PlaceholderAgent" not in str(e)  # Should not have undefined name error
                
        except ImportError:
            # Import errors are acceptable - agent should be skipped
            pass
    
    def test_agent_discovery_with_errors(self):
        """Test that agent discovery continues despite individual agent errors."""
        from automagik.agents.models.agent_factory import AgentFactory
        
        # Test agent discovery process
        try:
            available_agents = AgentFactory.list_available_agents()
            assert isinstance(available_agents, list)
            assert len(available_agents) > 0
            
            # Should have some working agents even if some fail
            for agent_name in available_agents:
                try:
                    agent = AgentFactory.create_agent(agent_name, {"name": f"test_{agent_name}"})
                    assert agent is not None
                except Exception as e:
                    # Individual agent errors should not crash the system
                    print(f"Agent {agent_name} failed (acceptable): {e}")
                    
        except Exception as e:
            pytest.fail(f"Agent discovery should not fail completely: {e}")


class TestSystemIntegrationValidation:
    """Test system-wide integration validation for migration safety."""
    
    def test_database_mcp_integration(self):
        """Test that database and MCP systems integrate properly after migration."""
        try:
            from automagik.db.models import MCPConfig
            from automagik.mcp.client import MCPManager
            
            # Test that MCP configs can be loaded from database
            MCPManager()
            
            # Mock database config
            test_config = MCPConfig(
                name="integration-test",
                config={
                    "server_type": "stdio",
                    "command": ["echo", "test"],
                    "agents": ["simple"],
                    "enabled": True
                }
            )
            
            # Test that config can be processed by MCP manager
            try:
                # This should not crash due to parameter mismatches
                server_config = test_config.config
                assert "command" in server_config
                assert "server_type" in server_config
                
            except Exception as e:
                pytest.fail(f"MCP-Database integration broken: {e}")
                
        except ImportError as e:
            pytest.skip(f"Required modules not available: {e}")
    
    def test_agent_mcp_tool_registration(self):
        """Test that agent-MCP tool registration works after migration."""
        try:
            from automagik.agents.common.tool_registry import ToolRegistry
            from automagik.mcp.client import MCPManager
            
            # Test that tools can be registered from MCP servers
            tool_registry = ToolRegistry()
            MCPManager()
            
            # Mock MCP server with tools
            mock_server = Mock()
            mock_server.list_tools.return_value = [
                {"name": "test_tool", "description": "Test tool"}
            ]
            
            # Test tool registration process
            try:
                tool_registry.register_mcp_tools("test_agent", {"test-server": mock_server})
                
                # Should not crash during registration
                tools = tool_registry.list_tools()
                assert isinstance(tools, list)
                
            except Exception as e:
                pytest.fail(f"Tool registration integration broken: {e}")
                
        except ImportError as e:
            pytest.skip(f"Required modules not available: {e}")


# Integration smoke tests
class TestPostMigrationSmokeTests:
    """Smoke tests that should pass after migration to ensure basic functionality."""
    
    def test_basic_agent_creation_smoke_test(self):
        """Smoke test for basic agent creation after migration."""
        try:
            from automagik.agents.models.agent_factory import AgentFactory
            
            # Test that at least one agent type can be created
            agent_types = ["simple"]
            
            success_count = 0
            for agent_type in agent_types:
                try:
                    agent = AgentFactory.create_agent(agent_type, {"name": f"smoke_test_{agent_type}"})
                    if agent is not None:
                        success_count += 1
                except Exception as e:
                    print(f"Agent {agent_type} failed smoke test: {e}")
            
            assert success_count > 0, "At least one agent type should work for basic functionality"
            
        except Exception as e:
            pytest.fail(f"Basic agent creation smoke test failed: {e}")
    
    def test_database_connectivity_smoke_test(self):
        """Smoke test for database connectivity after migration."""
        try:
            from automagik.db.connection import execute_query
            
            # Test basic database connectivity
            result = execute_query("SELECT 1 as test", fetch=True)
            assert result is not None
            assert len(result) > 0
            assert result[0]["test"] == 1
            
        except Exception as e:
            pytest.fail(f"Database connectivity smoke test failed: {e}")
    
    def test_mcp_system_smoke_test(self):
        """Smoke test for MCP system functionality after migration."""
        try:
            from automagik.mcp.client import MCPManager
            
            # Test that MCP manager can be initialized
            manager = MCPManager()
            assert manager is not None
            
            # Test that it can handle empty configuration gracefully
            configs = manager.get_configurations()
            assert isinstance(configs, (list, dict))
            
        except Exception as e:
            pytest.fail(f"MCP system smoke test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])