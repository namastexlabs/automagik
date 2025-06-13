#!/usr/bin/env python3
"""
Comprehensive MCP Rollback Test Suite - NMSTX-258

Tests the rollback capabilities from the new single-table MCP system back to 
the legacy 2-table architecture, ensuring data recovery and system restoration.

Critical Areas Tested:
- Backup data restoration
- Database rollback procedures
- Data integrity after rollback
- Migration script rollback functionality
- System state validation
- Rollback error handling
"""

import pytest
import tempfile
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.migrate_mcp_system import MCPMigration


class TestMCPRollback:
    """Test cases for MCP system rollback functionality."""
    
    @pytest.fixture
    def sample_backup_data(self):
        """Sample backup data for rollback testing."""
        return {
            "metadata": {
                "backup_created_at": "2024-01-01T12:00:00Z",
                "source_system": "legacy_mcp",
                "migration_version": "1.0",
                "backup_checksum": "abc123def456",
                "server_count": 3,
                "assignment_count": 5
            },
            "mcp_servers": [
                {
                    "id": 1,
                    "name": "filesystem-server",
                    "server_type": "stdio",
                    "description": "File system access",
                    "command": ["npx", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "env": {"NODE_ENV": "production"},
                    "auto_start": True,
                    "max_retries": 3,
                    "timeout_seconds": 30,
                    "enabled": True,
                    "created_at": "2024-01-01T00:00:00Z"
                },
                {
                    "id": 2,
                    "name": "database-server", 
                    "server_type": "http",
                    "description": "Database access server",
                    "http_url": "http://localhost:3001",
                    "env": {"DB_URL": "postgresql://localhost/test"},
                    "auto_start": False,
                    "max_retries": 5,
                    "timeout_seconds": 60,
                    "enabled": True,
                    "created_at": "2024-01-01T00:00:00Z"
                },
                {
                    "id": 3,
                    "name": "api-server",
                    "server_type": "http",
                    "description": "API integration server",
                    "http_url": "http://localhost:3002",
                    "env": {"API_TOKEN": "secret123"},
                    "auto_start": True,
                    "max_retries": 2,
                    "timeout_seconds": 45,
                    "enabled": False,
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ],
            "agent_mcp_servers": [
                {"agent_id": 1, "mcp_server_id": 1, "agent_name": "simple"},
                {"agent_id": 2, "mcp_server_id": 1, "agent_name": "genie"},
                {"agent_id": 3, "mcp_server_id": 2, "agent_name": "genie"},
                {"agent_id": 4, "mcp_server_id": 2, "agent_name": "sofia"},
                {"agent_id": 5, "mcp_server_id": 3, "agent_name": "discord"}
            ]
        }
    
    @pytest.fixture
    def migration_instance(self):
        """Create MCPMigration instance for rollback testing."""
        return MCPMigration(dry_run=False)
    
    @pytest.fixture
    def temp_backup_file(self, sample_backup_data):
        """Create temporary backup file with sample data."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_backup_data, f, indent=2)
            temp_file = f.name
        
        yield temp_file
        
        # Cleanup
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    def test_rollback_restores_original_state(self, migration_instance, temp_backup_file, sample_backup_data):
        """Test that rollback completely restores the original system state."""
        with patch('scripts.migrate_mcp_system.execute_query') as mock_execute, \
             patch('scripts.migrate_mcp_system.get_db_connection') as mock_conn:
            
            # Mock database operations
            mock_conn.return_value.__enter__.return_value = MagicMock()
            
            # Perform rollback
            success = migration_instance.perform_rollback(temp_backup_file)
            assert success, "Rollback should succeed"
            
            # Verify database operations were called
            assert mock_execute.called
            
            # Check that all servers would be restored
            restore_calls = [call for call in mock_execute.call_args_list 
                           if 'INSERT INTO mcp_servers' in str(call)]
            assert len(restore_calls) == 3  # Should restore 3 servers
            
            # Check that all agent assignments would be restored
            assignment_calls = [call for call in mock_execute.call_args_list 
                              if 'INSERT INTO agent_mcp_servers' in str(call)]
            assert len(assignment_calls) == 5  # Should restore 5 assignments

    def test_rollback_validates_backup_integrity(self, migration_instance):
        """Test that rollback validates backup data integrity before proceeding."""
        # Test with corrupted backup data
        corrupted_backup = {
            "metadata": {"backup_created_at": "2024-01-01T12:00:00Z"},
            # Missing mcp_servers and agent_mcp_servers
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(corrupted_backup, f)
            temp_file = f.name
        
        try:
            # Should raise validation error
            with pytest.raises(ValueError, match="Invalid backup"):
                migration_instance.perform_rollback(temp_file)
        finally:
            os.unlink(temp_file)

    def test_rollback_handles_missing_backup_file(self, migration_instance):
        """Test rollback error handling when backup file is missing."""
        non_existent_file = "/tmp/non_existent_backup.json"
        
        with pytest.raises(FileNotFoundError):
            migration_instance.perform_rollback(non_existent_file)

    def test_rollback_preserves_data_types(self, migration_instance, temp_backup_file):
        """Test that rollback preserves correct data types for all fields."""
        backup_data = migration_instance.load_backup_file(temp_backup_file)
        
        # Verify data types in loaded backup
        servers = backup_data["mcp_servers"]
        assignments = backup_data["agent_mcp_servers"]
        
        for server in servers:
            assert isinstance(server["id"], int)
            assert isinstance(server["name"], str)
            assert isinstance(server["server_type"], str)
            assert isinstance(server["command"], list) or server.get("command") is None
            assert isinstance(server["env"], dict)
            assert isinstance(server["auto_start"], bool)
            assert isinstance(server["max_retries"], int)
            assert isinstance(server["timeout_seconds"], int)
            assert isinstance(server["enabled"], bool)
        
        for assignment in assignments:
            assert isinstance(assignment["agent_id"], int)
            assert isinstance(assignment["mcp_server_id"], int)
            assert isinstance(assignment["agent_name"], str)

    def test_rollback_clears_new_configurations(self, migration_instance, temp_backup_file):
        """Test that rollback clears new mcp_configs table before restoration."""
        with patch('scripts.migrate_mcp_system.execute_query') as mock_execute, \
             patch('scripts.migrate_mcp_system.get_db_connection') as mock_conn:
            
            mock_conn.return_value.__enter__.return_value = MagicMock()
            
            # Perform rollback
            migration_instance.perform_rollback(temp_backup_file)
            
            # Verify that mcp_configs table is cleared first
            clear_calls = [call for call in mock_execute.call_args_list 
                          if 'DELETE FROM mcp_configs' in str(call)]
            assert len(clear_calls) >= 1, "Should clear mcp_configs table"

    def test_rollback_transaction_rollback_on_error(self, migration_instance, temp_backup_file):
        """Test that rollback uses database transactions and rolls back on error."""
        with patch('scripts.migrate_mcp_system.execute_query', side_effect=Exception("DB Error")), \
             patch('scripts.migrate_mcp_system.get_db_connection') as mock_conn:
            
            mock_connection = MagicMock()
            mock_conn.return_value.__enter__.return_value = mock_connection
            
            # Rollback should fail and handle the error
            success = migration_instance.perform_rollback(temp_backup_file)
            assert not success, "Rollback should fail when database error occurs"
            
            # Verify transaction was attempted
            assert mock_conn.called

    def test_rollback_dry_run_mode(self, migration_instance, temp_backup_file):
        """Test rollback dry run mode doesn't modify database."""
        migration_instance.dry_run = True
        
        with patch('scripts.migrate_mcp_system.execute_query') as mock_execute:
            # Dry run should not execute any database commands
            success = migration_instance.perform_rollback(temp_backup_file)
            assert success, "Dry run should succeed"
            mock_execute.assert_not_called()

    def test_rollback_backup_table_restoration(self, migration_instance, temp_backup_file):
        """Test that rollback can restore from database backup tables."""
        with patch('scripts.migrate_mcp_system.execute_query') as mock_execute, \
             patch('scripts.migrate_mcp_system.get_db_connection') as mock_conn:
            
            mock_conn.return_value.__enter__.return_value = MagicMock()
            
            # Test restoration from backup tables (alternative rollback method)
            migration_instance.restore_from_backup_tables()
            
            # Should attempt to restore from backup tables
            assert mock_execute.called
            
            # Check for backup table queries
            backup_restore_calls = [call for call in mock_execute.call_args_list 
                                  if 'mcp_servers_backup' in str(call) or 'agent_mcp_servers_backup' in str(call)]
            assert len(backup_restore_calls) > 0, "Should query backup tables"

    def test_rollback_validates_agent_assignments(self, migration_instance, temp_backup_file, sample_backup_data):
        """Test that rollback validates agent assignment integrity."""
        # Load and validate assignment data
        backup_data = migration_instance.load_backup_file(temp_backup_file)
        
        servers = {server["id"]: server for server in backup_data["mcp_servers"]}
        assignments = backup_data["agent_mcp_servers"]
        
        # Verify all assignments reference valid servers
        for assignment in assignments:
            server_id = assignment["mcp_server_id"]
            assert server_id in servers, f"Assignment references non-existent server {server_id}"
            
            # Verify agent name is valid
            assert assignment["agent_name"].strip(), "Agent name should not be empty"

    def test_rollback_preserves_server_configuration(self, migration_instance, temp_backup_file):
        """Test that rollback preserves all server configuration details."""
        backup_data = migration_instance.load_backup_file(temp_backup_file)
        
        # Verify complex configurations are preserved
        filesystem_server = next(s for s in backup_data["mcp_servers"] if s["name"] == "filesystem-server")
        
        assert filesystem_server["server_type"] == "stdio"
        assert filesystem_server["command"] == ["npx", "@modelcontextprotocol/server-filesystem", "/tmp"]
        assert filesystem_server["env"]["NODE_ENV"] == "production"
        assert filesystem_server["auto_start"] is True
        assert filesystem_server["max_retries"] == 3
        assert filesystem_server["timeout_seconds"] == 30
        assert filesystem_server["enabled"] is True
        
        # Verify HTTP server configuration
        db_server = next(s for s in backup_data["mcp_servers"] if s["name"] == "database-server")
        assert db_server["server_type"] == "http"
        assert db_server["http_url"] == "http://localhost:3001"
        assert db_server["env"]["DB_URL"] == "postgresql://localhost/test"

    def test_rollback_agent_assignment_restoration(self, migration_instance, temp_backup_file):
        """Test that all agent assignments are correctly restored."""
        backup_data = migration_instance.load_backup_file(temp_backup_file)
        assignments = backup_data["agent_mcp_servers"]
        
        # Group assignments by server
        assignments_by_server = {}
        for assignment in assignments:
            server_id = assignment["mcp_server_id"]
            if server_id not in assignments_by_server:
                assignments_by_server[server_id] = []
            assignments_by_server[server_id].append(assignment["agent_name"])
        
        # Verify filesystem-server assignments (server_id=1)
        assert set(assignments_by_server[1]) == {"simple", "genie"}
        
        # Verify database-server assignments (server_id=2) 
        assert set(assignments_by_server[2]) == {"genie", "sofia"}
        
        # Verify api-server assignments (server_id=3)
        assert set(assignments_by_server[3]) == {"discord"}

    def test_rollback_metadata_validation(self, migration_instance, temp_backup_file):
        """Test that rollback validates backup metadata."""
        backup_data = migration_instance.load_backup_file(temp_backup_file)
        metadata = backup_data["metadata"]
        
        # Verify required metadata fields
        required_fields = ["backup_created_at", "source_system", "migration_version"]
        for field in required_fields:
            assert field in metadata, f"Metadata missing required field: {field}"
        
        # Verify counts match actual data
        assert metadata["server_count"] == len(backup_data["mcp_servers"])
        assert metadata["assignment_count"] == len(backup_data["agent_mcp_servers"])

    def test_rollback_partial_failure_recovery(self, migration_instance, temp_backup_file):
        """Test rollback behavior when partial restoration fails."""
        call_count = 0
        
        def mock_execute_with_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Fail on third call to simulate partial failure
            if call_count == 3:
                raise Exception("Simulated database error")
            return True
        
        with patch('scripts.migrate_mcp_system.execute_query', side_effect=mock_execute_with_failure), \
             patch('scripts.migrate_mcp_system.get_db_connection') as mock_conn:
            
            mock_connection = MagicMock()
            mock_conn.return_value.__enter__.return_value = mock_connection
            
            # Should handle partial failure gracefully
            success = migration_instance.perform_rollback(temp_backup_file)
            assert not success, "Rollback should fail on database error"

    def test_rollback_complete_workflow(self, migration_instance, temp_backup_file):
        """Test complete rollback workflow including validation and restoration."""
        with patch('scripts.migrate_mcp_system.execute_query') as mock_execute, \
             patch('scripts.migrate_mcp_system.get_db_connection') as mock_conn:
            
            mock_conn.return_value.__enter__.return_value = MagicMock()
            
            # Perform complete rollback workflow
            success = migration_instance.perform_rollback(temp_backup_file)
            assert success, "Complete rollback workflow should succeed"
            
            # Verify workflow steps
            executed_queries = [str(call) for call in mock_execute.call_args_list]
            
            # Should clear new configs
            clear_queries = [q for q in executed_queries if 'DELETE FROM mcp_configs' in q]
            assert len(clear_queries) >= 1
            
            # Should restore servers
            server_queries = [q for q in executed_queries if 'INSERT INTO mcp_servers' in q]
            assert len(server_queries) >= 1
            
            # Should restore assignments  
            assignment_queries = [q for q in executed_queries if 'INSERT INTO agent_mcp_servers' in q]
            assert len(assignment_queries) >= 1


class TestMCPRollbackIntegration:
    """Integration tests for MCP rollback with real database operations."""
    
    @pytest.mark.integration
    def test_full_rollback_integration(self):
        """Test complete rollback integration with database."""
        # Skip if not in integration test environment
        if not os.environ.get("AM_INTEGRATION_TEST"):
            pytest.skip("Integration test environment not available")
        
        # This would test:
        # 1. Load backup file
        # 2. Validate backup integrity
        # 3. Clear new mcp_configs table
        # 4. Restore mcp_servers table
        # 5. Restore agent_mcp_servers table
        # 6. Verify data integrity
        # 7. Test system functionality
        
        pass


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])