"""Test configuration for pytest."""
import os
from pathlib import Path
from dotenv import load_dotenv
import pytest
from unittest.mock import Mock, AsyncMock
from automagik.agents.models.dependencies import AutomagikAgentsDependencies

# Configure pytest-asyncio
pytest_plugins = ('pytest_asyncio',)

# Get the project root directory
project_root = Path(__file__).parent.parent

# Load environment variables from .env file
env_path = project_root / '.env'
load_dotenv(env_path)

# Verify OMIE credentials are loaded
if not os.getenv("OMIE_APP_KEY") or not os.getenv("OMIE_APP_SECRET"):
    print("Warning: OMIE credentials not found in .env file")

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers",
        "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )

@pytest.fixture
def optimized_test_dependencies():
    """Create optimized dependencies for testing that skip expensive operations."""
    return AutomagikAgentsDependencies(
        test_mode=True,
        disable_memory_operations=True,
        mock_external_apis=True,
        model_name="gpt-4.1-mini",  # Use faster model for tests
        model_settings={"temperature": 0.0}  # Deterministic responses
    )

@pytest.fixture
def mock_graphiti_client():
    """Mock Graphiti client to avoid expensive memory operations."""
    mock_client = AsyncMock()
    mock_client.add_episode = AsyncMock(return_value={"success": True, "episode_id": "test-episode"})
    mock_client.search = AsyncMock(return_value={"nodes": [], "edges": []})
    return mock_client

@pytest.fixture
def mock_blackpearl_api():
    """Mock BlackPearl API to avoid external calls during testing."""
    mock_api = Mock()
    mock_api.search_contacts = Mock(return_value={"count": 0, "results": []})
    mock_api.create_contact = Mock(return_value={"id": 999, "name": "Test Contact"})
    mock_api.search_clients = Mock(return_value={"count": 0, "results": []})
    return mock_api

@pytest.fixture(autouse=True)
def fast_test_environment():
    """Automatically configure fast test environment for all tests."""
    # Set environment variables for faster testing
    os.environ["DISABLE_MEMORY_OPERATIONS"] = "true"
    os.environ["MOCK_EXTERNAL_APIS"] = "true"
    os.environ["TEST_MODE"] = "true"
    
    yield
    
    # Cleanup
    os.environ.pop("DISABLE_MEMORY_OPERATIONS", None)
    os.environ.pop("MOCK_EXTERNAL_APIS", None)
    os.environ.pop("TEST_MODE", None) 