"""Tests for the new streamlined MCP API routes."""

import pytest
import uuid
from datetime import datetime
from unittest.mock import patch
from fastapi.testclient import TestClient

from src.main import app
from src.db.models import MCPConfig


class TestStreamlinedMCPRoutes:
    """Test cases for the new streamlined MCP API routes."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for API calls."""
        from src.config import settings
        return {"x-api-key": settings.AM_API_KEY}
    
    @pytest.fixture
    def sample_config(self):
        """Sample MCP configuration for testing."""
        return {
            "name": "test-server",
            "server_type": "stdio",
            "command": ["python", "-m", "test_server"],
            "agents": ["simple"],
            "tools": {"include": ["*"]},
            "environment": {"DEBUG": "true"},
            "timeout": 30000,
            "retry_count": 3,
            "enabled": True,
            "auto_start": True
        }
    
    @pytest.fixture
    def sample_mcp_config(self):
        """Sample MCPConfig object for testing."""
        return MCPConfig(
            id=uuid.uuid4(),
            name="test-server",
            config={
                "name": "test-server",
                "server_type": "stdio",
                "command": ["python", "-m", "test_server"],
                "agents": ["simple"],
                "tools": {"include": ["*"]},
                "environment": {"DEBUG": "true"},
                "timeout": 30000,
                "retry_count": 3,
                "enabled": True,
                "auto_start": True
            },
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
    
    # Test GET /configs
    @patch('src.api.routes.mcp_routes.list_mcp_configs')
    def test_list_configs_success(self, mock_list, client, auth_headers, sample_mcp_config):
        """Test successful listing of MCP configurations."""
        # Setup mock
        mock_list.return_value = [sample_mcp_config]
        
        # Make request
        response = client.get("/api/v1/mcp/configs", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["configs"]) == 1
        assert data["configs"][0]["name"] == "test-server"
        assert data["filtered_by_agent"] is None
        
        mock_list.assert_called_once_with(enabled_only=True, agent_name=None)
    
    @patch('src.api.routes.mcp_routes.list_mcp_configs')
    def test_list_configs_with_agent_filter(self, mock_list, client, auth_headers, sample_mcp_config):
        """Test listing configs filtered by agent."""
        # Setup mock
        mock_list.return_value = [sample_mcp_config]
        
        # Make request with agent filter
        response = client.get("/api/v1/mcp/configs?agent_name=simple&enabled_only=false", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["filtered_by_agent"] == "simple"
        
        mock_list.assert_called_once_with(enabled_only=False, agent_name="simple")
    
    @patch('src.api.routes.mcp_routes.list_mcp_configs')
    def test_list_configs_empty(self, mock_list, client, auth_headers):
        """Test listing configs with no results."""
        # Setup mock
        mock_list.return_value = []
        
        # Make request
        response = client.get("/api/v1/mcp/configs", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["configs"]) == 0
    
    # Test POST /configs
    @patch('src.api.routes.mcp_routes.get_mcp_config_by_name')
    @patch('src.api.routes.mcp_routes.create_mcp_config')
    def test_create_config_success(self, mock_create, mock_get_by_name, client, auth_headers, sample_config, sample_mcp_config):
        """Test successful creation of MCP configuration."""
        # Setup mocks
        mock_get_by_name.side_effect = [None, sample_mcp_config]  # Not exists, then exists after creation
        mock_create.return_value = str(sample_mcp_config.id)
        
        # Make request
        response = client.post("/api/v1/mcp/configs", json=sample_config, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test-server"
        assert data["config"]["server_type"] == "stdio"
        
        mock_create.assert_called_once()
        assert mock_get_by_name.call_count == 2  # Check if exists, then get after creation
    
    @patch('src.api.routes.mcp_routes.get_mcp_config_by_name')
    def test_create_config_already_exists(self, mock_get_by_name, client, auth_headers, sample_config, sample_mcp_config):
        """Test creating config that already exists."""
        # Setup mock
        mock_get_by_name.return_value = sample_mcp_config
        
        # Make request
        response = client.post("/api/v1/mcp/configs", json=sample_config, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 409
        data = response.json()
        assert "already exists" in data["detail"]
    
    def test_create_config_invalid_server_type(self, client, auth_headers, sample_config):
        """Test creating config with invalid server type."""
        # Modify config to have invalid server type
        sample_config["server_type"] = "invalid"
        
        # Make request
        response = client.post("/api/v1/mcp/configs", json=sample_config, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 400
        data = response.json()
        assert "server_type must be" in data["detail"]
    
    def test_create_config_stdio_missing_command(self, client, auth_headers, sample_config):
        """Test creating stdio config without command."""
        # Remove command from config
        del sample_config["command"]
        
        # Make request
        response = client.post("/api/v1/mcp/configs", json=sample_config, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 400
        data = response.json()
        assert "command is required" in data["detail"]
    
    def test_create_config_http_missing_url(self, client, auth_headers, sample_config):
        """Test creating http config without URL."""
        # Change to http type without URL
        sample_config["server_type"] = "http"
        del sample_config["command"]
        
        # Make request
        response = client.post("/api/v1/mcp/configs", json=sample_config, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 400
        data = response.json()
        assert "url is required" in data["detail"]
    
    def test_create_config_empty_agents(self, client, auth_headers, sample_config):
        """Test creating config with empty agents list."""
        # Set empty agents list
        sample_config["agents"] = []
        
        # Make request
        response = client.post("/api/v1/mcp/configs", json=sample_config, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 400
        data = response.json()
        assert "agents list cannot be empty" in data["detail"]
    
    def test_create_config_low_timeout(self, client, auth_headers, sample_config):
        """Test creating config with too low timeout."""
        # Set very low timeout
        sample_config["timeout"] = 500
        
        # Make request
        response = client.post("/api/v1/mcp/configs", json=sample_config, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 400
        data = response.json()
        assert "timeout must be at least 1000ms" in data["detail"]
    
    # Test PUT /configs/{name}
    @patch('src.api.routes.mcp_routes.get_mcp_config_by_name')
    @patch('src.api.routes.mcp_routes.update_mcp_config_by_name')
    def test_update_config_success(self, mock_update, mock_get_by_name, client, auth_headers, sample_config, sample_mcp_config):
        """Test successful update of MCP configuration."""
        # Setup mocks
        updated_config = sample_mcp_config.model_copy()
        updated_config.config["timeout"] = 45000
        mock_get_by_name.side_effect = [sample_mcp_config, updated_config]  # Exists check, then get after update
        mock_update.return_value = True
        
        # Modify config for update
        sample_config["timeout"] = 45000
        
        # Make request
        response = client.put("/api/v1/mcp/configs/test-server", json=sample_config, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test-server"
        
        mock_update.assert_called_once()
        assert mock_get_by_name.call_count == 2
    
    @patch('src.api.routes.mcp_routes.get_mcp_config_by_name')
    def test_update_config_not_found(self, mock_get_by_name, client, auth_headers, sample_config):
        """Test updating non-existent config."""
        # Setup mock
        mock_get_by_name.return_value = None
        
        # Make request
        response = client.put("/api/v1/mcp/configs/nonexistent", json=sample_config, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    @patch('src.api.routes.mcp_routes.get_mcp_config_by_name')
    def test_update_config_name_mismatch(self, mock_get_by_name, client, auth_headers, sample_config, sample_mcp_config):
        """Test updating config with mismatched name."""
        # Setup mock
        mock_get_by_name.return_value = sample_mcp_config
        
        # Change name in config (should fail)
        sample_config["name"] = "different-name"
        
        # Make request
        response = client.put("/api/v1/mcp/configs/test-server", json=sample_config, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 400
        data = response.json()
        assert "Cannot change configuration name" in data["detail"]
    
    # Test DELETE /configs/{name}
    @patch('src.api.routes.mcp_routes.get_mcp_config_by_name')
    @patch('src.api.routes.mcp_routes.delete_mcp_config_by_name')
    def test_delete_config_success(self, mock_delete, mock_get_by_name, client, auth_headers, sample_mcp_config):
        """Test successful deletion of MCP configuration."""
        # Setup mocks
        mock_get_by_name.return_value = sample_mcp_config
        mock_delete.return_value = True
        
        # Make request
        response = client.delete("/api/v1/mcp/configs/test-server", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 204
        assert response.content == b""  # No content for 204
        
        mock_delete.assert_called_once_with("test-server")
    
    @patch('src.api.routes.mcp_routes.get_mcp_config_by_name')
    def test_delete_config_not_found(self, mock_get_by_name, client, auth_headers):
        """Test deleting non-existent config."""
        # Setup mock
        mock_get_by_name.return_value = None
        
        # Make request
        response = client.delete("/api/v1/mcp/configs/nonexistent", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    @patch('src.api.routes.mcp_routes.get_mcp_config_by_name')
    @patch('src.api.routes.mcp_routes.delete_mcp_config_by_name')
    def test_delete_config_db_error(self, mock_delete, mock_get_by_name, client, auth_headers, sample_mcp_config):
        """Test deletion with database error."""
        # Setup mocks
        mock_get_by_name.return_value = sample_mcp_config
        mock_delete.return_value = False  # Database operation failed
        
        # Make request
        response = client.delete("/api/v1/mcp/configs/test-server", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 500
        data = response.json()
        assert "Failed to delete" in data["detail"]
    
    # Test authentication
    def test_authentication_required_list(self, client):
        """Test that authentication is required for listing configs."""
        # Make request without auth header
        response = client.get("/api/v1/mcp/configs")
        
        # Assert response
        assert response.status_code == 401
    
    def test_authentication_required_create(self, client, sample_config):
        """Test that authentication is required for creating configs."""
        # Make request without auth header
        response = client.post("/api/v1/mcp/configs", json=sample_config)
        
        # Assert response
        assert response.status_code == 401
    
    def test_authentication_required_update(self, client, sample_config):
        """Test that authentication is required for updating configs."""
        # Make request without auth header
        response = client.put("/api/v1/mcp/configs/test-server", json=sample_config)
        
        # Assert response
        assert response.status_code == 401
    
    def test_authentication_required_delete(self, client):
        """Test that authentication is required for deleting configs."""
        # Make request without auth header
        response = client.delete("/api/v1/mcp/configs/test-server")
        
        # Assert response
        assert response.status_code == 401