"""
NMSTX-257 Migration Safety System - Test Coverage Validation

This module provides unit tests that can run independently to validate
the migration safety features without requiring full database connectivity.
"""

import pytest
import os
import time
import json
from unittest.mock import Mock, patch
from datetime import datetime

# Test imports directly
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))

try:
    from migrate_mcp_system import (
        FeatureFlags,
        MigrationMonitor, 
        SafetyThresholdExceeded,
        MCPMigration
    )
    MIGRATION_MODULE_AVAILABLE = True
except ImportError as e:
    MIGRATION_MODULE_AVAILABLE = False
    pytest.skip(f"Migration module not available: {e}", allow_module_level=True)


class TestFeatureFlagsValidation:
    """Isolated tests for FeatureFlags class."""
    
    def setup_method(self):
        """Clean environment for each test."""
        self.original_env = dict(os.environ)
        # Clear test flags
        for flag in ["MCP_USE_NEW_SYSTEM", "MCP_MIGRATION_ENABLED", 
                    "MCP_SAFETY_CHECKS", "MCP_AUTO_ROLLBACK", "MCP_MONITORING_ENABLED"]:
            os.environ.pop(flag, None)
    
    def teardown_method(self):
        """Restore environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_feature_flags_default_safety_values(self):
        """Test that safety flags default to safe values."""
        flags = FeatureFlags()
        
        # These should default to True for production safety
        assert flags.is_enabled("MCP_SAFETY_CHECKS") is True
        assert flags.is_enabled("MCP_AUTO_ROLLBACK") is True
        assert flags.is_enabled("MCP_MONITORING_ENABLED") is True
        
        # These should default to False requiring explicit enablement
        assert flags.is_enabled("MCP_USE_NEW_SYSTEM") is False
        assert flags.is_enabled("MCP_MIGRATION_ENABLED") is False
    
    def test_feature_flags_environment_parsing(self):
        """Test environment variable parsing robustness."""
        test_cases = [
            ("true", True), ("TRUE", True), ("1", True), ("yes", True), ("on", True),
            ("false", False), ("FALSE", False), ("0", False), ("no", False), ("off", False),
            ("invalid", False), ("", False), ("random", False)
        ]
        
        for env_value, expected in test_cases:
            os.environ["MCP_USE_NEW_SYSTEM"] = env_value
            flags = FeatureFlags()
            actual = flags.is_enabled("MCP_USE_NEW_SYSTEM")
            assert actual == expected, f"Failed for env_value='{env_value}', expected={expected}, got={actual}"
    
    def test_feature_flags_runtime_modification(self):
        """Test runtime flag modification."""
        flags = FeatureFlags()
        
        # Test enabling
        flags.enable("MCP_MIGRATION_ENABLED")
        assert flags.is_enabled("MCP_MIGRATION_ENABLED") is True
        assert os.environ["MCP_MIGRATION_ENABLED"] == "true"
        
        # Test disabling
        flags.disable("MCP_MIGRATION_ENABLED")
        assert flags.is_enabled("MCP_MIGRATION_ENABLED") is False
        assert os.environ["MCP_MIGRATION_ENABLED"] == "false"


class TestMigrationMonitorValidation:
    """Isolated tests for MigrationMonitor class."""
    
    def setup_method(self):
        """Create fresh monitor."""
        self.monitor = MigrationMonitor()
    
    def test_monitor_initialization_values(self):
        """Test monitor initializes with correct safety thresholds."""
        assert self.monitor.start_time is None
        assert len(self.monitor.errors) == 0
        assert len(self.monitor.warnings) == 0
        assert len(self.monitor.performance_metrics) == 0
        
        # Verify safety thresholds
        expected = {
            "max_errors": 5,
            "max_duration_minutes": 30,
            "min_success_rate": 0.8,
            "max_response_time_ms": 5000,
        }
        assert self.monitor.safety_thresholds == expected
    
    def test_error_recording_and_threshold(self):
        """Test error recording and threshold enforcement."""
        # Record errors up to threshold
        for i in range(4):
            self.monitor.record_error(f"Error {i}", "test_context")
        
        assert len(self.monitor.errors) == 4
        
        # Fifth error should trigger threshold exception
        with pytest.raises(SafetyThresholdExceeded, match="Too many errors: 5"):
            self.monitor.record_error("Threshold error", "test")
    
    def test_warning_recording(self):
        """Test warning recording functionality."""
        self.monitor.record_warning("Test warning", "test_context")
        
        assert len(self.monitor.warnings) == 1
        warning = self.monitor.warnings[0]
        assert warning["warning"] == "Test warning"
        assert warning["context"] == "test_context"
        assert "timestamp" in warning
        
        # Verify timestamp format
        datetime.fromisoformat(warning["timestamp"])
    
    def test_duration_threshold_enforcement(self):
        """Test duration threshold checking."""
        self.monitor.start_monitoring()
        
        # Simulate exceeding time limit (31 minutes)
        self.monitor.start_time = time.time() - (31 * 60)
        
        with pytest.raises(SafetyThresholdExceeded, match="Migration exceeded time limit"):
            self.monitor.check_duration_threshold()
    
    def test_response_time_monitoring(self):
        """Test response time monitoring with mocked database."""
        with patch('migrate_mcp_system.execute_query') as mock_execute:
            mock_execute.return_value = [{"result": 1}]
            
            # Test normal response time
            response_time = self.monitor.test_response_time()
            
            assert isinstance(response_time, float)
            assert response_time >= 0
            mock_execute.assert_called_with("SELECT 1", fetch=True)
    
    def test_response_time_warning_generation(self):
        """Test that slow response times generate warnings."""
        with patch('migrate_mcp_system.execute_query') as mock_execute:
            mock_execute.return_value = [{"result": 1}]
            
            # Mock slow response (6 seconds = 6000ms > 5000ms threshold)
            with patch('time.time', side_effect=[0, 6]):
                response_time = self.monitor.test_response_time()
                
                assert response_time == 6000
                assert len(self.monitor.warnings) == 1
                assert "High response time" in self.monitor.warnings[0]["warning"]
    
    def test_monitoring_summary_generation(self):
        """Test comprehensive monitoring summary."""
        self.monitor.start_monitoring()
        self.monitor.record_error("Test error", "error_context")
        self.monitor.record_warning("Test warning", "warning_context")
        self.monitor.performance_metrics = {"server1": 100.0, "server2": 200.0}
        
        summary = self.monitor.get_summary()
        
        # Verify all expected fields
        required_fields = ["duration_minutes", "total_errors", "total_warnings", 
                          "errors", "warnings", "performance_metrics"]
        for field in required_fields:
            assert field in summary
        
        assert summary["total_errors"] == 1
        assert summary["total_warnings"] == 1
        assert len(summary["errors"]) == 1
        assert len(summary["warnings"]) == 1
        assert summary["performance_metrics"]["server1"] == 100.0


class TestMCPMigrationSafetyValidation:
    """Isolated tests for MCPMigration safety integration."""
    
    def setup_method(self):
        """Setup test environment."""
        self.original_env = dict(os.environ)
        os.environ["MCP_MIGRATION_ENABLED"] = "true"
    
    def teardown_method(self):
        """Cleanup environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_migration_safety_initialization(self):
        """Test migration initializes with proper safety components."""
        migration = MCPMigration(dry_run=True)
        
        assert isinstance(migration.feature_flags, FeatureFlags)
        assert isinstance(migration.monitor, MigrationMonitor)
        assert migration.dry_run is True
        assert migration.backup_data == {}
        assert isinstance(migration.auto_rollback_enabled, bool)
    
    def test_pre_migration_safety_disabled_by_flag(self):
        """Test migration refuses to run when disabled by flag."""
        os.environ["MCP_MIGRATION_ENABLED"] = "false"
        
        migration = MCPMigration(dry_run=True)
        result = migration.pre_migration_checks()
        
        assert result is False
    
    def test_server_config_transformation(self):
        """Test server configuration transformation logic."""
        migration = MCPMigration(dry_run=True)
        
        legacy_config = {
            "id": 1,
            "name": "test-server",
            "server_type": "stdio",
            "command": ["echo", "test"],
            "enabled": True,
            "auto_start": True,
            "max_retries": 3,
            "timeout_seconds": 30,
            "description": "Test server",
            "tags": ["test"],
            "priority": 1
        }
        
        agent_names = ["simple", "genie"]
        
        transformed = migration.transform_server_config(legacy_config, agent_names)
        
        # Verify transformation correctness
        assert transformed["name"] == "test-server"
        assert transformed["server_type"] == "stdio"
        assert transformed["command"] == ["echo", "test"]
        assert transformed["agents"] == ["simple", "genie"]
        assert transformed["enabled"] is True
        assert transformed["auto_start"] is True
        assert transformed["retry_count"] == 3
        assert transformed["timeout"] == 30000  # Converted to ms
        assert transformed["description"] == "Test server"
        assert transformed["tags"] == ["test"]
        assert transformed["priority"] == 1
        
        # Verify tools configuration
        assert "tools" in transformed
        assert transformed["tools"]["include"] == ["*"]
        assert transformed["tools"]["exclude"] == []
    
    def test_server_config_transformation_with_wildcard_agents(self):
        """Test transformation with no agent assignments (should use wildcard)."""
        migration = MCPMigration(dry_run=True)
        
        legacy_config = {
            "id": 1,
            "name": "global-server",
            "server_type": "http",
            "http_url": "http://api.example.com",
            "enabled": True
        }
        
        # No agent assignments
        transformed = migration.transform_server_config(legacy_config, [])
        
        assert transformed["agents"] == ["*"]  # Should default to wildcard
        assert transformed["url"] == "http://api.example.com"
        assert "command" not in transformed  # HTTP servers don't have commands
    
    def test_backup_data_structure_validation(self):
        """Test backup data structure validation."""
        migration = MCPMigration(dry_run=True)
        
        # Test with invalid backup data
        migration.backup_data = {}
        
        with patch.object(migration.monitor, 'record_error') as mock_record_error:
            result = migration.migrate_to_new_schema()
            
            assert result is False
            mock_record_error.assert_called_with(
                "No backup data available for migration", 
                "migration_start"
            )


class TestSafetyIntegrationScenarios:
    """Test integration scenarios for safety features."""
    
    def test_safety_threshold_exception_properties(self):
        """Test SafetyThresholdExceeded exception properties."""
        message = "Test safety threshold exceeded"
        exception = SafetyThresholdExceeded(message)
        
        assert str(exception) == message
        assert isinstance(exception, Exception)
        
        # Test that it can be caught as base Exception
        try:
            raise SafetyThresholdExceeded("Test")
        except Exception as e:
            assert isinstance(e, SafetyThresholdExceeded)
    
    def test_feature_flag_production_safety_scenarios(self):
        """Test production safety flag scenarios."""
        # Scenario 1: Fresh deployment (all flags default)
        flags = FeatureFlags()
        
        # Should be safe by default
        assert flags.is_enabled("MCP_SAFETY_CHECKS") is True
        assert flags.is_enabled("MCP_AUTO_ROLLBACK") is True
        assert flags.is_enabled("MCP_MONITORING_ENABLED") is True
        
        # Should require explicit enablement
        assert flags.is_enabled("MCP_MIGRATION_ENABLED") is False
        
        # Scenario 2: Emergency override (disable safety for critical fixes)
        flags.disable("MCP_SAFETY_CHECKS")
        flags.disable("MCP_AUTO_ROLLBACK")
        
        assert flags.is_enabled("MCP_SAFETY_CHECKS") is False
        assert flags.is_enabled("MCP_AUTO_ROLLBACK") is False
        
        # Monitoring should still be enabled for observability
        assert flags.is_enabled("MCP_MONITORING_ENABLED") is True
    
    def test_monitoring_data_serialization(self):
        """Test that monitoring data can be serialized for persistence."""
        monitor = MigrationMonitor()
        monitor.start_monitoring()
        monitor.record_error("Test error", "context")
        monitor.record_warning("Test warning", "context")
        monitor.performance_metrics = {"server1": 123.45, "server2": 678.90}
        
        summary = monitor.get_summary()
        
        # Should be JSON serializable
        json_str = json.dumps(summary, indent=2)
        recovered = json.loads(json_str)
        
        assert recovered["total_errors"] == 1
        assert recovered["total_warnings"] == 1
        assert recovered["performance_metrics"]["server1"] == 123.45
        
        # Timestamps should be valid ISO format
        for error in recovered["errors"]:
            datetime.fromisoformat(error["timestamp"])
        
        for warning in recovered["warnings"]:
            datetime.fromisoformat(warning["timestamp"])


class TestImplementationCompleteness:
    """Validate that all required components are implemented."""
    
    def test_feature_flags_completeness(self):
        """Test that all required feature flags are implemented."""
        flags = FeatureFlags()
        
        required_flags = [
            "MCP_USE_NEW_SYSTEM",
            "MCP_MIGRATION_ENABLED", 
            "MCP_SAFETY_CHECKS",
            "MCP_AUTO_ROLLBACK",
            "MCP_MONITORING_ENABLED"
        ]
        
        for flag in required_flags:
            # Should not raise exception
            result = flags.is_enabled(flag)
            assert isinstance(result, bool)
    
    def test_safety_thresholds_completeness(self):
        """Test that all required safety thresholds are defined."""
        monitor = MigrationMonitor()
        
        required_thresholds = [
            "max_errors",
            "max_duration_minutes", 
            "min_success_rate",
            "max_response_time_ms"
        ]
        
        for threshold in required_thresholds:
            assert threshold in monitor.safety_thresholds
            assert isinstance(monitor.safety_thresholds[threshold], (int, float))
    
    def test_migration_methods_completeness(self):
        """Test that all required migration methods are implemented."""
        migration = MCPMigration(dry_run=True)
        
        required_methods = [
            "backup_existing_data",
            "transform_server_config", 
            "get_agent_names_for_server",
            "pre_migration_checks",
            "migrate_to_new_schema",
            "validate_migration",
            "save_backup_to_file",
            "rollback_migration"
        ]
        
        for method in required_methods:
            assert hasattr(migration, method)
            assert callable(getattr(migration, method))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])