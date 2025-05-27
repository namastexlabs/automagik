"""Integration tests for MCP system."""

import pytest
import httpx
import uuid
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
    
    @pytest.fixture
    def unique_server_name(self):
        """Generate unique server name for each test."""
        return f"test_server_{uuid.uuid4().hex[:8]}"
    
    @pytest.fixture
    def cleanup_servers(self):
        """Cleanup fixture to collect test servers for removal after each test."""
        created_servers = []
        return created_servers
    
    @pytest.mark.asyncio
    async def test_configure_filesystem_server(self, base_url, auth_headers, unique_server_name, cleanup_servers):
        """Test configuring a filesystem MCP server using the expected JSON format."""
        async with httpx.AsyncClient() as client:
            try:
                # Configure filesystem server with unique name
                config_data = {
                    "mcpServers": {
                        unique_server_name: {
                            "command": "npx",
                            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                            "description": "Filesystem MCP server for testing"
                        }
                    }
                }
                
                cleanup_servers.append(unique_server_name)
                
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
                assert data["servers"][0]["name"] == unique_server_name
                
            finally:
                # Cleanup - remove the server
                try:
                    await client.delete(
                        f"{base_url}/api/v1/mcp/servers/{unique_server_name}",
                        headers=auth_headers
                    )
                except Exception:
                    # Ignore cleanup errors
                    pass
    
    @pytest.mark.asyncio
    async def test_server_lifecycle_operations(self, base_url, auth_headers, unique_server_name, cleanup_servers):
        """Test MCP server lifecycle operations."""
        async with httpx.AsyncClient() as client:
            try:
                # First configure a server
                config_data = {
                    "mcpServers": {
                        unique_server_name: {
                            "command": "npx",
                            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                            "auto_start": False
                        }
                    }
                }
                
                cleanup_servers.append(unique_server_name)
                
                await client.post(
                    f"{base_url}/api/v1/mcp/configure",
                    json=config_data,
                    headers=auth_headers
                )
                
                # Test start server
                response = await client.post(
                    f"{base_url}/api/v1/mcp/servers/{unique_server_name}/start",
                    headers=auth_headers
                )
                assert response.status_code == 200
                
                # Test stop server
                response = await client.post(
                    f"{base_url}/api/v1/mcp/servers/{unique_server_name}/stop",
                    headers=auth_headers
                )
                assert response.status_code == 200
                
                # Test restart server
                response = await client.post(
                    f"{base_url}/api/v1/mcp/servers/{unique_server_name}/restart",
                    headers=auth_headers
                )
                assert response.status_code == 200
                
            finally:
                # Cleanup - remove the server
                try:
                    await client.delete(
                        f"{base_url}/api/v1/mcp/servers/{unique_server_name}",
                        headers=auth_headers
                    )
                except Exception:
                    # Ignore cleanup errors
                    pass
    
    @pytest.mark.asyncio
    async def test_server_tool_discovery(self, base_url, auth_headers, unique_server_name, cleanup_servers):
        """Test tool discovery for MCP servers."""
        async with httpx.AsyncClient() as client:
            try:
                # Configure filesystem server
                config_data = {
                    "mcpServers": {
                        unique_server_name: {
                            "command": "npx",
                            "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
                        }
                    }
                }
                
                cleanup_servers.append(unique_server_name)
                
                await client.post(
                    f"{base_url}/api/v1/mcp/configure",
                    json=config_data,
                    headers=auth_headers
                )
                
                # List tools for the server
                response = await client.get(
                    f"{base_url}/api/v1/mcp/servers/{unique_server_name}/tools",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["server_name"] == unique_server_name
                assert "tools" in data
                assert "total" in data
                
            finally:
                # Cleanup - remove the server
                try:
                    await client.delete(
                        f"{base_url}/api/v1/mcp/servers/{unique_server_name}",
                        headers=auth_headers
                    )
                except Exception:
                    # Ignore cleanup errors
                    pass
    
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
            # Configure multiple servers (using proper MCP servers)
            config_data = {
                "mcpServers": {
                    "filesystem": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                        "description": "Filesystem server"
                    },
                    "filesystem2": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/var/tmp"],
                        "description": "Second filesystem server"
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
            assert "filesystem2" in server_names
    
    @pytest.mark.asyncio
    async def test_server_crud_operations(self, base_url, auth_headers):
        """Test CRUD operations for MCP servers."""
        async with httpx.AsyncClient() as client:
            # Create server
            server_data = {
                "name": "test_crud_server",
                "server_type": "stdio",
                "command": ["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
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
                # Add a filesystem server with unique name
                unique_name = f"test_fs_{uuid.uuid4().hex[:8]}"
                config = MCPServerConfig(
                    name=unique_name,
                    server_type=MCPServerType.STDIO,
                    command=["npx", "-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
                    description="Test filesystem server",
                    auto_start=True
                )
                
                await manager.add_server(config)
                
                # Verify server was added
                servers = manager.list_servers()
                assert len(servers) == 1
                assert servers[0].name == unique_name
                
                # Test server operations
                await manager.start_server(unique_name)
                await manager.stop_server(unique_name)
                await manager.restart_server(unique_name)
                
                # Test tool operations (mocked)
                result = await manager.call_tool(unique_name, "test_tool", {})
                assert result == {"result": "success"}
                
                # Test resource operations (mocked)
                content = await manager.access_resource(unique_name, "test://resource")
                assert content == "resource content"
                
                # Get health status
                health = await manager.get_health()
                assert health.servers_total == 1
                
                # Clean up
                await manager.remove_server(unique_name)
                assert len(manager.list_servers()) == 0
                
            finally:
                await manager.shutdown()