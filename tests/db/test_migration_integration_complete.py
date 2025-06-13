"""
Complete Integration Tests for NMSTX-257 Migration Safety System

This test suite provides comprehensive end-to-end testing of the migration safety system,
including safety triggers, rollback mechanisms, and production scenario validation.
"""

import pytest
import os
import time
import json
import tempfile
import shutil
from unittest.mock import Mock, patch
from pathlib import Path
from datetime import datetime

# Add scripts directory for migration module
import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))

try:
    from migrate_mcp_system import (
        MCPMigration,
        SafetyThresholdExceeded,
        FeatureFlags,
        MigrationMonitor
    )
    MIGRATION_MODULE_AVAILABLE = True
except ImportError:
    MIGRATION_MODULE_AVAILABLE = False
    pytest.skip("Migration module not available", allow_module_level=True)


class TestSafetyTriggers:
    """Test suite for automatic safety triggers during migration."""
    
    def setup_method(self):
        """Set up test environment."""
        self.original_env = dict(os.environ)
        os.environ["MCP_MIGRATION_ENABLED"] = "true"
        os.environ["MCP_SAFETY_CHECKS"] = "true"
        os.environ["MCP_MONITORING_ENABLED"] = "true"
        os.environ["MCP_AUTO_ROLLBACK"] = "true"
    
    def teardown_method(self):
        """Clean up test environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_error_threshold_safety_trigger(self):
        """Test automatic rollback when error threshold is exceeded."""
        migration = MCPMigration(dry_run=False)
        migration.backup_data = {
            "mcp_servers": [{"id": i, "name": f"server-{i}", "server_type": "stdio", "enabled": True} 
                           for i in range(10)],
            "agent_assignments": []
        }
        
        with patch('migrate_mcp_system.execute_query') as mock_execute:
            with patch('migrate_mcp_system.create_mcp_config', side_effect=Exception("Server error")):
                with patch.object(migration, 'get_agent_names_for_server', return_value=[]):
                    
                    # Should trigger rollback after 5 errors
                    result = migration.migrate_to_new_schema()
                    
                    assert result is False
                    
                    # Verify rollback was triggered
                    rollback_calls = [call for call in mock_execute.call_args_list 
                                    if "DELETE FROM mcp_configs" in str(call)]
                    assert len(rollback_calls) > 0
    
    def test_duration_threshold_safety_trigger(self):
        """Test automatic rollback when migration takes too long."""
        migration = MCPMigration(dry_run=False)
        migration.backup_data = {
            "mcp_servers": [{"id": 1, "name": "test-server", "server_type": "stdio", "enabled": True}],
            "agent_assignments": []
        }
        
        # Mock time to simulate long duration
        with patch('time.time', side_effect=[0, 0, 32*60]):  # 32 minutes
            with patch('migrate_mcp_system.execute_query'):
                with patch.object(migration, 'get_agent_names_for_server', return_value=[]):
                    
                    result = migration.migrate_to_new_schema()
                    
                    assert result is False
                    
                    # Should have triggered duration threshold
                    assert len(migration.monitor.errors) > 0
                    duration_errors = [e for e in migration.monitor.errors 
                                     if "time limit" in e["error"]]
                    assert len(duration_errors) > 0
    
    def test_response_time_degradation_warning(self):
        """Test warning system for response time degradation."""
        migration = MCPMigration(dry_run=False)
        migration.backup_data = {
            "mcp_servers": [{"id": 1, "name": "test-server", "server_type": "stdio", "enabled": True}],
            "agent_assignments": []
        }
        
        # Mock slow response times
        response_times = [0, 6]  # 6 second response (6000ms > 5000ms threshold)
        
        with patch('time.time', side_effect=response_times):
            with patch('migrate_mcp_system.execute_query', return_value=[{"result": 1}]):
                with patch('migrate_mcp_system.create_mcp_config', return_value="config-id"):
                    with patch.object(migration, 'get_agent_names_for_server', return_value=[]):
                        
                        result = migration.migrate_to_new_schema()
                        
                        # Should complete but with warnings
                        assert result is True
                        assert len(migration.monitor.warnings) > 0
                        
                        # Should have response time warning
                        rt_warnings = [w for w in migration.monitor.warnings 
                                     if "response time" in w["warning"]]
                        assert len(rt_warnings) > 0
    
    def test_safety_triggers_can_be_disabled_for_emergency(self):
        """Test that safety triggers can be disabled for emergency migrations."""
        os.environ["MCP_SAFETY_CHECKS"] = "false"
        os.environ["MCP_AUTO_ROLLBACK"] = "false"
        
        migration = MCPMigration(dry_run=False)
        migration.backup_data = {
            "mcp_servers": [{"id": i, "name": f"server-{i}", "server_type": "stdio", "enabled": True} 
                           for i in range(10)],
            "agent_assignments": []
        }
        
        with patch('migrate_mcp_system.execute_query') as mock_execute:
            with patch('migrate_mcp_system.create_mcp_config', side_effect=Exception("Server error")):
                with patch.object(migration, 'get_agent_names_for_server', return_value=[]):
                    
                    # Should continue despite errors when safety disabled
                    result = migration.migrate_to_new_schema()
                    
                    assert result is False  # Due to errors, but no automatic rollback
                    
                    # Verify NO rollback was triggered
                    rollback_calls = [call for call in mock_execute.call_args_list 
                                    if "DELETE FROM mcp_configs" in str(call)]
                    assert len(rollback_calls) == 0


class TestCompleteEndToEndMigration:
    """End-to-end integration tests for complete migration scenarios."""
    
    def setup_method(self):
        """Set up realistic test environment."""
        self.original_env = dict(os.environ)
        self.temp_dir = tempfile.mkdtemp()
        self.backup_file = os.path.join(self.temp_dir, "test_backup.json")
        
        # Enable all safety features
        os.environ.update({
            "MCP_MIGRATION_ENABLED": "true",
            "MCP_SAFETY_CHECKS": "true", 
            "MCP_MONITORING_ENABLED": "true",
            "MCP_AUTO_ROLLBACK": "true"
        })
    
    def teardown_method(self):
        """Clean up test environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('migrate_mcp_system.list_mcp_servers')
    @patch('migrate_mcp_system.get_agent_server_assignments') 
    @patch('migrate_mcp_system.execute_query')
    @patch('migrate_mcp_system.create_mcp_config')
    @patch('migrate_mcp_system.list_mcp_configs')
    def test_successful_complete_migration(self, mock_list_configs, mock_create, 
                                         mock_execute, mock_assignments, mock_servers):
        """Test successful complete migration with all safety features."""
        # Mock realistic data
        mock_servers.return_value = [
            Mock(id=1, name="git-server", server_type="stdio", enabled=True,
                 description="Git operations server", command=["git", "mcp"], env={},
                 http_url=None, auto_start=True, max_retries=3, timeout_seconds=30,
                 tags=["git"], priority=1, status="active", tools_discovered=["git_status"],
                 resources_discovered=[], created_at=datetime.now(), updated_at=datetime.now()),
            Mock(id=2, name="linear-server", server_type="http", enabled=True,
                 description="Linear integration", command=None, env={},
                 http_url="http://linear.api", auto_start=True, max_retries=3, timeout_seconds=30,
                 tags=["linear"], priority=1, status="active", tools_discovered=["create_issue"],
                 resources_discovered=[], created_at=datetime.now(), updated_at=datetime.now())
        ]
        
        mock_assignments.return_value = [
            Mock(id=1, agent_id=1, mcp_server_id=1, created_at=datetime.now()),
            Mock(id=2, agent_id=1, mcp_server_id=2, created_at=datetime.now())
        ]
        
        # Mock database operations
        mock_execute.return_value = [{"result": 1}]
        mock_create.side_effect = ["config-1", "config-2"]
        
        # Mock validation
        mock_list_configs.return_value = [
            Mock(name="git-server", config={"server_type": "stdio"}),
            Mock(name="linear-server", config={"server_type": "http"})
        ]
        
        # Mock agent name lookup
        with patch('migrate_mcp_system.execute_query', side_effect=[
            [{"result": 1}],  # connectivity test
            [{"result": 1}],  # table check
            [{"name": "simple"}],  # agent lookup for server 1
            [{"name": "simple"}],  # agent lookup for server 2
            [{"result": 1}],  # response time test 1
            [{"result": 1}],  # response time test 2
            [{"result": 1}]   # final response time test
        ]):
            
            migration = MCPMigration(dry_run=False)
            
            # Test complete workflow
            backup_data = migration.backup_existing_data()
            success = migration.migrate_to_new_schema()
            
            assert success is True
            assert len(backup_data["mcp_servers"]) == 2
            
            # Verify monitoring
            summary = migration.monitor.get_summary()
            assert summary["total_errors"] == 0
            assert summary["duration_minutes"] >= 0
            
            # Verify validation
            validation_success = migration.validate_migration()
            assert validation_success is True
    
    def test_migration_with_partial_failure_and_rollback(self):
        """Test migration that partially fails and triggers automatic rollback."""
        migration = MCPMigration(dry_run=False)
        migration.backup_data = {
            "mcp_servers": [
                {"id": 1, "name": "good-server", "server_type": "stdio", "enabled": True},
                {"id": 2, "name": "bad-server", "server_type": "stdio", "enabled": True},
                {"id": 3, "name": "another-server", "server_type": "stdio", "enabled": True}
            ],
            "agent_assignments": []
        }
        
        def create_config_side_effect(config_create):
            if "bad-server" in config_create.name:
                raise Exception("Simulated server creation failure")
            return f"config-{config_create.name}"
        
        with patch('migrate_mcp_system.execute_query') as mock_execute:
            mock_execute.return_value = [{"result": 1}]
            
            with patch('migrate_mcp_system.create_mcp_config', side_effect=create_config_side_effect):
                with patch.object(migration, 'get_agent_names_for_server', return_value=["simple"]):
                    
                    result = migration.migrate_to_new_schema()
                    
                    # Should fail and trigger rollback
                    assert result is False
                    
                    # Verify rollback was called
                    rollback_calls = [call for call in mock_execute.call_args_list 
                                    if "DELETE FROM mcp_configs" in str(call)]
                    assert len(rollback_calls) > 0
                    
                    # Verify error monitoring
                    assert len(migration.monitor.errors) > 0
                    server_errors = [e for e in migration.monitor.errors 
                                   if "bad-server" in e.get("context", "")]
                    assert len(server_errors) > 0
    
    def test_backup_and_restore_functionality(self):
        """Test backup save/load and restore functionality."""
        migration = MCPMigration(dry_run=True)
        
        # Create test backup data
        test_backup = {
            "timestamp": datetime.now().isoformat(),
            "version": "legacy_to_simplified",
            "mcp_servers": [
                {
                    "id": 1,
                    "name": "test-server",
                    "server_type": "stdio",
                    "command": ["echo", "test"],
                    "enabled": True,
                    "created_at": datetime.now().isoformat()
                }
            ],
            "agent_assignments": [
                {
                    "id": 1,
                    "agent_id": 1,
                    "mcp_server_id": 1,
                    "created_at": datetime.now().isoformat()
                }
            ]
        }
        
        migration.backup_data = test_backup
        
        # Test backup save
        success = migration.save_backup_to_file(self.backup_file)
        assert success is True
        assert os.path.exists(self.backup_file)
        
        # Verify backup content
        with open(self.backup_file, 'r') as f:
            saved_backup = json.load(f)
        
        assert saved_backup["version"] == "legacy_to_simplified"
        assert len(saved_backup["mcp_servers"]) == 1
        assert saved_backup["mcp_servers"][0]["name"] == "test-server"
        
        # Test rollback
        with patch('migrate_mcp_system.execute_query') as mock_execute:
            success = migration.rollback_migration(self.backup_file)
            assert success is True
            
            # Verify DELETE was called for rollback
            delete_calls = [call for call in mock_execute.call_args_list 
                           if "DELETE FROM mcp_configs" in str(call)]
            assert len(delete_calls) > 0


class TestProductionScenarios:
    """Test production deployment scenarios and edge cases."""
    
    def setup_method(self):
        """Set up production-like test environment."""
        self.original_env = dict(os.environ)
        
    def teardown_method(self):
        """Clean up test environment."""
        os.environ.clear()
        os.environ.update(self.original_env)
    
    def test_production_migration_with_large_dataset(self):
        """Test migration performance with large production-like dataset."""
        os.environ.update({
            "MCP_MIGRATION_ENABLED": "true",
            "MCP_SAFETY_CHECKS": "true",
            "MCP_MONITORING_ENABLED": "true"
        })
        
        migration = MCPMigration(dry_run=True)
        
        # Simulate large production dataset
        large_backup = {
            "mcp_servers": [
                {
                    "id": i,
                    "name": f"prod-server-{i:03d}",
                    "server_type": "stdio",
                    "command": ["python", f"server_{i}.py"],
                    "enabled": True,
                    "auto_start": True,
                    "max_retries": 3,
                    "timeout_seconds": 30,
                    "tags": ["prod", f"region-{i%5}"],
                    "priority": i % 3 + 1
                }
                for i in range(50)  # 50 production servers
            ],
            "agent_assignments": [
                {
                    "id": i,
                    "agent_id": (i % 10) + 1,
                    "mcp_server_id": (i % 50) + 1,
                    "created_at": datetime.now().isoformat()
                }
                for i in range(200)  # 200 agent-server assignments
            ]
        }
        
        migration.backup_data = large_backup
        
        # Test performance of transformation
        start_time = time.time()
        
        for server_data in large_backup["mcp_servers"]:
            agent_names = migration.get_agent_names_for_server(server_data["id"])
            config = migration.transform_server_config(server_data, agent_names)
            
            # Verify transformation quality
            assert config["name"] == server_data["name"]
            assert config["server_type"] == server_data["server_type"]
            assert "command" in config
            assert "agents" in config
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should handle large dataset efficiently
        assert duration < 5.0  # Should complete 50 transformations in under 5 seconds
    
    def test_production_failure_recovery_scenarios(self):
        """Test various production failure scenarios and recovery."""
        scenarios = [
            {
                "name": "database_connection_lost",
                "error": "Connection to database lost",
                "should_rollback": True
            },
            {
                "name": "disk_space_full", 
                "error": "No space left on device",
                "should_rollback": True
            },
            {
                "name": "permission_denied",
                "error": "Permission denied",
                "should_rollback": True
            },
            {
                "name": "memory_exhausted",
                "error": "Out of memory",
                "should_rollback": True
            }
        ]
        
        for scenario in scenarios:
            os.environ.update({
                "MCP_MIGRATION_ENABLED": "true",
                "MCP_AUTO_ROLLBACK": "true"
            })
            
            migration = MCPMigration(dry_run=False)
            migration.backup_data = {
                "mcp_servers": [{"id": 1, "name": "test", "server_type": "stdio", "enabled": True}],
                "agent_assignments": []
            }
            
            with patch('migrate_mcp_system.execute_query') as mock_execute:
                # First call succeeds (pre-checks), subsequent calls fail
                mock_execute.side_effect = [
                    [{"result": 1}],  # connectivity
                    [{"result": 1}],  # table check
                    Exception(scenario["error"])  # failure during migration
                ]
                
                result = migration.migrate_to_new_schema()
                
                # Should fail gracefully
                assert result is False
                
                # Should record the error
                error_recorded = any(scenario["error"] in e["error"] 
                                   for e in migration.monitor.errors)
                assert error_recorded, f"Error not recorded for scenario: {scenario['name']}"
    
    def test_gradual_rollout_with_feature_flags(self):
        """Test gradual production rollout using feature flags."""
        # Phase 1: Migration disabled (safe default)
        os.environ["MCP_MIGRATION_ENABLED"] = "false"
        migration = MCPMigration(dry_run=False)
        
        result = migration.pre_migration_checks()
        assert result is False  # Should refuse to run
        
        # Phase 2: Migration enabled but with extra safety
        os.environ.update({
            "MCP_MIGRATION_ENABLED": "true",
            "MCP_SAFETY_CHECKS": "true",
            "MCP_AUTO_ROLLBACK": "true",
            "MCP_MONITORING_ENABLED": "true"
        })
        
        migration = MCPMigration(dry_run=True)  # Still dry run for safety
        
        with patch('migrate_mcp_system.execute_query', return_value=[{"result": 1}]):
            result = migration.pre_migration_checks()
            assert result is True  # Should now pass checks
        
        # Phase 3: Full production with monitoring
        migration = MCPMigration(dry_run=False)
        migration.backup_data = {
            "mcp_servers": [{"id": 1, "name": "prod-server", "server_type": "stdio", "enabled": True}],
            "agent_assignments": []
        }
        
        with patch('migrate_mcp_system.execute_query', return_value=[{"result": 1}]):
            with patch('migrate_mcp_system.create_mcp_config', return_value="config-id"):
                with patch.object(migration, 'get_agent_names_for_server', return_value=["simple"]):
                    
                    result = migration.migrate_to_new_schema()
                    assert result is True
                    
                    # Verify monitoring captured performance data
                    summary = migration.monitor.get_summary()
                    assert "prod-server" in summary.get("performance_metrics", {})


class TestMonitoringAndObservability:
    """Test monitoring, logging, and observability features."""
    
    def test_comprehensive_monitoring_data_collection(self):
        """Test that monitoring collects comprehensive operational data."""
        migration = MCPMigration(dry_run=True)
        migration.backup_data = {
            "mcp_servers": [
                {"id": 1, "name": "server-1", "server_type": "stdio", "enabled": True},
                {"id": 2, "name": "server-2", "server_type": "http", "enabled": True}
            ],
            "agent_assignments": []
        }
        
        with patch('migrate_mcp_system.execute_query', return_value=[{"result": 1}]):
            with patch.object(migration, 'get_agent_names_for_server', return_value=["simple"]):
                
                # Simulate some warnings and performance data
                migration.monitor.record_warning("Test warning", "test_context")
                migration.monitor.performance_metrics = {"server-1": 100.0, "server-2": 150.0}
                
                result = migration.migrate_to_new_schema()
                assert result is True
                
                # Verify comprehensive monitoring data
                summary = migration.monitor.get_summary()
                
                assert "duration_minutes" in summary
                assert "total_errors" in summary
                assert "total_warnings" in summary
                assert "errors" in summary
                assert "warnings" in summary
                assert "performance_metrics" in summary
                
                assert summary["total_warnings"] == 1
                assert len(summary["warnings"]) == 1
                assert summary["warnings"][0]["warning"] == "Test warning"
                assert summary["warnings"][0]["context"] == "test_context"
                
                assert "server-1" in summary["performance_metrics"]
                assert "server-2" in summary["performance_metrics"]
    
    def test_monitoring_data_persistence(self):
        """Test that monitoring data can be persisted for analysis."""
        migration = MCPMigration(dry_run=True)
        
        # Add some monitoring data
        migration.monitor.start_monitoring()
        migration.monitor.record_error("Test error", "error_context")
        migration.monitor.record_warning("Test warning", "warning_context")
        migration.monitor.performance_metrics = {"test-server": 200.0}
        
        # Get summary and verify it's serializable
        summary = migration.monitor.get_summary()
        
        # Should be JSON serializable for persistence
        json_str = json.dumps(summary, indent=2)
        recovered_summary = json.loads(json_str)
        
        assert recovered_summary["total_errors"] == 1
        assert recovered_summary["total_warnings"] == 1
        assert recovered_summary["performance_metrics"]["test-server"] == 200.0
        
        # Verify timestamps are properly formatted
        for error in recovered_summary["errors"]:
            # Should be valid ISO format
            datetime.fromisoformat(error["timestamp"])
        
        for warning in recovered_summary["warnings"]:
            datetime.fromisoformat(warning["timestamp"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])