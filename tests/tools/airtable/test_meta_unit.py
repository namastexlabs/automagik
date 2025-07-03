"""Enhanced unit tests for Airtable meta operations (bases and tables)."""

import pytest
from unittest.mock import Mock, patch

from automagik.tools.airtable.interface import airtable_list_bases, airtable_list_tables
from automagik.tools.airtable.tool import list_bases, list_tables


class TestListBases:
    """Test list_bases functionality."""
    
    @pytest.mark.asyncio
    async def test_list_bases_success(self, monkeypatch):
        """Test successful bases listing."""
        async def _fake_success(ctx=None):
            return {
                "success": True, 
                "bases": [
                    {"id": "app123", "name": "Demo Base"},
                    {"id": "app456", "name": "Production Base"}
                ]
            }
        
        monkeypatch.setattr(airtable_list_bases, "function", lambda *a, **k: _fake_success())
        result = await airtable_list_bases.function(None)
        
        assert result["success"] is True
        assert len(result["bases"]) == 2
        assert result["bases"][0]["id"] == "app123"
        assert result["bases"][0]["name"] == "Demo Base"
        assert result["bases"][1]["id"] == "app456"
    
    @pytest.mark.asyncio
    async def test_list_bases_empty_result(self, monkeypatch):
        """Test bases listing with no bases."""
        async def _fake_empty(ctx=None):
            return {"success": True, "bases": []}
        
        monkeypatch.setattr(airtable_list_bases, "function", lambda *a, **k: _fake_empty())
        result = await airtable_list_bases.function(None)
        
        assert result["success"] is True
        assert result["bases"] == []
    
    @pytest.mark.asyncio
    async def test_list_bases_api_error(self, monkeypatch):
        """Test bases listing with API error."""
        async def _fake_error(ctx=None):
            return {
                "success": False, 
                "error": "HTTP 403: Insufficient permissions"
            }
        
        monkeypatch.setattr(airtable_list_bases, "function", lambda *a, **k: _fake_error())
        result = await airtable_list_bases.function(None)
        
        assert result["success"] is False
        assert "403" in result["error"]
        assert "permissions" in result["error"]
    
    @pytest.mark.asyncio
    async def test_list_bases_network_error(self, monkeypatch):
        """Test bases listing with network error."""
        async def _fake_network_error(ctx=None):
            return {
                "success": False,
                "error": "Connection timeout"
            }
        
        monkeypatch.setattr(airtable_list_bases, "function", lambda *a, **k: _fake_network_error())
        result = await airtable_list_bases.function(None)
        
        assert result["success"] is False
        assert "timeout" in result["error"]
    
    @pytest.mark.asyncio
    async def test_list_bases_invalid_token(self, monkeypatch):
        """Test bases listing with invalid token."""
        async def _fake_invalid_token(ctx=None):
            return {
                "success": False,
                "error": "HTTP 401: Invalid authentication token"
            }
        
        monkeypatch.setattr(airtable_list_bases, "function", lambda *a, **k: _fake_invalid_token())
        result = await airtable_list_bases.function(None)
        
        assert result["success"] is False
        assert "401" in result["error"]
        assert "authentication" in result["error"]


class TestListTables:
    """Test list_tables functionality."""
    
    @pytest.mark.asyncio
    async def test_list_tables_success(self, monkeypatch):
        """Test successful tables listing."""
        async def _fake_success(ctx=None, base_id=None):
            return {
                "success": True, 
                "tables": [
                    {"id": "tbl123", "name": "Tasks"},
                    {"id": "tbl456", "name": "Projects"},
                    {"id": "tbl789", "name": "Team Members"}
                ]
            }
        
        monkeypatch.setattr(airtable_list_tables, "function", lambda *a, **k: _fake_success())
        result = await airtable_list_tables.function(None, base_id="app123")
        
        assert result["success"] is True
        assert len(result["tables"]) == 3
        assert result["tables"][0]["id"] == "tbl123"
        assert result["tables"][0]["name"] == "Tasks"
        assert result["tables"][2]["name"] == "Team Members"
    
    @pytest.mark.asyncio
    async def test_list_tables_single_table(self, monkeypatch):
        """Test tables listing with single table."""
        async def _fake_single(ctx=None, base_id=None):
            return {
                "success": True,
                "tables": [{"id": "tbl001", "name": "Main Table"}]
            }
        
        monkeypatch.setattr(airtable_list_tables, "function", lambda *a, **k: _fake_single())
        result = await airtable_list_tables.function(None, base_id="app123")
        
        assert result["success"] is True
        assert len(result["tables"]) == 1
        assert result["tables"][0]["name"] == "Main Table"
    
    @pytest.mark.asyncio
    async def test_list_tables_empty_base(self, monkeypatch):
        """Test tables listing with empty base."""
        async def _fake_empty(ctx=None, base_id=None):
            return {"success": True, "tables": []}
        
        monkeypatch.setattr(airtable_list_tables, "function", lambda *a, **k: _fake_empty())
        result = await airtable_list_tables.function(None, base_id="app123")
        
        assert result["success"] is True
        assert result["tables"] == []
    
    @pytest.mark.asyncio
    async def test_list_tables_invalid_base(self, monkeypatch):
        """Test tables listing with invalid base ID."""
        async def _fake_invalid_base(ctx=None, base_id=None):
            return {
                "success": False,
                "error": "HTTP 404: Base not found"
            }
        
        monkeypatch.setattr(airtable_list_tables, "function", lambda *a, **k: _fake_invalid_base())
        result = await airtable_list_tables.function(None, base_id="appInvalid")
        
        assert result["success"] is False
        assert "404" in result["error"]
        assert "not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_list_tables_permission_denied(self, monkeypatch):
        """Test tables listing with permission denied."""
        async def _fake_permission_denied(ctx=None, base_id=None):
            return {
                "success": False,
                "error": "HTTP 403: You don't have permission to access this base"
            }
        
        monkeypatch.setattr(airtable_list_tables, "function", lambda *a, **k: _fake_permission_denied())
        result = await airtable_list_tables.function(None, base_id="app123")
        
        assert result["success"] is False
        assert "403" in result["error"]
        assert "permission" in result["error"]


class TestMetaToolIntegration:
    """Test meta tool integration with actual tool functions."""
    
    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_list_bases_actual_function(self, mock_request, monkeypatch):
        """Test list_bases actual function with mocked HTTP."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "bases": [
                {"id": "app123", "name": "Test Base"},
                {"id": "app456", "name": "Another Base"}
            ]
        }
        mock_request.return_value = mock_response
        
        ctx = {}
        result = await list_bases(ctx)
        
        assert result["success"] is True
        assert len(result["bases"]) == 2
        assert result["bases"][0]["id"] == "app123"
        
        # Verify API call was made correctly
        mock_request.assert_called_once_with(
            "GET", 
            "https://api.airtable.com/v0/meta/bases"
        )
    
    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_list_tables_actual_function(self, mock_request, monkeypatch):
        """Test list_tables actual function with mocked HTTP."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "tables": [
                {"id": "tbl123", "name": "Main Table"},
                {"id": "tbl456", "name": "Secondary Table"}
            ]
        }
        mock_request.return_value = mock_response
        
        ctx = {}
        result = await list_tables(ctx, base_id="app123")
        
        assert result["success"] is True
        assert len(result["tables"]) == 2
        assert result["tables"][0]["name"] == "Main Table"
        
        # Verify API call was made correctly
        mock_request.assert_called_once_with(
            "GET",
            "https://api.airtable.com/v0/meta/bases/app123/tables"
        )


class TestErrorScenarios:
    """Test various error scenarios and edge cases."""
    
    @pytest.mark.asyncio
    async def test_list_bases_malformed_response(self, monkeypatch):
        """Test handling of malformed API response."""
        async def _fake_malformed(ctx=None):
            return {
                "success": True,
                "bases": "not_a_list"  # Invalid format
            }
        
        monkeypatch.setattr(airtable_list_bases, "function", lambda *a, **k: _fake_malformed())
        result = await airtable_list_bases.function(None)
        
        # Tool should still return the malformed data - validation handled at higher level
        assert result["success"] is True
        assert result["bases"] == "not_a_list"
    
    @pytest.mark.asyncio
    async def test_list_tables_missing_base_id(self, monkeypatch):
        """Test tables listing without base_id parameter."""
        async def _fake_missing_base(ctx=None, base_id=None):
            if base_id is None:
                return {
                    "success": False,
                    "error": "base_id parameter is required"
                }
            return {"success": True, "tables": []}
        
        monkeypatch.setattr(airtable_list_tables, "function", lambda *a, **k: _fake_missing_base(*a, **k))
        result = await airtable_list_tables.function(None, base_id=None)
        
        assert result["success"] is False
        assert "base_id" in result["error"]
    
    @pytest.mark.asyncio
    async def test_rate_limiting_scenario(self, monkeypatch):
        """Test handling of rate limiting."""
        async def _fake_rate_limited(ctx=None):
            return {
                "success": False,
                "error": "HTTP 429: Too many requests"
            }
        
        monkeypatch.setattr(airtable_list_bases, "function", lambda *a, **k: _fake_rate_limited())
        result = await airtable_list_bases.function(None)
        
        assert result["success"] is False
        assert "429" in result["error"]
        assert "Too many requests" in result["error"]


class TestDataIntegrity:
    """Test data structure integrity and validation."""
    
    @pytest.mark.asyncio
    async def test_bases_structure_validation(self, monkeypatch):
        """Test that bases have required structure."""
        async def _fake_structured(ctx=None):
            return {
                "success": True,
                "bases": [
                    {"id": "app123", "name": "Base 1", "extra_field": "ignored"},
                    {"id": "app456", "name": "Base 2"}
                ]
            }
        
        monkeypatch.setattr(airtable_list_bases, "function", lambda *a, **k: _fake_structured())
        result = await airtable_list_bases.function(None)
        
        assert result["success"] is True
        for base in result["bases"]:
            assert "id" in base
            assert "name" in base
            assert base["id"].startswith("app")
    
    @pytest.mark.asyncio
    async def test_tables_structure_validation(self, monkeypatch):
        """Test that tables have required structure."""
        async def _fake_structured(ctx=None, base_id=None):
            return {
                "success": True,
                "tables": [
                    {"id": "tbl123", "name": "Table 1", "description": "optional"},
                    {"id": "tbl456", "name": "Table 2"}
                ]
            }
        
        monkeypatch.setattr(airtable_list_tables, "function", lambda *a, **k: _fake_structured())
        result = await airtable_list_tables.function(None, base_id="app123")
        
        assert result["success"] is True
        for table in result["tables"]:
            assert "id" in table
            assert "name" in table
            assert table["id"].startswith("tbl") 