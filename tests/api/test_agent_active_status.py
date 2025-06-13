import pytest
from src.db.repository.agent import list_agents, get_agent_by_name, update_agent
from src.api.controllers.agent_controller import list_registered_agents


@pytest.mark.asyncio
async def test_list_agents_respects_active_status():
    """Test that listing agents only returns active agents"""
    
    # Get all agents from database
    all_agents = list_agents(active_only=False)
    
    if len(all_agents) < 2:
        pytest.skip("Need at least 2 agents in database for this test")
    
    # Pick two real agents (skip placeholder agents like claude-code_disabled)
    real_agents = [agent for agent in all_agents if not agent.name.endswith('_disabled') and not agent.name.endswith('_error')]
    
    if len(real_agents) < 2:
        pytest.skip("Need at least 2 real agents in database for this test")
    
    agent_to_activate = real_agents[0]
    agent_to_deactivate = real_agents[1]
    
    # Store original states to restore later
    original_states = {
        agent_to_activate.name: agent_to_activate.active,
        agent_to_deactivate.name: agent_to_deactivate.active
    }
    
    try:
        # Set active states
        agent_to_activate.active = True
        update_agent(agent_to_activate)
        
        agent_to_deactivate.active = False
        update_agent(agent_to_deactivate)
        
        # Call the API controller function
        agent_infos = await list_registered_agents()
        agent_names = [agent.name for agent in agent_infos]
        
        # Verify active agent is in the list
        assert agent_to_activate.name in agent_names, f"Active agent {agent_to_activate.name} should be in the list"
        
        # Verify inactive agent is NOT in the list
        assert agent_to_deactivate.name not in agent_names, f"Inactive agent {agent_to_deactivate.name} should NOT be in the list"
        
    finally:
        # Restore original states
        for agent_name, original_state in original_states.items():
            agent = get_agent_by_name(agent_name)
            if agent:
                agent.active = original_state
                update_agent(agent)


def test_database_list_agents_active_filter():
    """Test that the database list_agents function correctly filters by active status"""
    
    # Get all agents
    all_agents = list_agents(active_only=False)
    
    # Get only active agents
    active_agents = list_agents(active_only=True)
    
    # Active agents should be a subset of all agents
    assert len(active_agents) <= len(all_agents)
    
    # All returned active agents should have active=True
    for agent in active_agents:
        assert agent.active is True, f"Agent {agent.name} returned by active_only=True but has active={agent.active}"
    
    # Check that inactive agents are not in the active list
    inactive_agents = [a for a in all_agents if not a.active]
    active_agent_names = [a.name for a in active_agents]
    
    for inactive_agent in inactive_agents:
        assert inactive_agent.name not in active_agent_names, f"Inactive agent {inactive_agent.name} should not be in active agents list"


@pytest.mark.asyncio 
async def test_active_status_update():
    """Test updating agent active status"""
    
    # Get an agent from database
    all_agents = list_agents(active_only=False)
    
    if not all_agents:
        pytest.skip("No agents in database")
    
    test_agent = all_agents[0]
    original_state = test_agent.active
    
    try:
        # Toggle the active state
        new_state = not original_state
        test_agent.active = new_state
        update_result = update_agent(test_agent)
        
        assert update_result is not None, "Update should return agent ID"
        
        # Verify the change persisted
        updated_agent = get_agent_by_name(test_agent.name)
        assert updated_agent.active == new_state, f"Agent active state should be {new_state}"
        
        # Test listing with new state
        agent_infos = await list_registered_agents()
        agent_names = [agent.name for agent in agent_infos]
        
        if new_state:
            assert test_agent.name in agent_names, "Activated agent should appear in list"
        else:
            assert test_agent.name not in agent_names, "Deactivated agent should not appear in list"
            
    finally:
        # Restore original state
        test_agent.active = original_state
        update_agent(test_agent)


if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 