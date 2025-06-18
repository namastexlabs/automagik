"""Tests for tool management API routes."""

import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from src.main import app
from src.config import settings


@pytest.fixture
def client():
    """Create a test client with API key authentication."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Authentication headers for API requests."""
    return {"x-api-key": settings.AM_API_KEY}


class TestToolRoutes:
    """Test cases for tool management endpoints."""
    
    def test_list_tools_empty(self, client, auth_headers):
        """Test listing tools when none exist."""
        with patch('src.api.routes.tool_routes.db_list_tools') as mock_list:
            mock_list.return_value = []
            
            with patch('src.api.routes.tool_routes.get_tool_categories') as mock_categories:
                mock_categories.return_value = []
                
                response = client.get("/tools/", headers=auth_headers)
                assert response.status_code == 200
                
                data = response.json()
                assert data["tools"] == []
                assert data["total_count"] == 0
                assert data["filtered_count"] == 0
                assert data["categories"] == []
    
    def test_list_tools_with_data(self, client, auth_headers):
        """Test listing tools with sample data."""
        from src.db.models.tool import ToolDB
        from datetime import datetime
        import uuid
        
        mock_tool = ToolDB(
            id=uuid.uuid4(),
            name="test_tool",
            type="code",
            description="Test tool description",
            module_path="src.tools.test.tool",
            function_name="test_function",
            parameters_schema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "Test parameter"}
                },
                "required": ["param1"]
            },
            capabilities=["testing"],
            categories=["test"],
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch('src.api.routes.tool_routes.db_list_tools') as mock_list:
            mock_list.return_value = [mock_tool]
            
            with patch('src.api.routes.tool_routes.get_tool_categories') as mock_categories:
                mock_categories.return_value = ["test", "utility"]
                
                response = client.get("/tools/", headers=auth_headers)
                assert response.status_code == 200
                
                data = response.json()
                assert len(data["tools"]) == 1
                assert data["tools"][0]["name"] == "test_tool"
                assert data["tools"][0]["type"] == "code"
                assert data["tools"][0]["description"] == "Test tool description"
                assert len(data["tools"][0]["parameters"]) == 1
                assert data["categories"] == ["test", "utility"]
    
    def test_list_tools_with_filters(self, client, auth_headers):
        """Test listing tools with filtering parameters."""
        with patch('src.api.routes.tool_routes.db_list_tools') as mock_list:
            mock_list.return_value = []
            
            with patch('src.api.routes.tool_routes.get_tool_categories') as mock_categories:
                mock_categories.return_value = []
                
                response = client.get(
                    "/tools/?tool_type=code&enabled_only=true&category=test&agent_name=test_agent",
                    headers=auth_headers
                )
                assert response.status_code == 200
                
                # Verify the filters were passed correctly
                mock_list.assert_called_once()
    
    def test_list_tools_with_search(self, client, auth_headers):
        """Test listing tools with search functionality."""
        from src.db.models.tool import ToolDB
        from datetime import datetime
        import uuid
        
        # Create mock tools
        tools = [
            ToolDB(
                id=uuid.uuid4(),
                name="email_sender",
                type="code",
                description="Send emails via SMTP",
                module_path="src.tools.email.tool",
                function_name="send_email",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            ),
            ToolDB(
                id=uuid.uuid4(),
                name="file_processor",
                type="code", 
                description="Process files and documents",
                module_path="src.tools.file.tool",
                function_name="process_file",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
        ]
        
        with patch('src.api.routes.tool_routes.db_list_tools') as mock_list:
            mock_list.return_value = tools
            
            with patch('src.api.routes.tool_routes.get_tool_categories') as mock_categories:
                mock_categories.return_value = []
                
                # Search for "email" - should return only email_sender
                response = client.get("/tools/?search=email", headers=auth_headers)
                assert response.status_code == 200
                
                data = response.json()
                assert len(data["tools"]) == 1
                assert data["tools"][0]["name"] == "email_sender"
    
    def test_get_tool_details_success(self, client, auth_headers):
        """Test getting tool details successfully."""
        from src.db.models.tool import ToolDB
        from datetime import datetime
        import uuid
        
        tool_id = uuid.uuid4()
        mock_tool = ToolDB(
            id=tool_id,
            name="test_tool",
            type="code",
            description="Test tool description",
            module_path="src.tools.test.tool",
            function_name="test_function",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        mock_stats = {
            "total_executions": 10,
            "successful_executions": 8,
            "failed_executions": 2,
            "success_rate": 80.0,
            "avg_execution_time_ms": 150.5
        }
        
        with patch('src.api.routes.tool_routes.get_tool_by_name') as mock_get:
            mock_get.return_value = mock_tool
            
            with patch('src.api.routes.tool_routes.get_tool_execution_stats') as mock_stats_fn:
                mock_stats_fn.return_value = mock_stats
                
                response = client.get("/tools/test_tool", headers=auth_headers)
                assert response.status_code == 200
                
                data = response.json()
                assert data["tool"]["name"] == "test_tool"
                assert data["stats"]["total_executions"] == 10
                assert data["stats"]["success_rate"] == 80.0
    
    def test_get_tool_details_not_found(self, client, auth_headers):
        """Test getting details for non-existent tool."""
        with patch('src.api.routes.tool_routes.get_tool_by_name') as mock_get:
            mock_get.return_value = None
            
            response = client.get("/tools/nonexistent_tool", headers=auth_headers)
            assert response.status_code == 404
            assert "not found" in response.json()["detail"]
    
    def test_execute_tool_success(self, client, auth_headers):
        """Test successful tool execution."""
        from src.db.models.tool import ToolDB
        from datetime import datetime
        import uuid
        
        mock_tool = ToolDB(
            id=uuid.uuid4(),
            name="test_tool",
            type="code",
            description="Test tool",
            module_path="src.tools.test.tool",
            function_name="test_function",
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        request_data = {
            "context": {"agent_name": "test_agent", "session_id": "test_session"},
            "parameters": {"param1": "value1"}
        }
        
        with patch('src.api.routes.tool_routes.get_tool_by_name') as mock_get:
            mock_get.return_value = mock_tool
            
            with patch('src.api.routes.tool_routes.execute_tool') as mock_execute:
                mock_execute.return_value = {"result": "success"}
                
                with patch('src.api.routes.tool_routes.log_tool_execution') as mock_log:
                    mock_log.return_value = True
                    
                    response = client.post(
                        "/tools/test_tool/execute",
                        headers=auth_headers,
                        json=request_data
                    )
                    assert response.status_code == 200
                    
                    data = response.json()
                    assert data["status"] == "success"
                    assert data["result"]["result"] == "success"
    
    def test_execute_tool_not_found(self, client, auth_headers):
        """Test executing non-existent tool."""
        with patch('src.api.routes.tool_routes.get_tool_by_name') as mock_get:
            mock_get.return_value = None
            
            request_data = {
                "context": {},
                "parameters": {}
            }
            
            response = client.post(
                "/tools/nonexistent_tool/execute",
                headers=auth_headers,
                json=request_data
            )
            assert response.status_code == 404
    
    def test_execute_tool_disabled(self, client, auth_headers):
        """Test executing disabled tool."""
        from src.db.models.tool import ToolDB
        from datetime import datetime
        import uuid
        
        mock_tool = ToolDB(
            id=uuid.uuid4(),
            name="disabled_tool",
            type="code",
            enabled=False,  # Tool is disabled
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch('src.api.routes.tool_routes.get_tool_by_name') as mock_get:
            mock_get.return_value = mock_tool
            
            request_data = {
                "context": {},
                "parameters": {}
            }
            
            response = client.post(
                "/tools/disabled_tool/execute",
                headers=auth_headers,
                json=request_data
            )
            assert response.status_code == 403
            assert "disabled" in response.json()["detail"]
    
    def test_create_tool_success(self, client, auth_headers):
        """Test successful tool creation."""
        from src.db.models.tool import ToolDB
        from datetime import datetime
        import uuid
        
        tool_data = {
            "name": "new_tool",
            "type": "code",
            "description": "A new test tool",
            "module_path": "src.tools.new.tool",
            "function_name": "new_function",
            "parameters_schema": {
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "Test parameter"}
                }
            },
            "categories": ["test"],
            "enabled": True
        }
        
        mock_created_tool = ToolDB(
            id=uuid.uuid4(),
            name="new_tool",
            type="code",
            description="A new test tool",
            module_path="src.tools.new.tool",
            function_name="new_function",
            parameters_schema=tool_data["parameters_schema"],
            categories=["test"],
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch('src.api.routes.tool_routes.get_tool_by_name') as mock_get:
            mock_get.return_value = None  # Tool doesn't exist
            
            with patch('src.api.routes.tool_routes.create_tool') as mock_create:
                mock_create.return_value = mock_created_tool
                
                response = client.post(
                    "/tools/",
                    headers=auth_headers,
                    json=tool_data
                )
                assert response.status_code == 200
                
                data = response.json()
                assert data["status"] == "success"
                assert data["tool"]["name"] == "new_tool"
                assert "created successfully" in data["message"]
    
    def test_create_tool_already_exists(self, client, auth_headers):
        """Test creating tool that already exists."""
        from src.db.models.tool import ToolDB
        from datetime import datetime
        import uuid
        
        existing_tool = ToolDB(
            id=uuid.uuid4(),
            name="existing_tool",
            type="code",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        tool_data = {
            "name": "existing_tool",
            "type": "code",
            "description": "Tool that already exists"
        }
        
        with patch('src.api.routes.tool_routes.get_tool_by_name') as mock_get:
            mock_get.return_value = existing_tool
            
            response = client.post(
                "/tools/",
                headers=auth_headers,
                json=tool_data
            )
            assert response.status_code == 409
            assert "already exists" in response.json()["detail"]
    
    def test_update_tool_success(self, client, auth_headers):
        """Test successful tool update."""
        from src.db.models.tool import ToolDB
        from datetime import datetime
        import uuid
        
        tool_id = uuid.uuid4()
        existing_tool = ToolDB(
            id=tool_id,
            name="test_tool",
            type="code",
            description="Old description",
            enabled=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        updated_tool = ToolDB(
            id=tool_id,
            name="test_tool",
            type="code",
            description="Updated description",
            enabled=False,
            created_at=existing_tool.created_at,
            updated_at=datetime.utcnow()
        )
        
        update_data = {
            "description": "Updated description",
            "enabled": False
        }
        
        with patch('src.api.routes.tool_routes.get_tool_by_name') as mock_get:
            mock_get.return_value = existing_tool
            
            with patch('src.api.routes.tool_routes.update_tool') as mock_update:
                mock_update.return_value = updated_tool
                
                response = client.put(
                    "/tools/test_tool",
                    headers=auth_headers,
                    json=update_data
                )
                assert response.status_code == 200
                
                data = response.json()
                assert data["status"] == "success"
                assert data["tool"]["description"] == "Updated description"
    
    def test_update_tool_not_found(self, client, auth_headers):
        """Test updating non-existent tool."""
        with patch('src.api.routes.tool_routes.get_tool_by_name') as mock_get:
            mock_get.return_value = None
            
            update_data = {
                "description": "Updated description"
            }
            
            response = client.put(
                "/tools/nonexistent_tool",
                headers=auth_headers,
                json=update_data
            )
            assert response.status_code == 404
    
    def test_delete_tool_success(self, client, auth_headers):
        """Test successful tool deletion."""
        from src.db.models.tool import ToolDB
        from datetime import datetime
        import uuid
        
        existing_tool = ToolDB(
            id=uuid.uuid4(),
            name="test_tool",
            type="code",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch('src.api.routes.tool_routes.get_tool_by_name') as mock_get:
            mock_get.return_value = existing_tool
            
            with patch('src.api.routes.tool_routes.delete_tool') as mock_delete:
                mock_delete.return_value = True
                
                response = client.delete("/tools/test_tool", headers=auth_headers)
                assert response.status_code == 200
                
                data = response.json()
                assert data["status"] == "success"
                assert "deleted successfully" in data["message"]
    
    def test_delete_tool_not_found(self, client, auth_headers):
        """Test deleting non-existent tool."""
        with patch('src.api.routes.tool_routes.get_tool_by_name') as mock_get:
            mock_get.return_value = None
            
            response = client.delete("/tools/nonexistent_tool", headers=auth_headers)
            assert response.status_code == 404
    
    def test_list_tool_categories(self, client, auth_headers):
        """Test listing tool categories."""
        mock_categories = ["messaging", "file_operations", "database", "api"]
        
        with patch('src.api.routes.tool_routes.get_tool_categories') as mock_get:
            mock_get.return_value = mock_categories
            
            response = client.get("/tools/categories/list", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data == mock_categories
    
    def test_discover_tools(self, client, auth_headers):
        """Test tool discovery endpoint."""
        mock_discovered = {
            "code_tools": [
                {"name": "code_tool_1", "type": "code"},
                {"name": "code_tool_2", "type": "code"}
            ],
            "mcp_tools": [
                {"name": "mcp_tool_1", "type": "mcp"}
            ]
        }
        
        mock_sync_stats = {
            "created": 2,
            "updated": 1,
            "errors": 0,
            "total": 3
        }
        
        with patch('src.api.routes.tool_routes.get_tool_discovery_service') as mock_get_service:
            mock_service = MagicMock()
            mock_service.discover_all_tools = AsyncMock(return_value=mock_discovered)
            mock_service.sync_tools_to_database = AsyncMock(return_value=mock_sync_stats)
            mock_get_service.return_value = mock_service
            
            response = client.post("/tools/discover", headers=auth_headers)
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "success"
            assert data["discovered"] == mock_discovered
            assert data["sync_stats"] == mock_sync_stats
    
    def test_create_mcp_server(self, client, auth_headers):
        """Test creating MCP server configuration."""
        from src.db.models.mcp import MCPConfig
        from datetime import datetime
        import uuid
        
        server_data = {
            "name": "test_server",
            "server_type": "stdio",
            "config": {
                "command": "python",
                "args": ["-m", "test_mcp_server"]
            },
            "auto_discover": True
        }
        
        mock_config = MCPConfig(
            id=uuid.uuid4(),
            name="test_server",
            server_type="stdio",
            config=server_data["config"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch('src.api.routes.tool_routes.create_mcp_config') as mock_create:
            mock_create.return_value = mock_config
            
            with patch('src.api.routes.tool_routes.get_tool_discovery_service') as mock_get_service:
                mock_service = MagicMock()
                mock_service._discover_mcp_tools = AsyncMock(return_value=[])
                mock_get_service.return_value = mock_service
                
                response = client.post(
                    "/tools/mcp/servers",
                    headers=auth_headers,
                    json=server_data
                )
                assert response.status_code == 200
                
                data = response.json()
                assert data["status"] == "success"
                assert data["server_name"] == "test_server"
    
    def test_unauthorized_access(self, client):
        """Test that all endpoints require authentication."""
        endpoints = [
            ("GET", "/tools/"),
            ("GET", "/tools/test_tool"),
            ("POST", "/tools/test_tool/execute"),
            ("POST", "/tools/"),
            ("PUT", "/tools/test_tool"),
            ("DELETE", "/tools/test_tool"),
            ("GET", "/tools/categories/list"),
            ("POST", "/tools/discover"),
            ("POST", "/tools/mcp/servers")
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "PUT":
                response = client.put(endpoint, json={})
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == 401, f"Expected 401 for {method} {endpoint}"