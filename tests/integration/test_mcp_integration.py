"""Integration tests for MCP system."""

import pytest
import httpx
from unittest.mock import patch, AsyncMock

from src.config import settings


class TestMCPIntegration:
    """Integration tests for MCP system end-to-end functionality."""
    
    @pytest.fixture
    def base_url(self):
        """Base URL for API calls."""
        return f"http://localhost:{settings.AM_PORT}"
    
    @pytest.fixture
    def auth_headers(self):
        """Authentication headers."""
        return {"X-API-Key": "am-xxxxx"}
    
    @pytest.mark.asyncio
    async def test_configure_filesystem_server(self, base_url, auth_headers):
        """Test configuring a filesystem MCP server using the expected JSON format."""
        async with httpx.AsyncClient() as client:
            # Configure filesystem server
            config_data = {
                "mcpServers": {
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                        "description": "Filesystem MCP server for testing"
                    }
                }
            }
            
            response = await client.post(
                f"{base_url}/api/v1/mcp/configure",
                json=config_data,
                headers=auth_headers
            )
            
            # Debug output
            print(f"Response status: {response.status_code}")
            print(f"Response content: {response.text}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 1
            assert len(data["servers"]) == 1
            assert data["servers"][0]["name"] == "filesystem"
    
    @pytest.mark.asyncio
    async def test_server_lifecycle_operations(self, base_url, auth_headers):
        """Test MCP server lifecycle operations."""
        async with httpx.AsyncClient() as client:
            # First configure a server
            config_data = {
                "mcpServers": {
                    "test_server": {
                        "command": "echo",
                        "args": ["hello"],
                        "auto_start": False
                    }
                }
            }
            
            await client.post(
                f"{base_url}/api/v1/mcp/configure",
                json=config_data,
                headers=auth_headers
            )
            
            # Test start server
            response = await client.post(
                f"{base_url}/api/v1/mcp/servers/test_server/start",
                headers=auth_headers
            )
            assert response.status_code == 200
            
            # Test stop server
            response = await client.post(
                f"{base_url}/api/v1/mcp/servers/test_server/stop",
                headers=auth_headers
            )
            assert response.status_code == 200
            
            # Test restart server
            response = await client.post(
                f"{base_url}/api/v1/mcp/servers/test_server/restart",
                headers=auth_headers
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_server_tool_discovery(self, base_url, auth_headers):
        """Test tool discovery for MCP servers."""
        async with httpx.AsyncClient() as client:
            # Configure filesystem server
            config_data = {
                "mcpServers": {
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
                    }
                }
            }
            
            await client.post(
                f"{base_url}/api/v1/mcp/configure",
                json=config_data,
                headers=auth_headers
            )
            
            # List tools for the server
            response = await client.get(
                f"{base_url}/api/v1/mcp/servers/filesystem/tools",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["server_name"] == "filesystem"
            assert "tools" in data
            assert "total" in data
    
    @pytest.mark.asyncio
    async def test_agent_mcp_tool_integration(self, base_url, auth_headers):
        """Test agent integration with MCP tools."""
        async with httpx.AsyncClient() as client:
            # Configure filesystem server assigned to simple_agent
            config_data = {
                "mcpServers": {
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                        "agent_names": ["simple"]
                    }
                }
            }
            
            await client.post(
                f"{base_url}/api/v1/mcp/configure",
                json=config_data,
                headers=auth_headers
            )
            
            # List MCP tools available to the agent
            response = await client.get(
                f"{base_url}/api/v1/mcp/agents/simple/tools",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["agent_name"] == "simple"
            assert "filesystem" in data["servers"]
    
    @pytest.mark.asyncio
    async def test_call_mcp_tool(self, base_url, auth_headers):
        """Test calling an MCP tool."""
        async with httpx.AsyncClient() as client:
            # Configure filesystem server
            config_data = {
                "mcpServers": {
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
                    }
                }
            }
            
            await client.post(
                f"{base_url}/api/v1/mcp/configure",
                json=config_data,
                headers=auth_headers
            )
            
            # Call a filesystem tool
            tool_request = {
                "server_name": "filesystem",
                "tool_name": "list_files",
                "arguments": {"path": "/tmp"}
            }
            
            response = await client.post(
                f"{base_url}/api/v1/mcp/tools/call",
                json=tool_request,
                headers=auth_headers
            )
            
            # Should return success or specific error about missing server
            assert response.status_code == 200
            data = response.json()
            assert "success" in data
            assert data["tool_name"] == "list_files"
            assert data["server_name"] == "filesystem"
    
    @pytest.mark.asyncio
    async def test_mcp_health_check(self, base_url):
        """Test MCP health check endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/api/v1/mcp/health")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "servers_total" in data
            assert "servers_running" in data
            assert "tools_available" in data
    
    @pytest.mark.asyncio
    async def test_bulk_server_configuration(self, base_url, auth_headers):
        """Test configuring multiple servers at once."""
        async with httpx.AsyncClient() as client:
            # Configure multiple servers
            config_data = {
                "mcpServers": {
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                        "description": "Filesystem server"
                    },
                    "echo_server": {
                        "command": "echo",
                        "args": ["hello"],
                        "description": "Simple echo server"
                    }
                }
            }
            
            response = await client.post(
                f"{base_url}/api/v1/mcp/configure",
                json=config_data,
                headers=auth_headers
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["servers"]) == 2
            
            server_names = [server["name"] for server in data["servers"]]
            assert "filesystem" in server_names
            assert "echo_server" in server_names
    
    @pytest.mark.asyncio
    async def test_server_crud_operations(self, base_url, auth_headers):
        """Test CRUD operations for MCP servers."""
        async with httpx.AsyncClient() as client:
            # Create server
            server_data = {
                "name": "test_crud_server",
                "server_type": "stdio",
                "command": ["echo", "test"],
                "description": "Test CRUD server"
            }
            
            response = await client.post(
                f"{base_url}/api/v1/mcp/servers",
                json=server_data,
                headers=auth_headers
            )
            assert response.status_code == 200
            
            # Read server
            response = await client.get(
                f"{base_url}/api/v1/mcp/servers/test_crud_server",
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "test_crud_server"
            
            # Update server
            update_data = {
                "description": "Updated CRUD server"
            }
            response = await client.put(
                f"{base_url}/api/v1/mcp/servers/test_crud_server",
                json=update_data,
                headers=auth_headers
            )
            assert response.status_code == 200
            
            # Delete server
            response = await client.delete(
                f"{base_url}/api/v1/mcp/servers/test_crud_server",
                headers=auth_headers
            )
            assert response.status_code == 200
            
            # Verify deletion
            response = await client.get(
                f"{base_url}/api/v1/mcp/servers/test_crud_server",
                headers=auth_headers
            )
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_mcp_system_end_to_end():
    """End-to-end test of the complete MCP system functionality."""
    
    # Mock the actual MCP server components for testing
    with patch('src.mcp.server.MCPServerStdio') as mock_stdio:
        with patch('src.mcp.server.MCPServerHTTP') as mock_http:
            # Setup mock MCP server
            mock_server_instance = AsyncMock()
            mock_server_instance.start = AsyncMock()
            mock_server_instance.close = AsyncMock()
            mock_server_instance.list_tools = AsyncMock(return_value=[])
            mock_server_instance.list_resources = AsyncMock(return_value=[])
            mock_server_instance.call_tool = AsyncMock(return_value={"result": "success"})
            mock_server_instance.read_resource = AsyncMock(return_value="resource content")
            
            mock_stdio.return_value = mock_server_instance
            mock_http.return_value = mock_server_instance
            
            # Import after mocking
            from src.mcp.client import MCPClientManager
            from src.mcp.models import MCPServerConfig, MCPServerType
            
            # Test complete workflow
            manager = MCPClientManager()
            await manager.initialize()
            
            try:
                # Add a filesystem server
                config = MCPServerConfig(
                    name="test_filesystem",
                    server_type=MCPServerType.STDIO,
                    command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    description="Test filesystem server",
                    auto_start=True
                )
                
                await manager.add_server(config)
                
                # Verify server was added
                servers = manager.list_servers()
                assert len(servers) == 1
                assert servers[0].name == "test_filesystem"
                
                # Test server operations
                await manager.start_server("test_filesystem")
                await manager.stop_server("test_filesystem")
                await manager.restart_server("test_filesystem")
                
                # Test tool operations (mocked)
                result = await manager.call_tool("test_filesystem", "test_tool", {})
                assert result == {"result": "success"}
                
                # Test resource operations (mocked)
                content = await manager.access_resource("test_filesystem", "test://resource")
                assert content == "resource content"
                
                # Get health status
                health = await manager.get_health()
                assert health.servers_total == 1
                
                # Clean up
                await manager.remove_server("test_filesystem")
                assert len(manager.list_servers()) == 0
                
            finally:
                await manager.shutdown()