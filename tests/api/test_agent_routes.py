import pytest
import uuid
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
    
    # The number of agents should match what we found in setup
    assert len(agents) == len(available_agents)
    
    # Agent names should match available agents
    agent_names = [agent["name"] for agent in agents]
    for name in available_agents:
        assert name in agent_names

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

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 