"""Tests for TokenAnalyticsService."""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from typing import Dict, Any, List

from src.services.token_analytics import TokenAnalyticsService


class TestTokenAnalyticsService:
    """Test suite for TokenAnalyticsService."""
    
    @pytest.fixture
    def sample_session_usage_data(self):
        """Sample token usage data for session tests."""
        return [
            {
                "model": "gpt-4",
                "framework": "pydantic_ai",
                "message_count": 3,
                "total_requests": 3,
                "total_request_tokens": 150,
                "total_response_tokens": 300,
                "total_tokens": 450,
                "total_cache_creation_tokens": 50,
                "total_cache_read_tokens": 25,
                "first_usage": datetime(2024, 1, 15, 10, 0, 0),
                "last_usage": datetime(2024, 1, 15, 10, 30, 0)
            },
            {
                "model": "gpt-3.5-turbo",
                "framework": "pydantic_ai",
                "message_count": 2,
                "total_requests": 2,
                "total_request_tokens": 100,
                "total_response_tokens": 200,
                "total_tokens": 300,
                "total_cache_creation_tokens": 0,
                "total_cache_read_tokens": 0,
                "first_usage": datetime(2024, 1, 15, 11, 0, 0),
                "last_usage": datetime(2024, 1, 15, 11, 15, 0)
            }
        ]
    
    @pytest.fixture
    def sample_empty_result(self):
        """Empty database result."""
        return []
    
    @pytest.fixture
    def valid_session_id(self):
        """Valid session UUID."""
        return str(uuid.uuid4())
    
    @pytest.fixture
    def valid_user_id(self):
        """Valid user UUID."""
        return str(uuid.uuid4())
    
    def test_get_session_usage_summary_success(self, sample_session_usage_data, valid_session_id):
        """Test successful session usage summary retrieval."""
        with patch('src.services.token_analytics.execute_query') as mock_query, \
             patch('src.services.token_analytics.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.return_value = uuid.UUID(valid_session_id)
            mock_query.return_value = sample_session_usage_data
            
            # Call method
            result = TokenAnalyticsService.get_session_usage_summary(valid_session_id)
            
            # Assertions
            assert result["session_id"] == valid_session_id
            assert result["total_tokens"] == 750  # 450 + 300
            assert result["total_requests"] == 5   # 3 + 2
            assert len(result["models"]) == 2
            
            # Check model breakdown
            gpt4_model = next(m for m in result["models"] if m["model"] == "gpt-4")
            assert gpt4_model["total_tokens"] == 450
            assert gpt4_model["framework"] == "pydantic_ai"
            assert gpt4_model["cache_creation_tokens"] == 50
            
            # Check summary
            summary = result["summary"]
            assert summary["message_count"] == 5  # 3 + 2
            assert summary["unique_models"] == 2
            assert summary["total_request_tokens"] == 250  # 150 + 100
            assert summary["total_response_tokens"] == 500  # 300 + 200
            assert summary["total_cache_tokens"] == 75     # 50 + 25 + 0 + 0
            assert "analysis_timestamp" in summary
    
    def test_get_session_usage_summary_empty_result(self, sample_empty_result, valid_session_id):
        """Test session usage summary with no usage data."""
        with patch('src.services.token_analytics.execute_query') as mock_query, \
             patch('src.services.token_analytics.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.return_value = uuid.UUID(valid_session_id)
            mock_query.return_value = sample_empty_result
            
            # Call method
            result = TokenAnalyticsService.get_session_usage_summary(valid_session_id)
            
            # Assertions
            assert result["session_id"] == valid_session_id
            assert result["total_tokens"] == 0
            assert result["total_requests"] == 0
            assert result["models"] == []
            assert result["summary"]["message_count"] == 0
            assert result["summary"]["unique_models"] == 0
    
    def test_get_session_usage_summary_invalid_session_id(self):
        """Test session usage summary with invalid session ID."""
        with patch('src.services.token_analytics.safe_uuid') as mock_safe_uuid:
            
            # Setup mock to return None for invalid UUID
            mock_safe_uuid.return_value = None
            
            # Call method
            result = TokenAnalyticsService.get_session_usage_summary("invalid-uuid")
            
            # Assertions
            assert "error" in result
            assert result["error"] == "Invalid session ID"
    
    def test_get_session_usage_summary_database_error(self, valid_session_id):
        """Test session usage summary with database error."""
        with patch('src.services.token_analytics.execute_query') as mock_query, \
             patch('src.services.token_analytics.safe_uuid') as mock_safe_uuid, \
             patch('src.services.token_analytics.logger') as mock_logger:
            
            # Setup mocks
            mock_safe_uuid.return_value = uuid.UUID(valid_session_id)
            mock_query.side_effect = Exception("Database connection failed")
            
            # Call method
            result = TokenAnalyticsService.get_session_usage_summary(valid_session_id)
            
            # Assertions
            assert "error" in result
            assert "Database connection failed" in result["error"]
            mock_logger.error.assert_called()
    
    def test_get_user_usage_summary_success(self, valid_user_id):
        """Test successful user usage summary retrieval."""
        sample_user_data = [
            {
                "model": "gpt-4",
                "framework": "pydantic_ai",
                "session_count": 2,
                "message_count": 5,
                "total_requests": 5,
                "total_request_tokens": 250,
                "total_response_tokens": 500,
                "total_tokens": 750,
                "first_usage": datetime(2024, 1, 15, 10, 0, 0),
                "last_usage": datetime(2024, 1, 15, 12, 0, 0)
            }
        ]
        
        with patch('src.services.token_analytics.execute_query') as mock_query, \
             patch('src.services.token_analytics.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.return_value = uuid.UUID(valid_user_id)
            mock_query.return_value = sample_user_data
            
            # Call method
            result = TokenAnalyticsService.get_user_usage_summary(valid_user_id, days=30)
            
            # Assertions
            assert result["user_id"] == valid_user_id
            assert result["days_analyzed"] == 30
            assert result["total_tokens"] == 750
            assert len(result["models"]) == 1
            assert result["summary"]["session_count"] == 2
            assert result["summary"]["message_count"] == 5
            assert result["summary"]["unique_models"] == 1
    
    def test_get_agent_usage_summary_success(self):
        """Test successful agent usage summary retrieval."""
        agent_id = 123
        sample_agent_data = [
            {
                "model": "gpt-4",
                "framework": "pydantic_ai",
                "session_count": 3,
                "user_count": 2,
                "message_count": 8,
                "total_requests": 8,
                "total_request_tokens": 400,
                "total_response_tokens": 800,
                "total_tokens": 1200,
                "first_usage": datetime(2024, 1, 15, 9, 0, 0),
                "last_usage": datetime(2024, 1, 15, 15, 0, 0)
            }
        ]
        
        with patch('src.services.token_analytics.execute_query') as mock_query:
            
            # Setup mock
            mock_query.return_value = sample_agent_data
            
            # Call method
            result = TokenAnalyticsService.get_agent_usage_summary(agent_id, days=7)
            
            # Assertions
            assert result["agent_id"] == agent_id
            assert result["days_analyzed"] == 7
            assert result["total_tokens"] == 1200
            assert len(result["models"]) == 1
            assert result["summary"]["session_count"] == 3
            assert result["summary"]["user_count"] == 2
            assert result["summary"]["message_count"] == 8
    
    def test_get_top_usage_sessions_success(self):
        """Test successful top usage sessions retrieval."""
        sample_top_sessions = [
            {
                "session_id": uuid.uuid4(),
                "message_count": 10,
                "total_tokens": 1500,
                "request_tokens": 600,
                "response_tokens": 900,
                "session_start": datetime(2024, 1, 15, 10, 0, 0),
                "session_end": datetime(2024, 1, 15, 11, 0, 0),
                "unique_models": 2,
                "models_used": ["gpt-4", "gpt-3.5-turbo"]
            },
            {
                "session_id": uuid.uuid4(),
                "message_count": 5,
                "total_tokens": 800,
                "request_tokens": 300,
                "response_tokens": 500,
                "session_start": datetime(2024, 1, 15, 14, 0, 0),
                "session_end": datetime(2024, 1, 15, 14, 30, 0),
                "unique_models": 1,
                "models_used": ["gpt-4"]
            }
        ]
        
        with patch('src.services.token_analytics.execute_query') as mock_query:
            
            # Setup mock
            mock_query.return_value = sample_top_sessions
            
            # Call method
            result = TokenAnalyticsService.get_top_usage_sessions(limit=10, days=7)
            
            # Assertions
            assert len(result) == 2
            assert result[0]["total_tokens"] == 1500  # Highest usage first
            assert result[0]["unique_models"] == 2
            assert result[1]["total_tokens"] == 800
            assert result[1]["unique_models"] == 1
    
    def test_get_top_usage_sessions_empty_result(self):
        """Test top usage sessions with no data."""
        with patch('src.services.token_analytics.execute_query') as mock_query:
            
            # Setup mock
            mock_query.return_value = []
            
            # Call method
            result = TokenAnalyticsService.get_top_usage_sessions()
            
            # Assertions
            assert result == []
    
    def test_get_top_usage_sessions_database_error(self):
        """Test top usage sessions with database error."""
        with patch('src.services.token_analytics.execute_query') as mock_query, \
             patch('src.services.token_analytics.logger') as mock_logger:
            
            # Setup mock
            mock_query.side_effect = Exception("Query timeout")
            
            # Call method
            result = TokenAnalyticsService.get_top_usage_sessions()
            
            # Assertions
            assert result == []
            mock_logger.error.assert_called()
    
    def test_query_parameters_user_summary_with_days(self, valid_user_id):
        """Test that user summary query includes correct date filtering."""
        with patch('src.services.token_analytics.execute_query') as mock_query, \
             patch('src.services.token_analytics.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.return_value = uuid.UUID(valid_user_id)
            mock_query.return_value = []
            
            # Call method with specific days
            TokenAnalyticsService.get_user_usage_summary(valid_user_id, days=14)
            
            # Verify query was called with date parameter
            args, kwargs = mock_query.call_args
            query, params = args
            
            # Should have user_id and start_date parameters
            assert len(params) == 2
            assert params[0] == uuid.UUID(valid_user_id)
            assert isinstance(params[1], datetime)
            assert "AND created_at >= %s" in query
    
    def test_query_parameters_user_summary_no_days(self, valid_user_id):
        """Test that user summary query without days filter works correctly."""
        with patch('src.services.token_analytics.execute_query') as mock_query, \
             patch('src.services.token_analytics.safe_uuid') as mock_safe_uuid:
            
            # Setup mocks
            mock_safe_uuid.return_value = uuid.UUID(valid_user_id)
            mock_query.return_value = []
            
            # Call method without days (None)
            TokenAnalyticsService.get_user_usage_summary(valid_user_id, days=None)
            
            # Verify query was called without date parameter
            args, kwargs = mock_query.call_args
            query, params = args
            
            # Should only have user_id parameter
            assert len(params) == 1
            assert params[0] == uuid.UUID(valid_user_id)
            assert "AND created_at >= %s" not in query