"""
Comprehensive Test Suite for NMSTX-257 Migration Safety System

This test suite validates the production safety features implemented for 
MCP system migration including feature flags, monitoring, and safety triggers.
"""

import pytest
import os
import time
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

# Add the scripts directory to the path for importing the migration module
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))

from migrate_mcp_system import (
    FeatureFlags, 
    MigrationMonitor, 
    SafetyThresholdExceeded,
    MCPMigration
)


class TestFeatureFlags:
    """Test suite for FeatureFlags class ensuring proper configuration management."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        # Save original environment
        self.original_env = dict(os.environ)
        
        # Clear test-related environment variables
        test_vars = [
            "MCP_USE_NEW_SYSTEM", "MCP_MIGRATION_ENABLED", 
            "MCP_SAFETY_CHECKS", "MCP_AUTO_ROLLBACK", "MCP_MONITORING_ENABLED"
        ]
        for var in test_vars:
            os.environ.pop(var, None)
    
    def teardown_method(self):
        """Restore original environment after each test."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_default_flag_values(self):
        """Test that feature flags have correct default values."""
        flags = FeatureFlags()
        
        assert flags.is_enabled("MCP_USE_NEW_SYSTEM") is False
        assert flags.is_enabled("MCP_MIGRATION_ENABLED") is False
        assert flags.is_enabled("MCP_SAFETY_CHECKS") is True  # Default enabled for safety
        assert flags.is_enabled("MCP_AUTO_ROLLBACK") is True  # Default enabled for safety
        assert flags.is_enabled("MCP_MONITORING_ENABLED") is True  # Default enabled for safety
    
    def test_environment_variable_parsing(self):
        """Test various environment variable formats are parsed correctly."""
        test_cases = [
            ("true", True), ("TRUE", True), ("True", True),
            ("false", False), ("FALSE", False), ("False", False),
            ("1", True), ("0", False),
            ("yes", True), ("no", False),
            ("on", True), ("off", False),
            ("invalid", False)  # Invalid values default to False
        ]
        
        for env_value, expected in test_cases:
            os.environ["MCP_USE_NEW_SYSTEM"] = env_value
            flags = FeatureFlags()
            assert flags.is_enabled("MCP_USE_NEW_SYSTEM") == expected, f"Failed for {env_value}"
    
    def test_flag_enable_disable(self):
        """Test runtime flag enable/disable functionality."""
        flags = FeatureFlags()
        
        # Test enabling
        flags.enable("MCP_MIGRATION_ENABLED")
        assert flags.is_enabled("MCP_MIGRATION_ENABLED") is True
        assert os.environ["MCP_MIGRATION_ENABLED"] == "true"
        
        # Test disabling
        flags.disable("MCP_MIGRATION_ENABLED")
        assert flags.is_enabled("MCP_MIGRATION_ENABLED") is False
        assert os.environ["MCP_MIGRATION_ENABLED"] == "false"
    
    def test_nonexistent_flag(self):
        """Test handling of nonexistent flags."""
        flags = FeatureFlags()
        assert flags.is_enabled("NONEXISTENT_FLAG") is False
    
    def test_production_safety_flags(self):
        """Test that safety-critical flags default to safe values."""
        flags = FeatureFlags()
        
        # These should default to True for production safety
        safety_flags = ["MCP_SAFETY_CHECKS", "MCP_AUTO_ROLLBACK", "MCP_MONITORING_ENABLED"]
        for flag in safety_flags:
            assert flags.is_enabled(flag) is True, f"{flag} should default to True for safety"


class TestMigrationMonitor:
    """Test suite for MigrationMonitor class ensuring proper monitoring and safety."""
    
    def setup_method(self):
        """Set up fresh monitor for each test."""
        self.monitor = MigrationMonitor()
    
    def test_monitor_initialization(self):
        """Test monitor initializes with correct default values."""
        assert self.monitor.start_time is None
        assert self.monitor.errors == []
        assert self.monitor.warnings == []
        assert self.monitor.performance_metrics == {}
        
        # Test safety thresholds
        expected_thresholds = {
            "max_errors": 5,
            "max_duration_minutes": 30,
            "min_success_rate": 0.8,
            "max_response_time_ms": 5000,
        }
        assert self.monitor.safety_thresholds == expected_thresholds
    
    def test_start_monitoring(self):
        """Test monitoring start sets timestamp correctly."""
        start_time_before = time.time()
        self.monitor.start_monitoring()
        start_time_after = time.time()
        
        assert start_time_before <= self.monitor.start_time <= start_time_after
    
    def test_error_recording(self):
        """Test error recording and threshold checking."""
        # Record an error
        self.monitor.record_error("Test error", "test_context")
        
        assert len(self.monitor.errors) == 1
        error = self.monitor.errors[0]
        assert error["error"] == "Test error"
        assert error["context"] == "test_context"
        assert "timestamp" in error
        
        # Verify timestamp format
        datetime.fromisoformat(error["timestamp"])  # Should not raise
    
    def test_error_threshold_exceeded(self):
        """Test that error threshold triggers safety exception."""
        # Record errors up to threshold
        for i in range(4):
            self.monitor.record_error(f"Error {i}", "test")
        
        # Fifth error should trigger threshold
        with pytest.raises(SafetyThresholdExceeded, match="Too many errors: 5"):
            self.monitor.record_error("Final error", "test")
    
    def test_warning_recording(self):
        """Test warning recording functionality."""
        self.monitor.record_warning("Test warning", "test_context")
        
        assert len(self.monitor.warnings) == 1
        warning = self.monitor.warnings[0]
        assert warning["warning"] == "Test warning"
        assert warning["context"] == "test_context"
        assert "timestamp" in warning
    
    def test_duration_threshold_check(self):
        """Test duration threshold checking."""
        # Start monitoring and simulate time passing
        self.monitor.start_monitoring()
        
        # Simulate exceeding time limit
        self.monitor.start_time = time.time() - (31 * 60)  # 31 minutes ago
        
        with pytest.raises(SafetyThresholdExceeded, match="Migration exceeded time limit"):
            self.monitor.check_duration_threshold()
    
    def test_duration_threshold_not_started(self):
        """Test duration check when monitoring not started."""
        # Should not raise exception if monitoring not started
        self.monitor.check_duration_threshold()
    
    @patch('migrate_mcp_system.execute_query')
    def test_response_time_measurement(self, mock_execute):
        """Test response time measurement and threshold checking."""
        # Mock successful database query
        mock_execute.return_value = [{"result": 1}]
        
        response_time = self.monitor.test_response_time()
        
        assert isinstance(response_time, float)
        assert response_time >= 0
        mock_execute.assert_called_once_with("SELECT 1", fetch=True)
    
    @patch('migrate_mcp_system.execute_query')
    def test_response_time_failure(self, mock_execute):
        """Test response time measurement when database fails."""
        mock_execute.side_effect = Exception("Database error")
        
        response_time = self.monitor.test_response_time()
        
        assert response_time == float('inf')
        assert len(self.monitor.errors) == 1
        assert "Response time test failed" in self.monitor.errors[0]["error"]
    
    @patch('migrate_mcp_system.execute_query')
    def test_response_time_warning_threshold(self, mock_execute):
        """Test response time warning when threshold exceeded."""
        mock_execute.return_value = [{"result": 1}]
        
        # Simulate slow response by patching time
        with patch('time.time', side_effect=[0, 6]):  # 6 second response
            response_time = self.monitor.test_response_time()
        
        assert response_time == 6000  # 6 seconds in ms
        assert len(self.monitor.warnings) == 1
        assert "High response time" in self.monitor.warnings[0]["warning"]
    
    def test_monitoring_summary(self):
        """Test monitoring summary generation."""
        self.monitor.start_monitoring()
        self.monitor.record_error("Test error", "context")
        self.monitor.record_warning("Test warning", "context")
        self.monitor.performance_metrics = {"server1": 100.0, "server2": 200.0}
        
        summary = self.monitor.get_summary()
        
        assert "duration_minutes" in summary
        assert summary["total_errors"] == 1
        assert summary["total_warnings"] == 1
        assert len(summary["errors"]) == 1
        assert len(summary["warnings"]) == 1
        assert summary["performance_metrics"] == {"server1": 100.0, "server2": 200.0}


class TestSafetyThresholdExceeded:
    """Test suite for SafetyThresholdExceeded exception."""
    
    def test_exception_creation(self):
        """Test exception can be created and has correct message."""
        message = "Test safety threshold exceeded"
        exception = SafetyThresholdExceeded(message)
        
        assert str(exception) == message
        assert isinstance(exception, Exception)


class TestMCPMigrationSafetyFeatures:
    """Test suite for MCPMigration safety features and integration."""
    
    def setup_method(self):
        """Set up clean environment for each test."""
        self.original_env = dict(os.environ)
        # Enable migration for testing
        os.environ["MCP_MIGRATION_ENABLED"] = "true"
    
    def teardown_method(self):
        """Restore original environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_migration_initialization(self):
        """Test MCPMigration initializes with correct safety components."""
        migration = MCPMigration(dry_run=True)
        
        assert isinstance(migration.feature_flags, FeatureFlags)
        assert isinstance(migration.monitor, MigrationMonitor)
        assert migration.dry_run is True
        assert migration.backup_data == {}
        assert migration.auto_rollback_enabled == migration.feature_flags.is_enabled("MCP_AUTO_ROLLBACK")
    
    @patch('migrate_mcp_system.execute_query')
    def test_pre_migration_safety_checks_pass(self, mock_execute):
        """Test pre-migration safety checks pass with valid setup."""
        mock_execute.return_value = [{"result": 1}]
        migration = MCPMigration(dry_run=True)
        
        result = migration.pre_migration_checks()
        
        assert result is True
        # Should test database connectivity and table existence
        assert mock_execute.call_count >= 2
    
    @patch('migrate_mcp_system.execute_query')
    def test_pre_migration_checks_fail_missing_table(self, mock_execute):
        """Test pre-migration checks fail when mcp_configs table missing."""
        # First call succeeds (connectivity), second fails (table check)
        mock_execute.side_effect = [
            [{"result": 1}],  # Connectivity test passes
            Exception("Table not found")  # Table check fails
        ]
        
        migration = MCPMigration(dry_run=True)
        result = migration.pre_migration_checks()
        
        assert result is False
        assert len(migration.monitor.errors) == 1
        assert "mcp_configs table not found" in migration.monitor.errors[0]["error"]
    
    def test_pre_migration_checks_disabled_by_flag(self):
        """Test migration fails when disabled by feature flag."""
        os.environ["MCP_MIGRATION_ENABLED"] = "false"
        
        migration = MCPMigration(dry_run=True)
        result = migration.pre_migration_checks()
        
        assert result is False
    
    @patch('migrate_mcp_system.execute_query')
    def test_safety_checks_can_be_disabled(self, mock_execute):
        """Test that safety checks can be disabled for emergency situations."""
        os.environ["MCP_SAFETY_CHECKS"] = "false"
        mock_execute.return_value = [{"result": 1}]
        
        migration = MCPMigration(dry_run=True)
        migration.backup_data = {"mcp_servers": [], "agent_assignments": []}
        
        # Should skip pre-migration checks when disabled
        with patch.object(migration, 'pre_migration_checks') as mock_pre_check:
            migration.migrate_to_new_schema()
            mock_pre_check.assert_not_called()
    
    def test_auto_rollback_feature(self):
        """Test automatic rollback when safety threshold exceeded."""
        os.environ["MCP_AUTO_ROLLBACK"] = "true"
        
        migration = MCPMigration(dry_run=False)
        migration.backup_data = {"mcp_servers": [], "agent_assignments": []}
        
        # Mock execute_query to trigger safety threshold
        with patch('migrate_mcp_system.execute_query') as mock_execute:
            # Simulate safety threshold exceeded
            with patch.object(migration.monitor, 'check_duration_threshold', 
                             side_effect=SafetyThresholdExceeded("Test threshold")):
                
                result = migration.migrate_to_new_schema()
                
                assert result is False
                # Should have called DELETE to rollback
                mock_execute.assert_called_with("DELETE FROM mcp_configs", fetch=False)
    
    def test_auto_rollback_disabled(self):
        """Test that auto-rollback can be disabled."""
        os.environ["MCP_AUTO_ROLLBACK"] = "false"
        
        migration = MCPMigration(dry_run=False)
        migration.backup_data = {"mcp_servers": [], "agent_assignments": []}
        
        with patch('migrate_mcp_system.execute_query') as mock_execute:
            with patch.object(migration.monitor, 'check_duration_threshold',
                             side_effect=SafetyThresholdExceeded("Test threshold")):
                
                result = migration.migrate_to_new_schema()
                
                assert result is False
                # Should NOT have called DELETE for rollback
                delete_calls = [call for call in mock_execute.call_args_list 
                               if "DELETE FROM mcp_configs" in str(call)]
                assert len(delete_calls) == 0
    
    @patch('migrate_mcp_system.execute_query')
    def test_monitoring_integration(self, mock_execute):
        """Test that monitoring is properly integrated in migration process."""
        mock_execute.return_value = [{"result": 1}]
        
        migration = MCPMigration(dry_run=True)
        migration.backup_data = {
            "mcp_servers": [
                {"id": 1, "name": "test-server", "server_type": "stdio", "enabled": True}
            ],
            "agent_assignments": []
        }
        
        with patch.object(migration, 'get_agent_names_for_server', return_value=[]):
            result = migration.migrate_to_new_schema()
        
        assert result is True
        
        # Check that monitoring was used
        summary = migration.monitor.get_summary()
        assert summary["duration_minutes"] >= 0
        assert summary["total_errors"] == 0


class TestMigrationIntegration:
    """Integration tests for complete migration safety system."""
    
    def setup_method(self):
        """Set up clean environment for integration tests."""
        self.original_env = dict(os.environ)
        os.environ["MCP_MIGRATION_ENABLED"] = "true"
        os.environ["MCP_SAFETY_CHECKS"] = "true"
        os.environ["MCP_MONITORING_ENABLED"] = "true"
    
    def teardown_method(self):
        """Restore environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    @patch('migrate_mcp_system.execute_query')
    @patch('migrate_mcp_system.list_mcp_servers')
    @patch('migrate_mcp_system.get_agent_server_assignments')
    @patch('migrate_mcp_system.create_mcp_config')
    def test_complete_migration_with_monitoring(self, mock_create, mock_assignments, 
                                               mock_servers, mock_execute):
        """Test complete migration process with all safety features enabled."""
        # Mock data
        mock_servers.return_value = [
            Mock(id=1, name="test-server", server_type="stdio", enabled=True,
                 description="Test server", command=["echo", "test"], env={},
                 http_url=None, auto_start=True, max_retries=3, timeout_seconds=30,
                 tags=[], priority=1, status="active", tools_discovered=[],
                 resources_discovered=[], created_at=datetime.now(), updated_at=datetime.now())
        ]
        mock_assignments.return_value = [
            Mock(id=1, agent_id=1, mcp_server_id=1, created_at=datetime.now())
        ]
        mock_execute.return_value = [{"result": 1}]
        mock_create.return_value = "new-config-id"
        
        migration = MCPMigration(dry_run=False)
        
        # Test complete workflow
        backup_data = migration.backup_existing_data()
        assert len(backup_data["mcp_servers"]) == 1
        
        result = migration.migrate_to_new_schema()
        assert result is True
        
        # Verify monitoring summary
        summary = migration.monitor.get_summary()
        assert summary["total_errors"] == 0
        assert "test-server" in summary.get("performance_metrics", {})
    
    def test_feature_flag_production_safety(self):
        """Test that production safety is maintained through feature flags."""
        # Clear migration flag to simulate production state
        os.environ["MCP_MIGRATION_ENABLED"] = "false"
        
        migration = MCPMigration(dry_run=False)
        
        # Should refuse to run when migration is disabled
        result = migration.pre_migration_checks()
        assert result is False
        
        # Enable migration
        migration.feature_flags.enable("MCP_MIGRATION_ENABLED")
        
        # Now should pass migration enabled check (though may fail on other checks)
        with patch('migrate_mcp_system.execute_query', return_value=[{"result": 1}]):
            result = migration.pre_migration_checks()
            assert result is True


class TestCommandLineInterface:
    """Test suite for command line interface and flag overrides."""
    
    def test_feature_flag_environment_priority(self):
        """Test that environment variables are properly read for flags."""
        test_flags = {
            "MCP_USE_NEW_SYSTEM": "true",
            "MCP_MIGRATION_ENABLED": "false", 
            "MCP_SAFETY_CHECKS": "false",
            "MCP_AUTO_ROLLBACK": "false",
            "MCP_MONITORING_ENABLED": "false"
        }
        
        # Set environment
        for key, value in test_flags.items():
            os.environ[key] = value
        
        try:
            flags = FeatureFlags()
            
            assert flags.is_enabled("MCP_USE_NEW_SYSTEM") is True
            assert flags.is_enabled("MCP_MIGRATION_ENABLED") is False
            assert flags.is_enabled("MCP_SAFETY_CHECKS") is False
            assert flags.is_enabled("MCP_AUTO_ROLLBACK") is False
            assert flags.is_enabled("MCP_MONITORING_ENABLED") is False
            
        finally:
            # Clean up
            for key in test_flags:
                os.environ.pop(key, None)


# Performance and stress tests
class TestMigrationPerformance:
    """Test suite for migration performance and scalability."""
    
    def test_monitor_performance_under_load(self):
        """Test monitor performance with many errors and warnings."""
        monitor = MigrationMonitor()
        monitor.start_monitoring()
        
        # Record many warnings (should not affect performance significantly)
        start_time = time.time()
        for i in range(100):
            monitor.record_warning(f"Warning {i}", f"context_{i}")
        end_time = time.time()
        
        # Should complete quickly
        duration = end_time - start_time
        assert duration < 1.0  # Should complete in under 1 second
        assert len(monitor.warnings) == 100
    
    def test_large_backup_data_handling(self):
        """Test handling of large backup datasets."""
        migration = MCPMigration(dry_run=True)
        
        # Simulate large backup data
        large_backup = {
            "mcp_servers": [
                {
                    "id": i,
                    "name": f"server-{i}",
                    "server_type": "stdio",
                    "enabled": True,
                    "description": f"Server {i} description",
                    "command": ["echo", f"server-{i}"],
                    "env": {},
                    "auto_start": True,
                    "max_retries": 3,
                    "timeout_seconds": 30
                }
                for i in range(100)  # 100 servers
            ],
            "agent_assignments": []
        }
        
        migration.backup_data = large_backup
        
        # Test transformation performance
        start_time = time.time()
        for server_data in large_backup["mcp_servers"]:
            config = migration.transform_server_config(server_data, [])
            assert config["name"] == server_data["name"]
        end_time = time.time()
        
        # Should handle 100 transformations quickly
        duration = end_time - start_time
        assert duration < 2.0  # Should complete in under 2 seconds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])