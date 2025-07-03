"""Performance and stress tests for Airtable tools."""

import asyncio
import time
import pytest
from unittest.mock import Mock, patch

from automagik.tools.airtable.tool import (
    list_records, 
    create_records, 
    update_records, 
    MAX_RECORDS_PER_BATCH
)


class TestPerformance:
    """Test performance characteristics of Airtable operations."""
    
    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_list_records_performance(self, mock_request, monkeypatch):
        """Test list_records performance with large result sets."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        # Create large mock response (100 records)
        large_records = [
            {
                "id": f"rec{i:03d}",
                "fields": {
                    "Name": f"Record {i}",
                    "Status": "Active",
                    "Notes": f"This is test record number {i}"
                },
                "createdTime": "2024-01-01T00:00:00.000Z"
            }
            for i in range(100)
        ]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"records": large_records}
        mock_request.return_value = mock_response
        
        ctx = {}
        start_time = time.time()
        
        result = await list_records(ctx, table="tblTest", base_id="appTest")
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert result["success"] is True
        assert len(result["records"]) == 100
        assert duration < 1.0  # Should complete in under 1 second
    
    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_batch_create_performance(self, mock_request, monkeypatch):
        """Test performance of maximum batch create operation."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        # Mock successful batch create
        created_records = [
            {
                "id": f"rec{i:03d}",
                "fields": {"Name": f"Created Record {i}"},
                "createdTime": "2024-01-01T00:00:00.000Z"
            }
            for i in range(MAX_RECORDS_PER_BATCH)
        ]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"records": created_records}
        mock_request.return_value = mock_response
        
        # Create max batch of records
        records_to_create = [
            {"Name": f"Test Record {i}", "Status": "Active"}
            for i in range(MAX_RECORDS_PER_BATCH)
        ]
        
        ctx = {}
        start_time = time.time()
        
        result = await create_records(ctx, table="tblTest", records=records_to_create, base_id="appTest")
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert result["success"] is True
        assert len(result["records"]) == MAX_RECORDS_PER_BATCH
        assert duration < 2.0  # Should complete in under 2 seconds
    
    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_concurrent_operations(self, mock_request, monkeypatch):
        """Test concurrent Airtable operations."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        # Mock responses for different operations
        def mock_response_handler(*args, **kwargs):
            mock_response = Mock()
            mock_response.status_code = 200
            
            if "GET" in args:
                mock_response.json.return_value = {"records": [{"id": "rec123", "fields": {"Name": "Test"}}]}
            else:  # POST/PATCH
                mock_response.json.return_value = {"records": [{"id": "rec123", "fields": {"Name": "Test"}}]}
            
            return mock_response
        
        mock_request.side_effect = mock_response_handler
        
        ctx = {}
        
        # Run multiple operations concurrently
        start_time = time.time()
        
        tasks = [
            list_records(ctx, table="tblTest", base_id="appTest"),
            list_records(ctx, table="tblTest", base_id="appTest"),
            create_records(ctx, table="tblTest", records=[{"Name": "Test"}], base_id="appTest"),
            update_records(ctx, table="tblTest", records=[{"id": "rec123", "fields": {"Name": "Updated"}}], base_id="appTest")
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # All operations should succeed
        for result in results:
            assert result["success"] is True
        
        # Concurrent operations should be faster than sequential
        assert duration < 3.0  # Should complete concurrently in under 3 seconds
        assert mock_request.call_count == 4


class TestStressTests:
    """Stress tests for Airtable operations."""
    
    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_rapid_successive_requests(self, mock_request, monkeypatch):
        """Test rapid successive API requests."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"records": [{"id": "rec123", "fields": {"Name": "Test"}}]}
        mock_request.return_value = mock_response
        
        ctx = {}
        start_time = time.time()
        
        # Make 20 rapid requests
        tasks = [
            list_records(ctx, table="tblTest", base_id="appTest", page_size=1)
            for _ in range(20)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # All requests should succeed
        for result in results:
            assert result["success"] is True
        
        assert len(results) == 20
        assert mock_request.call_count == 20
        assert duration < 5.0  # Should handle rapid requests efficiently
    
    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_large_field_data_handling(self, mock_request, monkeypatch):
        """Test handling of records with large field data."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        # Create record with large text fields
        large_text = "x" * 10000  # 10KB of text
        large_record = {
            "id": "rec123",
            "fields": {
                "Name": "Large Record",
                "LargeText": large_text,
                "Description": large_text,
                "Notes": large_text
            },
            "createdTime": "2024-01-01T00:00:00.000Z"
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"records": [large_record]}
        mock_request.return_value = mock_response
        
        ctx = {}
        start_time = time.time()
        
        result = await list_records(ctx, table="tblTest", base_id="appTest")
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert result["success"] is True
        assert len(result["records"]) == 1
        assert len(result["records"][0]["fields"]["LargeText"]) == 10000
        assert duration < 2.0  # Should handle large data efficiently
    
    @patch('automagik.tools.airtable.tool.requests.request')
    @pytest.mark.asyncio 
    async def test_rate_limit_simulation(self, mock_request, monkeypatch):
        """Test behavior under simulated rate limiting."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        call_count = 0
        
        def rate_limit_simulation(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            mock_response = Mock()
            
            # First request hits rate limit, second succeeds (matches actual retry logic)
            if call_count == 1:
                mock_response.status_code = 429
            else:
                mock_response.status_code = 200
                mock_response.json.return_value = {"records": [{"id": "rec123", "fields": {"Name": "Test"}}]}
            
            return mock_response
        
        mock_request.side_effect = rate_limit_simulation
        
        ctx = {}
        start_time = time.time()
        
        # This should trigger rate limiting and retry once (actual _request function will handle retry)
        with patch('automagik.tools.airtable.tool.time.sleep'):  # Speed up the test
            result = await list_records(ctx, table="tblTest", base_id="appTest")
        
        end_time = time.time()
        duration = end_time - start_time
        
        assert result["success"] is True
        assert call_count == 2  # Should have made exactly 2 calls (first fails with 429, second succeeds)
        assert duration < 1.0  # Should complete quickly with mocked sleep


class TestMemoryUsage:
    """Test memory usage patterns."""
    
    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_large_record_set_memory(self, mock_request, monkeypatch):
        """Test memory usage with large record sets."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        # Create many records to test memory usage
        many_records = [
            {
                "id": f"rec{i:05d}",
                "fields": {
                    "Name": f"Record {i}",
                    "Description": f"Description for record {i}",
                    "Status": "Active",
                    "Index": i
                },
                "createdTime": "2024-01-01T00:00:00.000Z"
            }
            for i in range(1000)  # 1000 records
        ]
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"records": many_records}
        mock_request.return_value = mock_response
        
        ctx = {}
        
        # Test that large datasets are handled without memory issues
        result = await list_records(ctx, table="tblTest", base_id="appTest")
        
        assert result["success"] is True
        assert len(result["records"]) == 1000
        
        # Verify we can process the large dataset
        total_index = sum(record["fields"]["Index"] for record in result["records"])
        expected_total = sum(range(1000))  # 0 + 1 + 2 + ... + 999
        assert total_index == expected_total
    
    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_repeated_operations_memory(self, mock_request, monkeypatch):
        """Test memory stability over repeated operations."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "records": [{"id": "rec123", "fields": {"Name": "Test"}}]
        }
        mock_request.return_value = mock_response
        
        ctx = {}
        
        # Perform many repeated operations
        for i in range(100):
            result = await list_records(ctx, table="tblTest", base_id="appTest")
            assert result["success"] is True
            
            # Test that each iteration produces consistent results
            assert len(result["records"]) == 1
            assert result["records"][0]["id"] == "rec123"
        
        # Should complete without memory issues
        assert mock_request.call_count == 100


class TestErrorRecovery:
    """Test error recovery and resilience."""
    
    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_intermittent_failures(self, mock_request, monkeypatch):
        """Test recovery from intermittent failures."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        call_count = 0
        
        def intermittent_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            
            mock_response = Mock()
            
            # Fail every 3rd request
            if call_count % 3 == 0:
                mock_response.status_code = 500
                mock_response.text = "Internal Server Error"
            else:
                mock_response.status_code = 200
                mock_response.json.return_value = {"records": [{"id": f"rec{call_count}", "fields": {"Name": "Test"}}]}
            
            return mock_response
        
        mock_request.side_effect = intermittent_failure
        
        ctx = {}
        
        # Test multiple operations with intermittent failures
        successful_operations = 0
        failed_operations = 0
        
        for i in range(10):
            result = await list_records(ctx, table="tblTest", base_id="appTest")
            
            if result["success"]:
                successful_operations += 1
            else:
                failed_operations += 1
        
        # Should have some successes and some failures
        assert successful_operations > 0
        assert failed_operations > 0
        assert successful_operations + failed_operations == 10
    
    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_timeout_handling(self, mock_request, monkeypatch):
        """Test handling of timeout scenarios."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        def timeout_simulation(*args, **kwargs):
            import requests
            raise requests.Timeout("Request timed out")
        
        mock_request.side_effect = timeout_simulation
        
        ctx = {}
        
        # Should handle timeout gracefully
        result = await list_records(ctx, table="tblTest", base_id="appTest")
        
        assert result["success"] is False
        assert "timeout" in result["error"].lower() or "Request timed out" in result["error"]


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_empty_response_handling(self, mock_request, monkeypatch):
        """Test handling of empty API responses."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"records": []}
        mock_request.return_value = mock_response
        
        ctx = {}
        result = await list_records(ctx, table="tblTest", base_id="appTest")
        
        assert result["success"] is True
        assert result["records"] == []
    
    @patch('automagik.tools.airtable.tool._request')
    @pytest.mark.asyncio
    async def test_malformed_json_response(self, mock_request, monkeypatch):
        """Test handling of malformed JSON responses."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Not valid JSON"
        mock_request.return_value = mock_response
        
        ctx = {}
        result = await list_records(ctx, table="tblTest", base_id="appTest")
        
        assert result["success"] is False
        assert "Invalid JSON" in result["error"] or "json" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_maximum_batch_size_boundary(self, monkeypatch):
        """Test exactly at maximum batch size boundary."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        # Test exactly MAX_RECORDS_PER_BATCH records
        records = [{"Name": f"Record {i}"} for i in range(MAX_RECORDS_PER_BATCH)]
        
        with patch('automagik.tools.airtable.tool._request') as mock_request:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"records": []}
            mock_request.return_value = mock_response
            
            ctx = {}
            result = await create_records(ctx, table="tblTest", records=records, base_id="appTest")
            
            assert result["success"] is True
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_over_maximum_batch_size(self, monkeypatch):
        """Test over maximum batch size boundary."""
        monkeypatch.setattr("automagik.tools.airtable.tool._get_token", lambda: "test_token")
        
        # Test one more than MAX_RECORDS_PER_BATCH records
        records = [{"Name": f"Record {i}"} for i in range(MAX_RECORDS_PER_BATCH + 1)]
        
        ctx = {}
        result = await create_records(ctx, table="tblTest", records=records, base_id="appTest")
        
        assert result["success"] is False
        assert "max 10 records" in result["error"] 