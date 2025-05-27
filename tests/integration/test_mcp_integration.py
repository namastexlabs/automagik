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
        return {"X-API-Key": settings.AM_API_KEY}
    
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
    async def test_configure_calculator_server(self, base_url, auth_headers, unique_server_name, cleanup_servers):
        """Test configuring a calculator MCP server using the expected JSON format."""
        async with httpx.AsyncClient() as client:
            try:
                # Configure calculator server with unique name
                config_data = {
                    "mcpServers": {
                        unique_server_name: {
                            "command": "uvx",
                            "args": ["mcp-server-calculator"],
                            "description": "Calculator MCP server for testing"
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
                            "command": "uvx",
                            "args": ["mcp-server-calculator"],
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
                # Configure calculator server
                config_data = {
                    "mcpServers": {
                        unique_server_name: {
                            "command": "uvx",
                            "args": ["mcp-server-calculator"]
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
            # Use unique server name to avoid conflicts with other tests
            unique_name = f"calculator_{uuid.uuid4().hex[:8]}"
            
            try:
                # Configure calculator server assigned to simple_agent
                config_data = {
                    "mcpServers": {
                        unique_name: {
                            "command": "uvx",
                            "args": ["mcp-server-calculator"],
                            "agent_names": ["simple"]
                        }
                    }
                }
                
                config_response = await client.post(
                    f"{base_url}/api/v1/mcp/configure",
                    json=config_data,
                    headers=auth_headers
                )
                assert config_response.status_code == 200
                
                # Give server a moment to start
                import asyncio
                await asyncio.sleep(1)
                
                # List MCP tools available to the agent
                response = await client.get(
                    f"{base_url}/api/v1/mcp/agents/simple/tools",
                    headers=auth_headers
                )
                
                assert response.status_code == 200
                data = response.json()
                assert data["agent_name"] == "simple"
                assert unique_name in data["servers"]
                assert data["total"] >= 1  # Should have at least 1 tool
                
                # Verify tools are discovered
                assert len(data["tools"]) >= 1
                # Calculator server should have at least one calculate tool
                tool_names = [tool["tool_name"] for tool in data["tools"]]
                assert "calculate" in tool_names
                
            finally:
                # Cleanup - remove the server
                try:
                    await client.delete(
                        f"{base_url}/api/v1/mcp/servers/{unique_name}",
                        headers=auth_headers
                    )
                except Exception:
                    # Ignore cleanup errors
                    pass
    
    @pytest.mark.asyncio
    async def test_call_mcp_tool(self, base_url, auth_headers):
        """Test calling an MCP tool."""
        async with httpx.AsyncClient() as client:
            # Configure calculator server
            config_data = {
                "mcpServers": {
                    "calculator": {
                        "command": "uvx",
                        "args": ["mcp-server-calculator"]
                    }
                }
            }
            
            await client.post(
                f"{base_url}/api/v1/mcp/configure",
                json=config_data,
                headers=auth_headers
            )
            
            # Call a calculator tool
            tool_request = {
                "server_name": "calculator",
                "tool_name": "add",
                "arguments": {"a": 5, "b": 3}
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
            assert data["tool_name"] == "add"
            assert data["server_name"] == "calculator"
    
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
            # Configure multiple servers (using calculator servers)
            config_data = {
                "mcpServers": {
                    "calculator1": {
                        "command": "uvx",
                        "args": ["mcp-server-calculator"],
                        "description": "Calculator server 1"
                    },
                    "calculator2": {
                        "command": "uvx",
                        "args": ["mcp-server-calculator"],
                        "description": "Calculator server 2"
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
            assert "calculator1" in server_names
            assert "calculator2" in server_names
    
    @pytest.mark.asyncio
    async def test_server_crud_operations(self, base_url, auth_headers):
        """Test CRUD operations for MCP servers."""
        async with httpx.AsyncClient() as client:
            # Create server
            server_data = {
                "name": "test_crud_server",
                "server_type": "stdio",
                "command": ["uvx", "mcp-server-calculator"],
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
@pytest.mark.skip(reason="Mock test causing conflicts with real MCP functionality - real functionality tested by other integration tests")
async def test_mcp_system_end_to_end():
    """End-to-end test of the complete MCP system functionality."""
    
    # Mock the MCPServerManager class entirely for isolated testing
    with patch('src.mcp.client.MCPClientManager._load_server_configurations') as mock_load:
        with patch('src.mcp.server.MCPServerManager') as mock_server_manager:
            # Mock database loading to return empty (isolated test)
            mock_load.return_value = None
            
            # Setup mock MCPServerManager instance
            mock_server_instance = AsyncMock()
            mock_server_instance.name = "test_calc_12345678"
            mock_server_instance.is_running = True
            mock_server_instance.status = None  # Will use enum later
            mock_server_instance.config = AsyncMock()
            mock_server_instance.state = AsyncMock() 
            mock_server_instance.tools = [{"name": "test_tool", "description": "Test tool"}]
            mock_server_instance.resources = []
            
            # Mock server operations
            mock_server_instance.start = AsyncMock()
            mock_server_instance.stop = AsyncMock()
            mock_server_instance.restart = AsyncMock()
            mock_server_instance.call_tool = AsyncMock(return_value={"result": "success"})
            mock_server_instance.access_resource = AsyncMock(return_value="resource content")
            mock_server_instance.get_pydantic_tools = AsyncMock(return_value=[])
            
            # Make the mock class return our mock instance
            mock_server_manager.return_value = mock_server_instance
            
            # Import after mocking
            from src.mcp.client import MCPClientManager
            from src.mcp.models import MCPServerConfig, MCPServerType, MCPServerStatus
            
            # Set up the mock status after importing the enum
            mock_server_instance.status = MCPServerStatus.RUNNING
            
            # Test complete workflow with isolated manager
            manager = MCPClientManager()
            await manager.initialize()
            
            try:
                # Verify manager starts empty (no existing servers loaded)
                initial_servers = manager.list_servers()
                assert len(initial_servers) == 0, f"Expected empty manager but found {len(initial_servers)} servers"
                
                # Add a calculator server with unique name
                unique_name = f"test_calc_{uuid.uuid4().hex[:8]}"
                config = MCPServerConfig(
                    name=unique_name,
                    server_type=MCPServerType.STDIO,
                    command=["uvx", "mcp-server-calculator"],
                    description="Test calculator server",
                    auto_start=True
                )
                
                # Update mock instance name to match
                mock_server_instance.name = unique_name
                
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