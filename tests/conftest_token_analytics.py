"""Test configuration and fixtures for token analytics tests."""

import pytest
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock


@pytest.fixture
def sample_token_usage_basic():
    """Basic token usage data for testing."""
    return {
        "framework": "pydantic_ai",
        "model": "gpt-4",
        "total_requests": 1,
        "request_tokens": 100,
        "response_tokens": 200,
        "total_tokens": 300,
        "cache_creation_tokens": 0,
        "cache_read_tokens": 0,
        "per_message_usage": [
            {
                "requests": 1,
                "request_tokens": 100,
                "response_tokens": 200,
                "total_tokens": 300,
                "details": None
            }
        ]
    }


@pytest.fixture
def sample_token_usage_with_cache():
    """Token usage data with cache information."""
    return {
        "framework": "pydantic_ai",
        "model": "gpt-4",
        "total_requests": 2,
        "request_tokens": 150,
        "response_tokens": 300,
        "total_tokens": 450,
        "cache_creation_tokens": 25,
        "cache_read_tokens": 15,
        "per_message_usage": [
            {
                "requests": 1,
                "request_tokens": 75,
                "response_tokens": 150,
                "total_tokens": 225,
                "details": {"cache_creation_tokens": 25}
            },
            {
                "requests": 1,
                "request_tokens": 75,
                "response_tokens": 150,
                "total_tokens": 225,
                "details": {"cache_read_tokens": 15}
            }
        ]
    }


@pytest.fixture
def sample_multi_model_usage():
    """Sample usage data for multiple models."""
    return [
        {
            "model": "gpt-4",
            "framework": "pydantic_ai",
            "message_count": 3,
            "total_requests": 3,
            "total_request_tokens": 150,
            "total_response_tokens": 300,
            "total_tokens": 450,
            "total_cache_creation_tokens": 25,
            "total_cache_read_tokens": 10,
            "first_usage": datetime(2024, 1, 15, 10, 0, 0),
            "last_usage": datetime(2024, 1, 15, 10, 30, 0)
        },
        {
            "model": "gpt-3.5-turbo",
            "framework": "pydantic_ai",
            "message_count": 2,
            "total_requests": 2,
            "total_request_tokens": 80,
            "total_response_tokens": 160,
            "total_tokens": 240,
            "total_cache_creation_tokens": 0,
            "total_cache_read_tokens": 0,
            "first_usage": datetime(2024, 1, 15, 11, 0, 0),
            "last_usage": datetime(2024, 1, 15, 11, 15, 0)
        }
    ]


@pytest.fixture
def sample_session_analytics_response():
    """Complete session analytics response structure."""
    session_id = str(uuid.uuid4())
    return {
        "session_id": session_id,
        "total_tokens": 690,
        "total_requests": 5,
        "models": [
            {
                "model": "gpt-4",
                "framework": "pydantic_ai",
                "message_count": 3,
                "total_requests": 3,
                "request_tokens": 150,
                "response_tokens": 300,
                "total_tokens": 450,
                "cache_creation_tokens": 25,
                "cache_read_tokens": 10,
                "first_usage": "2024-01-15T10:00:00",
                "last_usage": "2024-01-15T10:30:00"
            },
            {
                "model": "gpt-3.5-turbo",
                "framework": "pydantic_ai",
                "message_count": 2,
                "total_requests": 2,
                "request_tokens": 80,
                "response_tokens": 160,
                "total_tokens": 240,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "first_usage": "2024-01-15T11:00:00",
                "last_usage": "2024-01-15T11:15:00"
            }
        ],
        "summary": {
            "message_count": 5,
            "unique_models": 2,
            "total_request_tokens": 230,
            "total_response_tokens": 460,
            "total_cache_tokens": 35,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    }


@pytest.fixture
def sample_user_analytics_response():
    """Complete user analytics response structure."""
    user_id = str(uuid.uuid4())
    return {
        "user_id": user_id,
        "days_analyzed": 30,
        "total_tokens": 1500,
        "models": [
            {
                "model": "gpt-4",
                "framework": "pydantic_ai",
                "session_count": 3,
                "message_count": 8,
                "total_requests": 8,
                "request_tokens": 600,
                "response_tokens": 900,
                "total_tokens": 1500,
                "first_usage": "2024-01-01T10:00:00",
                "last_usage": "2024-01-15T15:00:00"
            }
        ],
        "summary": {
            "session_count": 3,
            "message_count": 8,
            "unique_models": 1,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    }


@pytest.fixture
def sample_agent_analytics_response():
    """Complete agent analytics response structure."""
    return {
        "agent_id": 123,
        "days_analyzed": 7,
        "total_tokens": 2400,
        "models": [
            {
                "model": "gpt-4",
                "framework": "pydantic_ai",
                "session_count": 5,
                "user_count": 3,
                "message_count": 15,
                "total_requests": 15,
                "request_tokens": 900,
                "response_tokens": 1500,
                "total_tokens": 2400,
                "first_usage": "2024-01-10T09:00:00",
                "last_usage": "2024-01-15T17:00:00"
            }
        ],
        "summary": {
            "session_count": 5,
            "user_count": 3,
            "message_count": 15,
            "unique_models": 1,
            "analysis_timestamp": datetime.utcnow().isoformat()
        }
    }


@pytest.fixture
def sample_top_sessions_response():
    """Sample top usage sessions response."""
    return [
        {
            "session_id": str(uuid.uuid4()),
            "message_count": 12,
            "total_tokens": 1800,
            "request_tokens": 720,
            "response_tokens": 1080,
            "session_start": datetime(2024, 1, 15, 9, 0, 0),
            "session_end": datetime(2024, 1, 15, 10, 0, 0),
            "unique_models": 2,
            "models_used": ["gpt-4", "gpt-3.5-turbo"]
        },
        {
            "session_id": str(uuid.uuid4()),
            "message_count": 8,
            "total_tokens": 1200,
            "request_tokens": 480,
            "response_tokens": 720,
            "session_start": datetime(2024, 1, 15, 14, 0, 0),
            "session_end": datetime(2024, 1, 15, 14, 45, 0),
            "unique_models": 1,
            "models_used": ["gpt-4"]
        }
    ]


@pytest.fixture
def mock_pydantic_ai_usage():
    """Mock PydanticAI usage object."""
    mock_usage = Mock()
    mock_usage.requests = 1
    mock_usage.request_tokens = 100
    mock_usage.response_tokens = 200
    mock_usage.total_tokens = 300
    mock_usage.details = {"cache_creation_tokens": 25, "cache_read_tokens": 10}
    return mock_usage


@pytest.fixture
def mock_pydantic_ai_result(mock_pydantic_ai_usage):
    """Mock PydanticAI result with usage information."""
    mock_result = Mock()
    mock_result.output = "Test agent response"
    
    # Create mock message with usage
    mock_message = Mock()
    mock_message.usage = mock_pydantic_ai_usage
    mock_message.tool_calls = None
    mock_message.tool_call_id = None
    mock_message.content = None
    
    # Mock all_messages method
    mock_result.all_messages.return_value = [mock_message]
    
    return mock_result


@pytest.fixture
def test_session_ids():
    """Generate test session IDs."""
    return [str(uuid.uuid4()) for _ in range(5)]


@pytest.fixture
def test_user_ids():
    """Generate test user IDs."""
    return [str(uuid.uuid4()) for _ in range(3)]


@pytest.fixture
def test_agent_ids():
    """Generate test agent IDs."""
    return [101, 102, 103, 104, 105]


@pytest.fixture
def date_ranges():
    """Common date ranges for testing."""
    now = datetime.utcnow()
    return {
        "last_7_days": now - timedelta(days=7),
        "last_30_days": now - timedelta(days=30),
        "last_90_days": now - timedelta(days=90),
        "today": now.replace(hour=0, minute=0, second=0, microsecond=0),
        "yesterday": (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    }


# Mark configurations for different test types
def pytest_configure(config):
    """Configure pytest markers for token analytics tests."""
    config.addinivalue_line(
        "markers", "token_analytics: mark test as related to token analytics"
    )
    config.addinivalue_line(
        "markers", "usage_tracking: mark test as related to usage tracking"
    )
    config.addinivalue_line(
        "markers", "analytics_api: mark test as related to analytics API endpoints"
    )
    config.addinivalue_line(
        "markers", "analytics_service: mark test as related to TokenAnalyticsService"
    )


# Auto-apply markers based on test file location
def pytest_collection_modifyitems(config, items):
    """Automatically apply markers based on test file paths."""
    for item in items:
        # Apply token_analytics marker to all analytics-related tests
        if "analytics" in str(item.fspath) or "usage_tracking" in str(item.fspath):
            item.add_marker(pytest.mark.token_analytics)
        
        # Apply specific markers based on file names
        if "test_token_analytics" in str(item.fspath):
            item.add_marker(pytest.mark.analytics_service)
        elif "test_analytics_routes" in str(item.fspath):
            item.add_marker(pytest.mark.analytics_api)
        elif "usage_tracking" in str(item.fspath):
            item.add_marker(pytest.mark.usage_tracking)