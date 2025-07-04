#!/usr/bin/env python3
"""Test script to verify API fix for external agents."""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(name)s - %(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up environment for testing
os.environ['AUTOMAGIK_EXTERNAL_AGENTS_DIR'] = str(project_root / 'agents_examples')
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', 'test-key')


async def test_agent_factory_fix():
    """Test that AgentFactory properly creates external agents."""
    logger.info("Testing AgentFactory fix for external agents...")
    
    try:
        from automagik.agents.models.agent_factory import AgentFactory
        
        # First, discover agents
        logger.info("Discovering agents...")
        AgentFactory.discover_agents()
        
        # List available agents
        available = AgentFactory.list_available_agents()
        logger.info(f"Available agents: {available}")
        
        # Try to create an external agent
        logger.info("\nAttempting to create flashinho_pro_external...")
        agent = AgentFactory.create_agent("flashinho_pro_external", {"model": "openai:gpt-4o-mini"})
        
        if agent and agent.__class__.__name__ != "PlaceholderAgent":
            logger.info(f"✅ Successfully created agent: {agent.__class__.__name__}")
            
            # Check if it's the correct type
            if "Flashinho" in agent.__class__.__name__:
                logger.info("✅ Agent is correctly identified as a Flashinho agent!")
                return True
            else:
                logger.error(f"❌ Agent type is wrong: {agent.__class__.__name__}")
                return False
        else:
            logger.error("❌ Failed to create agent or got PlaceholderAgent")
            return False
            
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_api_simulation():
    """Simulate what the API does when creating an agent."""
    logger.info("\n\nSimulating API agent creation flow...")
    
    try:
        # This simulates what happens in agent_controller.py
        from automagik.agents.models.agent_factory import AgentFactory
        
        # Create a new factory instance (like the API does)
        factory = AgentFactory()
        
        # Try to get agent with session (like the API does)
        agent_name = "flashinho_pro_external"
        logger.info(f"Attempting to create {agent_name} via factory instance...")
        
        # Use the same method the API uses
        agent = factory.get_agent_with_session(
            agent_name, 
            session_id="test-session-123",
            user_id="test-user-123"
        )
        
        if agent:
            logger.info(f"✅ Agent created: {agent.__class__.__name__}")
            
            if "Flashinho" in agent.__class__.__name__:
                logger.info("✅ API simulation successful - external agent created correctly!")
                return True
            else:
                logger.error(f"❌ API simulation failed - got {agent.__class__.__name__} instead of Flashinho agent")
                return False
        else:
            logger.error("❌ API simulation failed - no agent created")
            return False
            
    except Exception as e:
        logger.error(f"❌ API simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    logger.info("=== Testing External Agent API Fix ===\n")
    
    # Test 1: Direct factory test
    result1 = await test_agent_factory_fix()
    
    # Test 2: API simulation test
    result2 = await test_api_simulation()
    
    # Summary
    logger.info("\n=== Test Summary ===")
    logger.info(f"Direct factory test: {'✅ PASSED' if result1 else '❌ FAILED'}")
    logger.info(f"API simulation test: {'✅ PASSED' if result2 else '❌ FAILED'}")
    
    if result1 and result2:
        logger.info("\n✅ All tests passed! The fix should work.")
    else:
        logger.error("\n❌ Some tests failed. The fix needs more work.")
    
    return result1 and result2


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)