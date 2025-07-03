import pytest
from fastapi.testclient import TestClient
from automagik.main import app
from automagik.config import settings

@pytest.fixture(scope="session")
def client():
    """
    Create a test client with API key authentication
    """
    # This will be shared across all tests
    client = TestClient(app)
    
    # Add API key to headers for all requests
    original_request = client.request
    
    def request_with_auth(*args, **kwargs):
        # Add API key to headers if not already present
        headers = kwargs.get("headers", {})
        if headers is None:
            headers = {}
        headers["x-api-key"] = settings.AUTOMAGIK_API_KEY
        kwargs["headers"] = headers
        return original_request(*args, **kwargs)
    
    # Replace the request method with our custom one
    client.request = request_with_auth
    
    return client

@pytest.fixture(scope="session", autouse=True)
def setup_and_teardown():
    """
    Setup and teardown operations for the entire test session
    """
    # Setup before all tests
    print("\nSetting up test environment...")
    
    # Let the tests run
    yield
    
    # Teardown after all tests
    print("\nCleaning up test environment...")
    # Any cleanup code would go here 