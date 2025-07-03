#!/usr/bin/env python3
"""Test agent discovery in external directory."""

import os
import sys

# Ensure we're using the project's virtual environment
sys.path.insert(0, '/home/cezar/automagik/am-agents-labs')

def test_agent_discovery():
    """Test if external agent can be discovered."""
    print("🧪 Testing External Agent Discovery")
    print("=" * 50)
    
    # Set external agents directory
    os.environ["AUTOMAGIK_EXTERNAL_AGENTS_DIR"] = "/home/cezar/automagik/am-agents-labs/automagik_agents"
    os.environ["AUTOMAGIK_DATABASE_TYPE"] = "sqlite"
    os.environ["AUTOMAGIK_SQLITE_DATABASE_PATH"] = ":memory:"
    
    try:
        from automagik.agents.models.agent_factory import AgentFactory
        
        print("📁 External agents directory:", os.environ["AUTOMAGIK_EXTERNAL_AGENTS_DIR"])
        
        # Trigger external agent discovery
        print("\n🔍 Discovering external agents...")
        AgentFactory._discover_external_agents()
        
        # List available agents
        print("\n📋 Available agents:")
        agents = AgentFactory.list_available_agents()
        for agent in agents:
            print(f"   - {agent}")
        
        # Check if our external agent was discovered
        if "flashinho_pro_external" in agents:
            print("\n✅ External agent 'flashinho_pro_external' discovered!")
            
            # Try to create the agent
            print("\n🔧 Creating external agent instance...")
            agent_instance = AgentFactory.create_agent("flashinho_pro_external", {})
            print(f"✅ Agent created: {type(agent_instance).__name__}")
            
            return True
        else:
            print("\n❌ External agent not found in available agents")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_agent_discovery()
    sys.exit(0 if success else 1)