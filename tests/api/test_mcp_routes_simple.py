"""Simplified tests for the new streamlined MCP API routes."""

import pytest
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from automagik.main import app


class TestStreamlinedMCPRoutesSimple:
    """Test cases for the new streamlined MCP API routes."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers for API calls."""
        from automagik.config import settings
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
    
    # Test GET /configs
    @patch('automagik.api.routes.mcp_routes.list_mcp_configs')
    def test_list_configs_success(self, mock_list, client, auth_headers):
        """Test successful listing of MCP configurations."""
        # Setup mock with minimal data structure
        mock_config = MagicMock()
        mock_config.id = uuid.uuid4()
        mock_config.name = "test-server"
        mock_config.config = {"server_type": "stdio"}
        mock_config.created_at = datetime.now()
        mock_config.updated_at = datetime.now()
        mock_list.return_value = [mock_config]
        
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
    
    @patch('automagik.api.routes.mcp_routes.list_mcp_configs')
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
    
    # Test validation
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