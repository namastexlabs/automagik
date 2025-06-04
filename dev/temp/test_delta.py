#!/usr/bin/env python3
"""Test script for Delta agent implementation."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from src.agents.langgraph.delta import create_agent

def test_delta_agent():
    """Test Delta agent creation and basic functionality."""
    print("🔍 Testing Delta agent implementation...")
    
    # Test agent creation
    config = {
        'workspace_path': '/test/workspace/api',
        'user_id': 1,
        'session_id': 'test-session'
    }
    
    try:
        agent = create_agent(config)
        print(f"✅ Delta agent created successfully")
        print(f"   Description: {agent.description}")
        print(f"   Workspace: {agent.workspace_path}")
        print(f"   Agent type: {type(agent).__name__}")
        
        # Test workspace update
        agent.update_workspace_path('/new/test/path')
        print(f"✅ Workspace update successful: {agent.workspace_path}")
        
        # Test string representation
        print(f"✅ String representation: {agent}")
        
        print("\n🎯 All Delta agent tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing Delta agent: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_delta_agent() 