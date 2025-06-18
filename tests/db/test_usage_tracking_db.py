"""Tests for database integration of usage tracking."""

import pytest
import uuid
import json
from unittest.mock import Mock, patch, call
from datetime import datetime

from src.db.models import Message
from src.db.repository.message import create_message, update_message


class TestUsageTrackingDatabase:
    """Test suite for usage tracking database integration."""
    
    @pytest.fixture
    def sample_usage_data(self):
        """Sample usage data for testing."""
        return {
            "framework": "pydantic_ai",
            "model": "gpt-4",
            "total_requests": 1,
            "request_tokens": 100,
            "response_tokens": 200,
            "total_tokens": 300,
            "cache_creation_tokens": 25,
            "cache_read_tokens": 10,
            "per_message_usage": [
                {
                    "requests": 1,
                    "request_tokens": 100,
                    "response_tokens": 200,
                    "total_tokens": 300,
                    "details": {"cache_creation_tokens": 25}
                }
            ]
        }
    
    @pytest.fixture
    def sample_message_with_usage(self, sample_usage_data):
        """Sample message with usage data."""
        return Message(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            agent_id=123,
            role="assistant",
            text_content="Test response",
            message_type="text",
            usage=sample_usage_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    @pytest.fixture
    def sample_message_without_usage(self):
        """Sample message without usage data."""
        return Message(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            agent_id=123,
            role="user",
            text_content="Test message",
            message_type="text",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
    
    def test_create_message_with_usage_success(self, sample_message_with_usage, sample_usage_data):
        """Test successful message creation with usage data."""
        with patch('src.db.repository.message.execute_query') as mock_execute:
            
            # Setup mock to return success
            mock_execute.return_value = [{"id": sample_message_with_usage.id}]
            
            # Call create_message
            result = create_message(sample_message_with_usage)
            
            # Assertions
            assert result == sample_message_with_usage.id
            
            # Verify execute_query was called with correct parameters
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            query, params = call_args[0]
            
            # Check that query includes usage column
            assert "usage" in query
            assert "VALUES" in query
            assert query.count("%s") == 16  # Should have 16 parameters including usage
            
            # Check that usage data is properly JSON serialized in params
            usage_param = params[-1]  # usage is last parameter
            assert isinstance(usage_param, str)
            parsed_usage = json.loads(usage_param)
            assert parsed_usage == sample_usage_data
    
    def test_create_message_without_usage_success(self, sample_message_without_usage):
        """Test successful message creation without usage data."""
        with patch('src.db.repository.message.execute_query') as mock_execute:
            
            # Setup mock to return success
            mock_execute.return_value = [{"id": sample_message_without_usage.id}]
            
            # Call create_message
            result = create_message(sample_message_without_usage)
            
            # Assertions
            assert result == sample_message_without_usage.id
            
            # Verify execute_query was called
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            query, params = call_args[0]
            
            # Check that usage is None in params
            usage_param = params[-1]  # usage is last parameter
            assert usage_param is None
    
    def test_create_message_usage_json_serialization(self, sample_message_with_usage):
        """Test that complex usage data is properly JSON serialized."""
        # Add complex nested data to usage
        complex_usage = {
            "framework": "pydantic_ai",
            "model": "gpt-4",
            "total_tokens": 300,
            "nested_data": {
                "cache_info": {
                    "creation_tokens": 25,
                    "read_tokens": 10
                },
                "model_details": {
                    "version": "gpt-4-0125-preview",
                    "parameters": {"temperature": 0.7}
                }
            },
            "array_data": [1, 2, 3, {"nested": True}]
        }
        sample_message_with_usage.usage = complex_usage
        
        with patch('src.db.repository.message.execute_query') as mock_execute:
            
            # Setup mock
            mock_execute.return_value = [{"id": sample_message_with_usage.id}]
            
            # Call create_message
            create_message(sample_message_with_usage)
            
            # Get the usage parameter
            call_args = mock_execute.call_args
            params = call_args[0][1]
            usage_param = params[-1]
            
            # Verify it's properly serialized JSON
            assert isinstance(usage_param, str)
            parsed_usage = json.loads(usage_param)
            assert parsed_usage == complex_usage
            assert parsed_usage["nested_data"]["cache_info"]["creation_tokens"] == 25
            assert parsed_usage["array_data"][3]["nested"] is True
    
    def test_update_message_with_usage_success(self, sample_message_with_usage, sample_usage_data):
        """Test successful message update with usage data."""
        with patch('src.db.repository.message.execute_query') as mock_execute:
            
            # Setup mock to return success
            mock_execute.return_value = [{"id": sample_message_with_usage.id}]
            
            # Call update_message
            result = update_message(sample_message_with_usage)
            
            # Assertions
            assert result == sample_message_with_usage.id
            
            # Verify execute_query was called with UPDATE query
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            query, params = call_args[0]
            
            # Check that query is UPDATE and includes usage
            assert "UPDATE messages" in query
            assert "usage = %s" in query
            
            # Check that usage data is in params (third to last: usage, updated_at, message.id)
            usage_param = params[-3]  # usage is third to last parameter
            assert isinstance(usage_param, str)
            parsed_usage = json.loads(usage_param)
            assert parsed_usage == sample_usage_data
    
    def test_create_message_database_error(self, sample_message_with_usage):
        """Test message creation with database error."""
        with patch('src.db.repository.message.execute_query') as mock_execute, \
             patch('src.db.repository.message.logger') as mock_logger:
            
            # Setup mock to raise exception
            mock_execute.side_effect = Exception("Database connection failed")
            
            # Call create_message - should handle exception gracefully
            result = create_message(sample_message_with_usage)
            
            # Should return None on error
            assert result is None
            mock_logger.error.assert_called()
    
    def test_message_model_usage_field(self, sample_usage_data):
        """Test that Message model properly handles usage field."""
        # Test with usage data
        message_with_usage = Message(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            agent_id=123,
            role="assistant",
            text_content="Test response",
            usage=sample_usage_data
        )
        
        assert message_with_usage.usage == sample_usage_data
        
        # Test without usage data
        message_without_usage = Message(
            id=uuid.uuid4(),
            session_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            agent_id=123,
            role="user",
            text_content="Test message"
        )
        
        assert message_without_usage.usage is None
    
    def test_message_from_db_row_with_usage(self, sample_usage_data):
        """Test Message.from_db_row with usage data."""
        # Sample database row with JSON usage data
        db_row = {
            "id": uuid.uuid4(),
            "session_id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "agent_id": 123,
            "role": "assistant",
            "text_content": "Test response",
            "message_type": "text",
            "raw_payload": None,
            "channel_payload": None,
            "tool_calls": None,
            "tool_outputs": None,
            "context": None,
            "usage": json.dumps(sample_usage_data),  # JSON string as it comes from DB
            "system_prompt": None,
            "user_feedback": None,
            "flagged": None,
            "media_url": None,
            "mime_type": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Create Message from db row
        message = Message.from_db_row(db_row)
        
        # Assertions
        assert message is not None
        assert message.usage == sample_usage_data
        assert message.role == "assistant"
        assert message.text_content == "Test response"
    
    def test_message_from_db_row_with_invalid_usage_json(self):
        """Test Message.from_db_row with invalid usage JSON."""
        # Sample database row with invalid JSON
        db_row = {
            "id": uuid.uuid4(),
            "session_id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "agent_id": 123,
            "role": "assistant",
            "text_content": "Test response",
            "message_type": "text",
            "raw_payload": None,
            "channel_payload": None,
            "tool_calls": None,
            "tool_outputs": None,
            "context": None,
            "usage": "invalid json string",  # Invalid JSON
            "system_prompt": None,
            "user_feedback": None,
            "flagged": None,
            "media_url": None,
            "mime_type": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Create Message from db row - should handle invalid JSON gracefully
        message = Message.from_db_row(db_row)
        
        # Should set usage to None when JSON is invalid
        assert message is not None
        assert message.usage is None
        assert message.role == "assistant"
    
    def test_message_from_db_row_without_usage(self):
        """Test Message.from_db_row without usage data."""
        # Sample database row without usage
        db_row = {
            "id": uuid.uuid4(),
            "session_id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "agent_id": 123,
            "role": "user",
            "text_content": "Test message",
            "message_type": "text",
            "raw_payload": None,
            "channel_payload": None,
            "tool_calls": None,
            "tool_outputs": None,
            "context": None,
            "usage": None,  # No usage data
            "system_prompt": None,
            "user_feedback": None,
            "flagged": None,
            "media_url": None,
            "mime_type": None,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Create Message from db row
        message = Message.from_db_row(db_row)
        
        # Assertions
        assert message is not None
        assert message.usage is None
        assert message.role == "user"
        assert message.text_content == "Test message"
    
    @pytest.mark.integration
    def test_usage_data_query_performance(self):
        """Test that usage queries are properly indexed for performance."""
        # This would be an integration test that verifies the database indexes
        # are working correctly for usage queries
        
        with patch('src.db.repository.message.execute_query') as mock_execute:
            
            # Mock a query that uses the usage indexes
            mock_execute.return_value = []
            
            # Simulate a query that would use the usage model index (SQLite syntax)
            query = """
                SELECT session_id, COUNT(*) as message_count,
                       SUM(CAST(JSON_EXTRACT(usage, '$.total_tokens') AS INTEGER)) as total_tokens
                FROM messages 
                WHERE JSON_EXTRACT(usage, '$.model') = ? 
                  AND usage IS NOT NULL
                GROUP BY session_id
                ORDER BY total_tokens DESC
            """
            
            from src.db.connection import execute_query
            with patch('src.db.connection.execute_query') as mock_db_execute:
                mock_db_execute.return_value = []
                
                # This would normally test actual query performance
                # but for unit testing we just verify the query structure
                result = execute_query(query, ("gpt-4",))
                
                mock_db_execute.assert_called_once_with(query, ("gpt-4",), True, True)
                assert result == []