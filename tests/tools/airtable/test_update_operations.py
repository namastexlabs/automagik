"""Test Airtable update operations for registry management.

This module tests the critical update functionality needed for registry operations.
Includes unit tests with mocked responses, integration tests with real API calls,
and agent usage tests.
"""

import asyncio
import os
import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from pydantic_ai import Agent, RunContext, capture_run_messages
from pydantic_ai.models.test import TestModel
from pydantic_ai.messages import ModelRequest, ModelResponse, ToolCallPart, ToolReturnPart

from src.tools.airtable.tool import update_records, create_records, list_records
from src.tools.airtable.interface import airtable_update_records, airtable_create_records, airtable_list_records
from src.config import settings

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    """Force pytest-anyio to use the asyncio backend only."""
    return "asyncio"


@pytest.fixture
def dummy_context() -> RunContext[Dict]:
    """Dummy run context for tool testing."""
    return {}


# ---------------------------------------------------------------------------
# Unit Tests with Mocked API Responses
# ---------------------------------------------------------------------------

class TestUpdateRecordsUnit:
    """Unit tests for update_records with mocked API responses."""

    async def test_update_records_success(self, dummy_context, monkeypatch):
        """Test successful update of multiple records."""
        
        def mock_request(method, url, **kwargs):
            """Mock successful API response."""
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "records": [
                    {
                        "id": "rec123",
                        "fields": {"Name": "Updated Record 1", "Status": "Active"},
                        "createdTime": "2024-01-01T00:00:00.000Z"
                    },
                    {
                        "id": "rec456", 
                        "fields": {"Name": "Updated Record 2", "Status": "Inactive"},
                        "createdTime": "2024-01-01T00:00:00.000Z"
                    }
                ]
            }
            return mock_response

        monkeypatch.setattr("src.tools.airtable.tool._request", mock_request)
        
        records_to_update = [
            {"id": "rec123", "fields": {"Name": "Updated Record 1", "Status": "Active"}},
            {"id": "rec456", "fields": {"Name": "Updated Record 2", "Status": "Inactive"}}
        ]
        
        result = await update_records(
            dummy_context,
            table="tblTest123",
            records=records_to_update,
            base_id="appTest123"
        )
        
        assert result["success"] is True
        assert len(result["records"]) == 2
        assert result["records"][0]["id"] == "rec123"
        assert result["records"][0]["fields"]["Name"] == "Updated Record 1"
        assert result["records"][1]["id"] == "rec456"
        assert result["records"][1]["fields"]["Status"] == "Inactive"

    async def test_update_records_missing_id(self, dummy_context, monkeypatch):
        """Test update fails when record ID is missing."""
        
        records_to_update = [
            {"fields": {"Name": "Missing ID Record"}}  # No 'id' field
        ]
        
        result = await update_records(
            dummy_context,
            table="tblTest123", 
            records=records_to_update,
            base_id="appTest123"
        )
        
        assert result["success"] is False
        assert "Each record must include an 'id'" in result["error"]

    async def test_update_records_too_many(self, dummy_context, monkeypatch):
        """Test update fails when trying to update more than 10 records."""
        
        records_to_update = [
            {"id": f"rec{i}", "fields": {"Name": f"Record {i}"}}
            for i in range(11)  # 11 records, exceeds limit
        ]
        
        result = await update_records(
            dummy_context,
            table="tblTest123",
            records=records_to_update,
            base_id="appTest123"
        )
        
        assert result["success"] is False
        assert "max 10 records per update" in result["error"]

    async def test_update_records_api_error(self, dummy_context, monkeypatch):
        """Test update handles API errors gracefully."""
        
        def mock_request_error(method, url, **kwargs):
            """Mock API error response."""
            mock_response = Mock()
            mock_response.status_code = 422
            mock_response.text = "INVALID_REQUEST_UNKNOWN: Field 'NonExistentField' does not exist"
            return mock_response

        monkeypatch.setattr("src.tools.airtable.tool._request", mock_request_error)
        
        records_to_update = [
            {"id": "rec123", "fields": {"NonExistentField": "Invalid"}}
        ]
        
        result = await update_records(
            dummy_context,
            table="tblTest123",
            records=records_to_update,
            base_id="appTest123"
        )
        
        assert result["success"] is False
        assert "HTTP 422" in result["error"]
        assert "NonExistentField" in result["error"]


# ---------------------------------------------------------------------------
# Registry-Specific Update Scenarios
# ---------------------------------------------------------------------------

class TestRegistryUpdateScenarios:
    """Test common registry update patterns."""

    async def test_registry_status_update(self, dummy_context, monkeypatch):
        """Test updating registry entry status (common registry operation)."""
        
        def mock_request(method, url, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "records": [
                    {
                        "id": "recAgent123",
                        "fields": {
                            "Name": "simple_agent", 
                            "Status": "Active",
                            "Version": "1.2.0",
                            "LastUpdated": "2024-01-15T10:30:00.000Z"
                        },
                        "createdTime": "2024-01-01T00:00:00.000Z"
                    }
                ]
            }
            return mock_response

        monkeypatch.setattr("src.tools.airtable.tool._request", mock_request)
        
        # Simulate updating an agent's status in registry
        registry_update = [
            {
                "id": "recAgent123",
                "fields": {
                    "Status": "Active",
                    "Version": "1.2.0", 
                    "LastUpdated": "2024-01-15T10:30:00.000Z"
                }
            }
        ]
        
        result = await update_records(
            dummy_context,
            table="tblAgentRegistry",
            records=registry_update,
            base_id="appRegistry123"
        )
        
        assert result["success"] is True
        updated_record = result["records"][0]
        assert updated_record["fields"]["Status"] == "Active"
        assert updated_record["fields"]["Version"] == "1.2.0"
        assert "LastUpdated" in updated_record["fields"]

    async def test_bulk_registry_update(self, dummy_context, monkeypatch):
        """Test updating multiple registry entries at once."""
        
        def mock_request(method, url, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "records": [
                    {"id": "recAgent1", "fields": {"Status": "Deprecated"}},
                    {"id": "recAgent2", "fields": {"Status": "Deprecated"}},
                    {"id": "recAgent3", "fields": {"Status": "Deprecated"}}
                ]
            }
            return mock_response

        monkeypatch.setattr("src.tools.airtable.tool._request", mock_request)
        
        # Simulate deprecating multiple agents
        bulk_update = [
            {"id": "recAgent1", "fields": {"Status": "Deprecated"}},
            {"id": "recAgent2", "fields": {"Status": "Deprecated"}}, 
            {"id": "recAgent3", "fields": {"Status": "Deprecated"}}
        ]
        
        result = await update_records(
            dummy_context,
            table="tblAgentRegistry",
            records=bulk_update,
            base_id="appRegistry123"
        )
        
        assert result["success"] is True
        assert len(result["records"]) == 3
        for record in result["records"]:
            assert record["fields"]["Status"] == "Deprecated"


# ---------------------------------------------------------------------------
# Agent Usage Tests
# ---------------------------------------------------------------------------

class TestAgentUpdateUsage:
    """Test that agents can successfully use update tools."""

    def _mock_update_response(self, *args, **kwargs):
        """Return a canned update result."""
        return {
            "success": True,
            "records": [
                {
                    "id": "rec123",
                    "fields": {"Name": "Updated Agent", "Status": "Active"},
                    "createdTime": "2024-01-01T00:00:00.000Z"
                }
            ]
        }

    async def test_agent_update_registry_entry(self, monkeypatch):
        """Test agent can update a registry entry."""
        
        monkeypatch.setattr(airtable_update_records, "function", self._mock_update_response)
        
        agent = Agent(
            "test",
            tools=[airtable_update_records],
            system_prompt="You can update Airtable records for registry management."
        )
        
        with capture_run_messages() as messages:
            with agent.override(model=TestModel()):
                await agent.run(
                    "Update the agent registry entry rec123 to set status as Active and name as 'Updated Agent'"
                )
        
        # Verify tool was called
        tool_calls = [
            p for msg in messages 
            if isinstance(msg, ModelResponse)
            for p in msg.parts 
            if isinstance(p, ToolCallPart) and p.tool_name == "airtable_update_records"
        ]
        assert len(tool_calls) > 0, "airtable_update_records tool was not called"


# ---------------------------------------------------------------------------
# Integration Tests (Real API)
# ---------------------------------------------------------------------------

skip_integration_tests = pytest.mark.skipif(
    not (settings.AIRTABLE_TOKEN and settings.AIRTABLE_TEST_BASE_ID and settings.AIRTABLE_TEST_TABLE),
    reason="Airtable integration variables not configured (AIRTABLE_TOKEN, AIRTABLE_TEST_BASE_ID, AIRTABLE_TEST_TABLE)"
)


@skip_integration_tests
class TestUpdateIntegration:
    """Integration tests with real Airtable API."""

    async def test_create_update_delete_cycle(self, dummy_context):
        """Test full CRUD cycle: create → update → delete."""
        
        # Step 1: Create a test record
        test_record = [{"Name": "Test Registry Entry"}]  # Remove Status field to avoid select option issues
        
        create_result = await create_records(
            dummy_context,
            table=settings.AIRTABLE_TEST_TABLE,
            records=test_record,
            base_id=settings.AIRTABLE_TEST_BASE_ID
        )
        
        if not create_result["success"]:
            print(f"🔍 CREATE FAILED: {create_result}")
            print(f"🔍 Config values - Base: {settings.AIRTABLE_TEST_BASE_ID}, Table: {settings.AIRTABLE_TEST_TABLE}")
        
        assert create_result["success"] is True
        created_record = create_result["records"][0]
        record_id = created_record["id"]
        
        try:
            # Step 2: Update the record
            update_data = [
                {
                    "id": record_id,
                    "fields": {"Name": "Updated Test Entry"}  # Simplified update without Status field
                }
            ]
            
            update_result = await update_records(
                dummy_context,
                table=settings.AIRTABLE_TEST_TABLE,
                records=update_data,
                base_id=settings.AIRTABLE_TEST_BASE_ID
            )
            
            assert update_result["success"] is True
            updated_record = update_result["records"][0]
            assert updated_record["id"] == record_id
            assert updated_record["fields"]["Name"] == "Updated Test Entry"
            
            # Step 3: Verify the update by fetching the record
            from src.tools.airtable.tool import get_record
            
            fetch_result = await get_record(
                dummy_context,
                table=settings.AIRTABLE_TEST_TABLE,
                record_id=record_id,
                base_id=settings.AIRTABLE_TEST_BASE_ID
            )
            
            assert fetch_result["success"] is True
            fetched_record = fetch_result["record"]
            assert fetched_record["fields"]["Name"] == "Updated Test Entry"
            
        finally:
            # Step 4: Clean up - delete the test record
            from src.tools.airtable.tool import delete_records
            
            delete_result = await delete_records(
                dummy_context,
                table=settings.AIRTABLE_TEST_TABLE,
                record_ids=[record_id],
                base_id=settings.AIRTABLE_TEST_BASE_ID
            )
            
            assert delete_result["success"] is True
            assert record_id in delete_result["deleted_record_ids"] 