import pytest
import uuid
import os
from unittest.mock import patch
from src.agents.models.agent_factory import AgentFactory

# Global variables
available_agents = []

def setup_module():
    """Setup before running tests - discover available agents"""
    global available_agents
    
    # Initialize agent factory
    AgentFactory.discover_agents()
    available_agents = AgentFactory.list_available_agents()
    
    # Ensure we have at least one agent available
    if not available_agents:
        pytest.skip("No agents available for testing")

def test_list_agents(client):
    """Test listing available agents endpoint"""
    response = client.get("/api/v1/agent/list")
    assert response.status_code == 200
    
    # Check response data
    agents = response.json()
    assert isinstance(agents, list)
    
    # Each agent should have name and description fields
    for agent in agents:
        assert "name" in agent
        assert "description" in agent
    
    # The API should return at least some agents
    assert len(agents) > 0
    
    # Check that basic agents are available
    api_names = [agent["name"] for agent in agents]
    
    # At minimum, we should have 'simple' agent available
    assert "simple" in api_names
    
    # If we have discovered agents, check that some of them are in the API
    # Note: API only returns agents that have been registered in the database
    factory_names = available_agents
    
    # Count how many factory agents are in the API
    matching_agents = [name for name in factory_names if name in api_names]
    
    # We should have at least some registered agents in the API
    # This accounts for the fact that agents are only registered when first used
    # Expect at least 1 agent, or 20% of discovered agents, whichever is lower
    min_expected = max(1, min(2, len(factory_names) // 5))
    assert len(matching_agents) >= min_expected, f"Expected at least {min_expected} agents in API, but only found {len(matching_agents)}: {matching_agents}. Available factory agents: {factory_names}, API agents: {api_names}"

def test_run_agent_simple(client):
    """Test running an agent with simple parameters"""
    global available_agents
    
    # Skip if no agents available
    if not available_agents:
        pytest.skip("No agents available for testing")
    
    # Get the first available agent
    test_agent = available_agents[0]
    
    # Simple request with just a message
    request_data = {
        "message_content": "Hello, agent! This is a test message.",
        "message_type": "text",
    }
    
    response = client.post(f"/api/v1/agent/{test_agent}/run", json=request_data)
    assert response.status_code == 200
    
    # Check response structure
    data = response.json()
    assert "message" in data
    assert "session_id" in data
    assert "success" in data
    
    # Content should be non-empty
    assert data["message"]
    assert isinstance(data["message"], str)

def test_run_agent_with_session(client):
    """Test running an agent with a session"""
    global available_agents
    
    # Skip if no agents available
    if not available_agents:
        pytest.skip("No agents available for testing")
    
    # Get the first available agent
    test_agent = available_agents[0]
    
    # Create a session name
    session_name = f"test_session_{uuid.uuid4().hex[:8]}"
    
    # Request with session name
    request_data = {
        "message_content": "Remember this session test.",
        "message_type": "text",
        "session_name": session_name
    }
    
    response = client.post(f"/api/v1/agent/{test_agent}/run", json=request_data)
    assert response.status_code == 200
    
    # Check response structure
    data = response.json()
    assert "message" in data
    assert "session_id" in data
    
    # Verify session data
    session_id = data["session_id"]
    
    # Run another request with the same session
    request_data = {
        "message_content": "What did I ask you to remember?",
        "message_type": "text",
        "session_id": session_id
    }
    
    response = client.post(f"/api/v1/agent/{test_agent}/run", json=request_data)
    assert response.status_code == 200
    
    # Session ID should match
    data = response.json()
    assert data["session_id"] == session_id
    
    # Clean up the session
    client.delete(f"/api/v1/sessions/{session_id}")

def test_run_nonexistent_agent(client):
    """Test running an agent that doesn't exist"""
    nonexistent_agent = f"nonexistent_agent_{uuid.uuid4().hex[:8]}"
    
    request_data = {
        "message_content": "Hello",
        "message_type": "text"
    }
    
    response = client.post(f"/api/v1/agent/{nonexistent_agent}/run", json=request_data)
    assert response.status_code == 404

def test_run_agent_with_parameters(client):
    """Test running an agent with custom parameters"""
    global available_agents
    
    # Skip if no agents available
    if not available_agents:
        pytest.skip("No agents available for testing")
    
    # Get the first available agent
    test_agent = available_agents[0]
    
    # Request with custom parameters
    request_data = {
        "message_content": "Testing with parameters",
        "message_type": "text",
        "parameters": {
            "temperature": 0.7,
            "max_tokens": 100
        }
    }
    
    response = client.post(f"/api/v1/agent/{test_agent}/run", json=request_data)
    assert response.status_code == 200
    
    # Check response structure
    data = response.json()
    assert "message" in data

def test_list_agents_with_am_agents_names_filter(client):
    """Test that listing agents respects AM_AGENTS_NAMES environment variable"""
    
    # First, get the current list of all agents without filter
    response = client.get("/api/v1/agent/list")
    assert response.status_code == 200
    all_agents = response.json()
    all_agent_names = [agent["name"] for agent in all_agents]
    
    # Ensure we have multiple agents for a meaningful test
    if len(all_agent_names) < 2:
        pytest.skip("Need at least 2 agents for this test")
    
    # Pick the first agent to include in our filter
    test_agent_name = all_agent_names[0]
    
    # Test with AM_AGENTS_NAMES set to a single agent
    with patch.dict(os.environ, {"AM_AGENTS_NAMES": test_agent_name}):
        # Need to patch the settings object as well since it's already loaded
        from src.config import settings
        original_value = settings.AM_AGENTS_NAMES
        try:
            settings.AM_AGENTS_NAMES = test_agent_name
            
            response = client.get("/api/v1/agent/list")
            assert response.status_code == 200
            filtered_agents = response.json()
            filtered_agent_names = [agent["name"] for agent in filtered_agents]
            
            # Should only return the specified agent
            assert len(filtered_agent_names) == 1
            assert test_agent_name in filtered_agent_names
        finally:
            # Restore original value
            settings.AM_AGENTS_NAMES = original_value
    
    # Test with multiple agents in AM_AGENTS_NAMES
    if len(all_agent_names) >= 3:
        # Pick first two agents
        test_agents = f"{all_agent_names[0]},{all_agent_names[1]}"
        
        with patch.dict(os.environ, {"AM_AGENTS_NAMES": test_agents}):
            from src.config import settings
            original_value = settings.AM_AGENTS_NAMES
            try:
                settings.AM_AGENTS_NAMES = test_agents
                
                response = client.get("/api/v1/agent/list")
                assert response.status_code == 200
                filtered_agents = response.json()
                filtered_agent_names = [agent["name"] for agent in filtered_agents]
                
                # Should return exactly 2 agents
                assert len(filtered_agent_names) == 2
                assert all_agent_names[0] in filtered_agent_names
                assert all_agent_names[1] in filtered_agent_names
            finally:
                # Restore original value
                settings.AM_AGENTS_NAMES = original_value
    
    # Test with empty AM_AGENTS_NAMES (should return all agents)
    with patch.dict(os.environ, {"AM_AGENTS_NAMES": ""}):
        from src.config import settings
        original_value = settings.AM_AGENTS_NAMES
        try:
            settings.AM_AGENTS_NAMES = ""
            
            response = client.get("/api/v1/agent/list")
            assert response.status_code == 200
            unfiltered_agents = response.json()
            
            # Should return all agents
            assert len(unfiltered_agents) == len(all_agents)
        finally:
            # Restore original value
            settings.AM_AGENTS_NAMES = original_value

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 