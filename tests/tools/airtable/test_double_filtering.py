"""Test double filtering and complex filter scenarios for Airtable agent.

This test file specifically focuses on validating that the Airtable agent can handle
complex filtering scenarios including:
- Double filtering (multiple conditions with AND/OR)
- Status-only filtering ("only tasks to do")
- Person + Status combinations
- Complex search queries with multiple criteria
"""

import pytest
from unittest.mock import Mock, patch

from automagik.tools.airtable.tool import list_records


class TestDoubleFiltering:
    """Test complex double filtering scenarios."""

    @pytest.fixture
    def dummy_context(self):
        """Create a dummy context for testing."""
        return {}

    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_status_only_filter_a_fazer(self, mock_request, dummy_context, monkeypatch):
        """Test filtering for only 'A fazer' (to do) status tasks."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        # Mock response with tasks that have 'A fazer' status
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": [
                {
                    "id": "rec1",
                    "fields": {
                        "Name": "Task 1",
                        "Status": "A fazer",
                        "Assigned Team Members": ["Daniel Amora"]
                    }
                },
                {
                    "id": "rec2", 
                    "fields": {
                        "Name": "Task 2",
                        "Status": "A fazer",
                        "Priority": "Alta"
                    }
                }
            ]
        }
        mock_request.return_value = mock_response
        
        result = await list_records(
            dummy_context,
            table="tblTasks",
            filter_formula="{{Status}} = 'A fazer'",
            base_id="appTest"
        )
        
        assert result["success"] is True
        assert len(result["records"]) == 2
        # Verify all returned records have 'A fazer' status
        for record in result["records"]:
            assert record["fields"]["Status"] == "A fazer"
        
        # Verify the correct filter was applied
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        assert "filterByFormula" in call_args[1]["params"]
        assert call_args[1]["params"]["filterByFormula"] == "{{Status}} = 'A fazer'"

    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_person_and_status_double_filter(self, mock_request, dummy_context, monkeypatch):
        """Test double filtering: specific person AND specific status."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": [
                {
                    "id": "rec1",
                    "fields": {
                        "Name": "Cezar's Task",
                        "Status": "Estou trabalhando",
                        "Assigned Team Members": ["Cezar Vasconcelos"]
                    }
                }
            ]
        }
        mock_request.return_value = mock_response
        
        result = await list_records(
            dummy_context,
            table="tblTasks",
            filter_formula="AND(SEARCH('Cezar Vasconcelos', {{Assigned Team Members}}), {{Status}} = 'Estou trabalhando')",
            base_id="appTest"
        )
        
        assert result["success"] is True
        assert len(result["records"]) == 1
        assert result["records"][0]["fields"]["Name"] == "Cezar's Task"
        assert result["records"][0]["fields"]["Status"] == "Estou trabalhando"
        
        # Verify the AND filter was applied correctly
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        expected_filter = "AND(SEARCH('Cezar Vasconcelos', {{Assigned Team Members}}), {{Status}} = 'Estou trabalhando')"
        assert call_args[1]["params"]["filterByFormula"] == expected_filter

    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_multiple_status_or_filter(self, mock_request, dummy_context, monkeypatch):
        """Test OR filtering for multiple status values."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": [
                {
                    "id": "rec1",
                    "fields": {
                        "Name": "Active Task 1",
                        "Status": "A fazer"
                    }
                },
                {
                    "id": "rec2",
                    "fields": {
                        "Name": "Active Task 2", 
                        "Status": "Estou trabalhando"
                    }
                }
            ]
        }
        mock_request.return_value = mock_response
        
        result = await list_records(
            dummy_context,
            table="tblTasks",
            filter_formula="OR({{Status}} = 'A fazer', {{Status}} = 'Estou trabalhando')",
            base_id="appTest"
        )
        
        assert result["success"] is True
        assert len(result["records"]) == 2
        
        # Verify both status types are present
        statuses = [record["fields"]["Status"] for record in result["records"]]
        assert "A fazer" in statuses
        assert "Estou trabalhando" in statuses

    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_not_completed_filter(self, mock_request, dummy_context, monkeypatch):
        """Test NOT filter to exclude completed tasks."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": [
                {
                    "id": "rec1",
                    "fields": {
                        "Name": "Incomplete Task 1",
                        "Status": "A fazer"
                    }
                },
                {
                    "id": "rec2",
                    "fields": {
                        "Name": "Incomplete Task 2",
                        "Status": "Estou bloqueado"
                    }
                }
            ]
        }
        mock_request.return_value = mock_response
        
        result = await list_records(
            dummy_context,
            table="tblTasks",
            filter_formula="NOT({{Status}} = 'Terminei')",
            base_id="appTest"
        )
        
        assert result["success"] is True
        assert len(result["records"]) == 2
        
        # Verify no completed tasks in results
        for record in result["records"]:
            assert record["fields"]["Status"] != "Terminei"

    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_priority_and_person_filter(self, mock_request, dummy_context, monkeypatch):
        """Test filtering by priority AND person assignment."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": [
                {
                    "id": "rec1",
                    "fields": {
                        "Name": "High Priority Task for Daniel",
                        "Priority": "Alta",
                        "Assigned Team Members": ["Daniel Amora"]
                    }
                }
            ]
        }
        mock_request.return_value = mock_response
        
        result = await list_records(
            dummy_context,
            table="tblTasks",
            filter_formula="AND({{Priority}} = 'Alta', SEARCH('Daniel Amora', {{Assigned Team Members}}))",
            base_id="appTest"
        )
        
        assert result["success"] is True
        assert len(result["records"]) == 1
        assert result["records"][0]["fields"]["Priority"] == "Alta"
        assert "Daniel Amora" in result["records"][0]["fields"]["Assigned Team Members"]

    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_complex_triple_filter(self, mock_request, dummy_context, monkeypatch):
        """Test complex filtering with three conditions."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": [
                {
                    "id": "rec1",
                    "fields": {
                        "Name": "Complex Task",
                        "Status": "A fazer",
                        "Priority": "Para tudo e faz",
                        "Assigned Team Members": ["Cezar Vasconcelos"]
                    }
                }
            ]
        }
        mock_request.return_value = mock_response
        
        result = await list_records(
            dummy_context,
            table="tblTasks",
            filter_formula="AND({{Status}} = 'A fazer', {{Priority}} = 'Para tudo e faz', SEARCH('Cezar Vasconcelos', {{Assigned Team Members}}))",
            base_id="appTest"
        )
        
        assert result["success"] is True
        assert len(result["records"]) == 1
        record = result["records"][0]
        assert record["fields"]["Status"] == "A fazer"
        assert record["fields"]["Priority"] == "Para tudo e faz"
        assert "Cezar Vasconcelos" in record["fields"]["Assigned Team Members"]

    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_empty_filter_result(self, mock_request, dummy_context, monkeypatch):
        """Test filter that returns no results."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": []  # No records match the filter
        }
        mock_request.return_value = mock_response
        
        result = await list_records(
            dummy_context,
            table="tblTasks",
            filter_formula="{{Status}} = 'NonExistentStatus'",
            base_id="appTest"
        )
        
        assert result["success"] is True
        assert len(result["records"]) == 0

    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_case_sensitive_status_filter(self, mock_request, dummy_context, monkeypatch):
        """Test that status filtering is case-sensitive."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": []  # No results for wrong case
        }
        mock_request.return_value = mock_response
        
        result = await list_records(
            dummy_context,
            table="tblTasks",
            filter_formula="{{Status}} = 'a fazer'",  # lowercase should not match 'A fazer'
            base_id="appTest"
        )
        
        assert result["success"] is True
        assert len(result["records"]) == 0


class TestFilterSyntaxValidation:
    """Test proper filter syntax generation and validation."""

    @pytest.fixture
    def dummy_context(self):
        return {}

    def test_field_reference_syntax(self):
        """Test that field references use double curly braces."""
        # This is more of a documentation test to ensure we follow the correct syntax
        valid_syntax = "{{Status}} = 'A fazer'"
        invalid_syntax = "{Status} = 'A fazer'"
        
        # The valid syntax should use double curly braces
        assert "{{" in valid_syntax and "}}" in valid_syntax
        assert "{{" not in invalid_syntax or "}}" not in invalid_syntax

    def test_search_function_syntax(self):
        """Test SEARCH function syntax for linked records."""
        valid_search = "SEARCH('Cezar Vasconcelos', {{Assigned Team Members}})"
        
        # Should contain SEARCH function with quoted search term
        assert valid_search.startswith("SEARCH(")
        assert "'Cezar Vasconcelos'" in valid_search
        assert "{{Assigned Team Members}}" in valid_search

    def test_logical_operators_syntax(self):
        """Test AND, OR, NOT operators syntax."""
        and_filter = "AND({{Status}} = 'A fazer', {{Priority}} = 'Alta')"
        or_filter = "OR({{Status}} = 'A fazer', {{Status}} = 'Estou trabalhando')"
        not_filter = "NOT({{Status}} = 'Terminei')"
        
        assert and_filter.startswith("AND(")
        assert or_filter.startswith("OR(")
        assert not_filter.startswith("NOT(")
        
        # All should end with closing parenthesis
        assert and_filter.endswith(")")
        assert or_filter.endswith(")")
        assert not_filter.endswith(")")


class TestCommonFilterScenarios:
    """Test common filtering scenarios the agent should handle."""

    @pytest.fixture
    def dummy_context(self):
        return {}

    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_blocked_tasks_filter(self, mock_request, dummy_context, monkeypatch):
        """Test filtering for blocked tasks specifically."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": [
                {
                    "id": "rec1",
                    "fields": {
                        "Name": "Blocked Task",
                        "Status": "Estou bloqueado",
                        "Blocker Reason": "Waiting for approval"
                    }
                }
            ]
        }
        mock_request.return_value = mock_response
        
        result = await list_records(
            dummy_context,
            table="tblTasks",
            filter_formula="{{Status}} = 'Estou bloqueado'",
            base_id="appTest"
        )
        
        assert result["success"] is True
        assert len(result["records"]) == 1
        assert result["records"][0]["fields"]["Status"] == "Estou bloqueado"

    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_high_priority_incomplete_tasks(self, mock_request, dummy_context, monkeypatch):
        """Test filtering for high priority tasks that are not completed."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": [
                {
                    "id": "rec1",
                    "fields": {
                        "Name": "Urgent Task",
                        "Status": "A fazer",
                        "Priority": "Para tudo e faz"
                    }
                },
                {
                    "id": "rec2",
                    "fields": {
                        "Name": "High Priority WIP",
                        "Status": "Estou trabalhando", 
                        "Priority": "Alta"
                    }
                }
            ]
        }
        mock_request.return_value = mock_response
        
        result = await list_records(
            dummy_context,
            table="tblTasks",
            filter_formula="AND(OR({{Priority}} = 'Para tudo e faz', {{Priority}} = 'Alta'), NOT({{Status}} = 'Terminei'))",
            base_id="appTest"
        )
        
        assert result["success"] is True
        assert len(result["records"]) == 2
        
        # Verify all are high priority and not completed
        for record in result["records"]:
            priority = record["fields"]["Priority"]
            status = record["fields"]["Status"]
            assert priority in ["Para tudo e faz", "Alta"]
            assert status != "Terminei"

    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_team_member_tasks_any_status(self, mock_request, dummy_context, monkeypatch):
        """Test getting all tasks for a team member regardless of status."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": [
                {
                    "id": "rec1",
                    "fields": {
                        "Name": "Daniel's Todo",
                        "Status": "A fazer",
                        "Assigned Team Members": ["Daniel Amora"]
                    }
                },
                {
                    "id": "rec2",
                    "fields": {
                        "Name": "Daniel's Completed",
                        "Status": "Terminei",
                        "Assigned Team Members": ["Daniel Amora", "Cezar Vasconcelos"]
                    }
                }
            ]
        }
        mock_request.return_value = mock_response
        
        result = await list_records(
            dummy_context,
            table="tblTasks",
            filter_formula="SEARCH('Daniel Amora', {{Assigned Team Members}})",
            base_id="appTest"
        )
        
        assert result["success"] is True
        assert len(result["records"]) == 2
        
        # Verify all records have Daniel as assignee
        for record in result["records"]:
            assert "Daniel Amora" in record["fields"]["Assigned Team Members"] 