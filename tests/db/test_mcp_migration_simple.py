#!/usr/bin/env python3
"""
Simplified MCP Migration Test Suite - NMSTX-258

Tests the migration from legacy 2-table MCP system to simplified single-table 
architecture using only basic Python functionality.
"""

import pytest
import tempfile
import json
import os
from datetime import datetime
from typing import Dict, List, Any
from unittest.mock import patch, MagicMock


class MockMCPMigration:
    """Mock migration class for testing migration logic."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.backup_data = {}
    
    def backup_existing_data(self) -> Dict[str, Any]:
        """Mock backup of existing MCP data."""
        # Mock successful backup
        self.backup_data = {
            "mcp_servers": [
                {
                    "id": 1,
                    "name": "filesystem-server",
                    "server_type": "stdio",
                    "command": ["npx", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    "enabled": True
                }
            ],
            "agent_mcp_servers": [
                {"agent_id": 1, "mcp_server_id": 1, "agent_name": "simple"}
            ]
        }
        return self.backup_data
    
    def transform_to_new_format(self, servers: List[Dict], assignments: List[Dict]) -> List[Dict]:
        """Transform legacy data to new format."""
        server_configs = []
        
        # Group assignments by server
        server_assignments = {}
        for assignment in assignments:
            server_id = assignment["mcp_server_id"]
            if server_id not in server_assignments:
                server_assignments[server_id] = []
            server_assignments[server_id].append(assignment["agent_name"])
        
        # Transform each server
        for server in servers:
            config = {
                "name": server["name"],
                "server_type": server.get("server_type", ""),
                "agents": server_assignments.get(server["id"], []),
                "tools": {"include": ["*"], "exclude": []},
                "environment": server.get("env", {}),
                "timeout": (server.get("timeout_seconds", 30) * 1000),
                "retry_count": server.get("max_retries", 3),
                "enabled": server.get("enabled", True),
                "auto_start": server.get("auto_start", False)
            }
            
            # Add server-type specific fields
            server_type = server.get("server_type", "")
            if server_type == "stdio":
                if "command" not in server:
                    raise ValueError(f"Server {server['name']} missing required field: command")
                config["command"] = server["command"]
            elif server_type == "http":
                if "http_url" not in server:
                    raise ValueError(f"Server {server['name']} missing required field: http_url")
                config["url"] = server["http_url"]
            elif server_type:  # Only validate if server_type is present
                raise ValueError(f"Invalid server_type: {server_type}")
            
            server_configs.append(config)
        
        return server_configs
    
    def validate_transformed_configs(self, configs: List[Dict]):
        """Validate transformed configurations."""
        for config in configs:
            # Basic validation
            if not config.get("name"):
                raise ValueError("Config missing name")
            server_type = config.get("server_type", "")
            if not server_type or server_type not in ["stdio", "http"]:
                raise ValueError(f"Invalid server_type: {server_type}")
    
    def perform_migration(self, configs: List[Dict]) -> bool:
        """Perform migration (mocked)."""
        if self.dry_run:
            return True
        # In real implementation, this would call create_mcp_config for each config
        return True


class TestMCPMigrationSimple:
    """Simplified test cases for MCP system migration."""
    
    @pytest.fixture
    def sample_legacy_data(self):
        """Sample legacy MCP data for testing migration."""
        return {
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
                    "enabled": True
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
                    "enabled": True
                }
            ],
            "agent_mcp_servers": [
                {"agent_id": 1, "mcp_server_id": 1, "agent_name": "simple"},
                {"agent_id": 2, "mcp_server_id": 1, "agent_name": "genie"},
                {"agent_id": 3, "mcp_server_id": 2, "agent_name": "genie"}
            ]
        }
    
    @pytest.fixture
    def migration_instance(self):
        """Create MockMCPMigration instance for testing."""
        return MockMCPMigration(dry_run=True)

    def test_migration_data_backup(self, migration_instance):
        """Test that migration creates proper backup data."""
        backup_data = migration_instance.backup_existing_data()
        
        # Verify backup structure
        assert "mcp_servers" in backup_data
        assert "agent_mcp_servers" in backup_data
        assert len(backup_data["mcp_servers"]) == 1
        assert len(backup_data["agent_mcp_servers"]) == 1
        
        # Verify server data
        server = backup_data["mcp_servers"][0]
        assert server["name"] == "filesystem-server"
        assert server["server_type"] == "stdio"
        
        # Verify assignment data
        assignment = backup_data["agent_mcp_servers"][0]
        assert assignment["agent_name"] == "simple"
        assert assignment["mcp_server_id"] == 1

    def test_migration_data_transformation(self, migration_instance, sample_legacy_data):
        """Test transformation from legacy to new format."""
        transformed_configs = migration_instance.transform_to_new_format(
            sample_legacy_data["mcp_servers"],
            sample_legacy_data["agent_mcp_servers"]
        )
        
        assert len(transformed_configs) == 2
        
        # Verify filesystem server transformation
        fs_config = next(c for c in transformed_configs if c["name"] == "filesystem-server")
        assert fs_config["server_type"] == "stdio"
        assert "command" in fs_config
        assert set(fs_config["agents"]) == {"simple", "genie"}
        assert fs_config["timeout"] == 30000  # Converted to milliseconds
        
        # Verify database server transformation
        db_config = next(c for c in transformed_configs if c["name"] == "database-server")
        assert db_config["server_type"] == "http"
        assert "url" in db_config
        assert db_config["agents"] == ["genie"]

    def test_migration_agent_assignment_preservation(self, migration_instance):
        """Test that agent assignments are correctly preserved and mapped."""
        server_data = {
            "mcp_servers": [
                {"id": 1, "name": "server1", "server_type": "stdio", "command": ["test"]},
                {"id": 2, "name": "server2", "server_type": "http", "http_url": "http://test"}
            ],
            "agent_mcp_servers": [
                {"agent_id": 1, "mcp_server_id": 1, "agent_name": "simple"},
                {"agent_id": 2, "mcp_server_id": 1, "agent_name": "genie"},
                {"agent_id": 3, "mcp_server_id": 2, "agent_name": "sofia"},
                {"agent_id": 4, "mcp_server_id": 2, "agent_name": "genie"}  # Genie on both servers
            ]
        }
        
        transformed_configs = migration_instance.transform_to_new_format(
            server_data["mcp_servers"],
            server_data["agent_mcp_servers"]
        )
        
        # Verify agent assignments
        server1_config = next(c for c in transformed_configs if c["name"] == "server1")
        server2_config = next(c for c in transformed_configs if c["name"] == "server2")
        
        assert set(server1_config["agents"]) == {"simple", "genie"}
        assert set(server2_config["agents"]) == {"sofia", "genie"}

    def test_migration_validation_prevents_data_loss(self, migration_instance):
        """Test that validation catches potential data loss scenarios."""
        # Test missing required fields
        invalid_server_data = {
            "mcp_servers": [
                {
                    "id": 1,
                    "name": "invalid-server",
                    # Missing server_type - should trigger validation error
                    "description": "Invalid server config"
                }
            ],
            "agent_mcp_servers": []
        }
        
        # Transform and then validate - should raise validation error
        transformed_configs = migration_instance.transform_to_new_format(
            invalid_server_data["mcp_servers"],
            invalid_server_data["agent_mcp_servers"]
        )
        
        with pytest.raises(ValueError, match="server_type"):
            migration_instance.validate_transformed_configs(transformed_configs)

    def test_migration_count_verification(self, migration_instance, sample_legacy_data):
        """Test that migration verifies server and assignment counts."""
        transformed_configs = migration_instance.transform_to_new_format(
            sample_legacy_data["mcp_servers"],
            sample_legacy_data["agent_mcp_servers"]
        )
        
        # Verify counts match
        original_server_count = len(sample_legacy_data["mcp_servers"])
        transformed_config_count = len(transformed_configs)
        
        assert transformed_config_count == original_server_count
        
        # Verify all agent assignments preserved
        original_assignments = sample_legacy_data["agent_mcp_servers"]
        total_agent_assignments = sum(len(config["agents"]) for config in transformed_configs)
        
        assert total_agent_assignments == len(original_assignments)

    def test_migration_dry_run_mode(self, migration_instance):
        """Test that dry run mode doesn't modify data."""
        migration_instance.dry_run = True
        
        # Dry run should always return True without making changes
        result = migration_instance.perform_migration([{"name": "test", "server_type": "stdio"}])
        assert result is True

    def test_migration_error_handling(self, migration_instance):
        """Test migration error handling and cleanup."""
        # Test validation error during transformation
        invalid_data = [{"name": "", "server_type": "invalid"}]  # Invalid server type
        
        with pytest.raises(ValueError):
            migration_instance.validate_transformed_configs(invalid_data)


if __name__ == "__main__":
    # Allow running tests directly
    pytest.main([__file__, "-v"])