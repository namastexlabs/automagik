"""Tests for MCP API routes."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from automagik.main import app
from automagik.mcp.models import MCPServerStatus, MCPServerState
from automagik.mcp.exceptions import MCPError


class TestMCPRoutes:
    """Test cases for MCP API routes."""
    
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
    def mock_mcp_client_manager(self):
        """Mock MCP manager."""
        with patch('automagik.api.routes.mcp_routes.get_mcp_manager') as mock:
            manager = MagicMock()
            # Set up async methods as AsyncMock
            manager.add_server = AsyncMock()
            manager._save_server_config = AsyncMock()
            manager.get_health = AsyncMock()
            # Make get_mcp_manager return the manager when awaited
            mock.return_value = manager
            yield manager
    
    def test_mcp_health_endpoint(self, client, mock_mcp_client_manager):
        """Test MCP health endpoint."""
        # Setup mock
        mock_health = MagicMock()
        mock_health.status = "healthy"
        mock_health.servers_total = 2
        mock_health.servers_running = 1
        mock_health.servers_error = 0
        mock_health.tools_available = 5
        mock_health.resources_available = 3
        
        mock_mcp_client_manager.get_health.return_value = mock_health
        
        # Make request
        response = client.get("/api/v1/mcp/health")
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["servers_total"] == 2
        assert data["servers_running"] == 1
    
    def test_list_mcp_servers(self, client, auth_headers, mock_mcp_client_manager):
        """Test listing MCP servers."""
        # Setup mock - create a proper MCPServerState instance
        from automagik.mcp.models import MCPServerState
        mock_server_state = MCPServerState(
            name="filesystem",
            status=MCPServerStatus.RUNNING
        )

        # Make list_servers return a regular list (not a coroutine)
        mock_mcp_client_manager.list_servers = MagicMock(return_value=[mock_server_state])
        
        # Make request
        response = client.get("/api/v1/mcp/servers", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["servers"]) == 1
    
    def test_create_mcp_server(self, client, auth_headers, mock_mcp_client_manager):
        """Test creating an MCP server."""
        # Setup mock
        mock_server = MagicMock()
        mock_server.state = MCPServerState(
            name="test-server",
            status=MCPServerStatus.RUNNING,
            last_error=None,
            error_count=0,
            connection_attempts=0,
            tools_discovered=[],
            resources_discovered=[]
        )
        
        mock_mcp_client_manager.get_server.return_value = mock_server
        
        # Request data
        server_data = {
            "name": "test-server",
            "server_type": "stdio",
            "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
            "description": "Test filesystem server"
        }
        
        # Make request
        response = client.post("/api/v1/mcp/servers", json=server_data, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        mock_mcp_client_manager.add_server.assert_called_once()
    
    def test_configure_mcp_servers_bulk(self, client, auth_headers, mock_mcp_client_manager):
        """Test bulk configuration of MCP servers."""
        # Setup mock
        mock_server1 = MagicMock()
        mock_server1.state = MCPServerState(
            name="filesystem",
            status=MCPServerStatus.RUNNING,
            last_error=None,
            error_count=0,
            connection_attempts=0,
            tools_discovered=[],
            resources_discovered=[]
        )
        
        mock_server2 = MagicMock()
        mock_server2.state = MCPServerState(
            name="weather",
            status=MCPServerStatus.RUNNING,
            last_error=None,
            error_count=0,
            connection_attempts=0,
            tools_discovered=[],
            resources_discovered=[]
        )
        
        mock_mcp_client_manager.get_server.side_effect = [mock_server1, mock_server2]
        
        # Request data in the expected format
        config_data = {
            "mcpServers": {
                "filesystem": {
                    "command": "npx",
                    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
                },
                "weather": {
                    "command": "node",
                    "args": ["weather-server.js"],
                    "env": {"API_KEY": "test-key"}
                }
            }
        }
        
        # Make request
        response = client.post("/api/v1/mcp/configure", json=config_data, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["servers"]) == 2
        
        # Verify both servers were added
        assert mock_mcp_client_manager.add_server.call_count == 2
    
    def test_get_mcp_server(self, client, auth_headers, mock_mcp_client_manager):
        """Test getting a specific MCP server."""
        # Setup mock
        mock_server = MagicMock()
        mock_server.state = MCPServerState(
            name="filesystem",
            status=MCPServerStatus.RUNNING,
            last_error=None,
            error_count=0,
            connection_attempts=0,
            tools_discovered=[],
            resources_discovered=[]
        )
        
        mock_mcp_client_manager.get_server.return_value = mock_server
        
        # Make request
        response = client.get("/api/v1/mcp/servers/filesystem", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "filesystem"
        assert data["status"] == MCPServerStatus.RUNNING
    
    def test_get_mcp_server_not_found(self, client, auth_headers, mock_mcp_client_manager):
        """Test getting a non-existent MCP server."""
        # Setup mock
        mock_mcp_client_manager.get_server.return_value = None
        
        # Make request
        response = client.get("/api/v1/mcp/servers/nonexistent", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 404
    
    def test_update_mcp_server(self, client, auth_headers, mock_mcp_client_manager):
        """Test updating an MCP server."""
        # Setup mock
        mock_server = MagicMock()
        mock_server.state = MCPServerState(
            name="filesystem",
            status=MCPServerStatus.RUNNING,
            last_error=None,
            error_count=0,
            connection_attempts=0,
            tools_discovered=[],
            resources_discovered=[]
        )
        mock_server.config = MagicMock()
        mock_server.is_running = True
        mock_server.restart = AsyncMock()
        
        mock_mcp_client_manager.get_server.return_value = mock_server
        
        # Request data
        update_data = {
            "description": "Updated filesystem server",
            "auto_start": False
        }
        
        # Make request
        response = client.put("/api/v1/mcp/servers/filesystem", json=update_data, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        mock_server.restart.assert_called_once()
    
    def test_delete_mcp_server(self, client, auth_headers, mock_mcp_client_manager):
        """Test deleting an MCP server."""
        # Setup mock
        mock_mcp_client_manager.remove_server = AsyncMock()
        
        # Make request
        response = client.delete("/api/v1/mcp/servers/filesystem", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        mock_mcp_client_manager.remove_server.assert_called_once_with("filesystem")
    
    def test_start_mcp_server(self, client, auth_headers, mock_mcp_client_manager):
        """Test starting an MCP server."""
        # Setup mock
        mock_mcp_client_manager.start_server = AsyncMock()
        
        # Make request
        response = client.post("/api/v1/mcp/servers/filesystem/start", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        mock_mcp_client_manager.start_server.assert_called_once_with("filesystem")
    
    def test_stop_mcp_server(self, client, auth_headers, mock_mcp_client_manager):
        """Test stopping an MCP server."""
        # Setup mock
        mock_mcp_client_manager.stop_server = AsyncMock()
        
        # Make request
        response = client.post("/api/v1/mcp/servers/filesystem/stop", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        mock_mcp_client_manager.stop_server.assert_called_once_with("filesystem")
    
    def test_restart_mcp_server(self, client, auth_headers, mock_mcp_client_manager):
        """Test restarting an MCP server."""
        # Setup mock
        mock_mcp_client_manager.restart_server = AsyncMock()
        
        # Make request
        response = client.post("/api/v1/mcp/servers/filesystem/restart", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        mock_mcp_client_manager.restart_server.assert_called_once_with("filesystem")
    
    def test_call_mcp_tool(self, client, auth_headers, mock_mcp_client_manager):
        """Test calling an MCP tool."""
        # Setup mock
        mock_result = {"files": ["file1.txt", "file2.txt"]}
        mock_mcp_client_manager.call_tool = AsyncMock(return_value=mock_result)
        
        # Request data
        tool_request = {
            "server_name": "filesystem",
            "tool_name": "list_files",
            "arguments": {"path": "/tmp"}
        }
        
        # Make request
        response = client.post("/api/v1/mcp/tools/call", json=tool_request, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["result"] == mock_result
        assert data["tool_name"] == "list_files"
        assert data["server_name"] == "filesystem"
    
    def test_call_mcp_tool_error(self, client, auth_headers, mock_mcp_client_manager):
        """Test calling an MCP tool that fails."""
        # Setup mock
        mock_mcp_client_manager.call_tool = AsyncMock(side_effect=MCPError("Tool not found"))
        
        # Request data
        tool_request = {
            "server_name": "filesystem",
            "tool_name": "nonexistent_tool",
            "arguments": {}
        }
        
        # Make request
        response = client.post("/api/v1/mcp/tools/call", json=tool_request, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Tool not found" in data["error"]
    
    def test_access_mcp_resource(self, client, auth_headers, mock_mcp_client_manager):
        """Test accessing an MCP resource."""
        # Setup mock
        mock_content = "File content here"
        mock_mcp_client_manager.access_resource = AsyncMock(return_value=mock_content)
        
        # Request data
        resource_request = {
            "server_name": "filesystem",
            "uri": "file:///tmp/test.txt"
        }
        
        # Make request
        response = client.post("/api/v1/mcp/resources/access", json=resource_request, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["content"] == mock_content
        assert data["uri"] == "file:///tmp/test.txt"
        assert data["server_name"] == "filesystem"
    
    def test_list_server_tools(self, client, auth_headers, mock_mcp_client_manager):
        """Test listing tools for a specific server."""
        # Setup mock
        mock_tool = MagicMock()
        mock_tool.name = "list_files"
        mock_tool.description = "List files in directory"
        
        mock_server = MagicMock()
        mock_server.tools = [mock_tool]
        
        mock_mcp_client_manager.get_server.return_value = mock_server
        
        # Make request
        response = client.get("/api/v1/mcp/servers/filesystem/tools", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["server_name"] == "filesystem"
        assert data["total"] == 1
        assert len(data["tools"]) == 1
    
    def test_list_server_resources(self, client, auth_headers, mock_mcp_client_manager):
        """Test listing resources for a specific server."""
        # Setup mock
        mock_resource = MagicMock()
        mock_resource.uri = "file:///tmp/test.txt"
        mock_resource.name = "test.txt"
        
        mock_server = MagicMock()
        mock_server.resources = [mock_resource]
        
        mock_mcp_client_manager.get_server.return_value = mock_server
        
        # Make request
        response = client.get("/api/v1/mcp/servers/filesystem/resources", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["server_name"] == "filesystem"
        assert data["total"] == 1
        assert len(data["resources"]) == 1
    
    def test_list_agent_mcp_tools(self, client, auth_headers, mock_mcp_client_manager):
        """Test listing MCP tools available to an agent."""
        # Setup mock
        mock_tool = MagicMock()
        mock_tool.name = "list_files"
        mock_tool.description = "List files in directory"
        mock_tool.input_schema = {"type": "object"}
        mock_tool.output_schema = {"type": "array"}
        
        mock_server = MagicMock()
        mock_server.name = "filesystem"
        mock_server.is_running = True
        mock_server.tools = [mock_tool]
        
        mock_mcp_client_manager.get_servers_for_agent.return_value = [mock_server]
        
        # Make request
        response = client.get("/api/v1/mcp/agents/simple/tools", headers=auth_headers)
        
        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert data["agent_name"] == "simple"
        assert data["total"] == 1
        assert len(data["tools"]) == 1
        assert len(data["servers"]) == 1
        assert data["servers"][0] == "filesystem"
    
    def test_authentication_required(self, client):
        """Test that authentication is required for protected endpoints."""
        # Make request without auth header
        response = client.get("/api/v1/mcp/servers")
        
        # Assert response
        assert response.status_code == 401
    
    def test_invalid_server_type(self, client, auth_headers, mock_mcp_client_manager):
        """Test creating server with invalid type."""
        # Request data with invalid server type
        server_data = {
            "name": "test-server",
            "server_type": "invalid",
            "command": ["echo", "hello"]
        }
        
        # Make request
        response = client.post("/api/v1/mcp/servers", json=server_data, headers=auth_headers)
        
        # Assert response
        assert response.status_code == 422  # Validation error