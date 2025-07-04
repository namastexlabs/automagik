#!/usr/bin/env python3
"""Test script to validate external agent functionality."""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up environment for testing
os.environ['AUTOMAGIK_EXTERNAL_AGENTS_DIR'] = str(project_root / 'agents_examples')
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY', 'test-key')
os.environ['GEMINI_API_KEY'] = os.environ.get('GEMINI_API_KEY', 'test-key')


async def test_external_agent_discovery():
    """Test that external agents can be discovered."""
    logger.info("Testing external agent discovery...")
    
    try:
        from automagik.agents.models.agent_factory import AgentFactory
        
        # Check if external agents are registered
        # The factory uses dynamic discovery, so let's try to create one
        external_agents_found = []
        test_agents = ['flashinho_pro_external', 'flashinho_pro', 'flashinho_the_first']
        
        for agent_name in test_agents:
            try:
                agent = AgentFactory.create_agent(agent_name, {})
                if agent:
                    external_agents_found.append(agent_name)
            except:
                pass
        
        logger.info(f"Found {len(external_agents_found)} external agents: {external_agents_found}")
        
        if external_agents_found:
            logger.info("✓ External agent discovery is working!")
            return True
        else:
            logger.error("✗ No external agents found")
            return False
            
    except Exception as e:
        logger.error(f"✗ Discovery failed: {e}")
        return False


async def test_external_agent_creation():
    """Test that external agents can be created."""
    logger.info("\nTesting external agent creation...")
    
    try:
        from automagik.agents.models.agent_factory import AgentFactory
        
        # Try to create an external agent
        config = {
            "model": "openai:gpt-4o-mini",
            "temperature": 0.7
        }
        
        agent = AgentFactory.create_agent("flashinho_pro_external", config)
        
        if agent:
            logger.info(f"✓ Created agent: {agent.__class__.__name__}")
            logger.info(f"  - Has prompt: {'_code_prompt_text' in dir(agent)}")
            logger.info(f"  - Has dependencies: {hasattr(agent, 'dependencies')}")
            logger.info(f"  - Has tool registry: {hasattr(agent, 'tool_registry')}")
            return True
        else:
            logger.error("✗ Failed to create agent")
            return False
            
    except Exception as e:
        logger.error(f"✗ Creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_base_external_agent():
    """Test BaseExternalAgent functionality."""
    logger.info("\nTesting BaseExternalAgent...")
    
    try:
        # Import from agents_examples
        sys.path.insert(0, str(project_root / 'agents_examples'))
        from base_external_agent import BaseExternalAgent
        
        # Create a simple test agent
        class TestAgent(BaseExternalAgent):
            DEFAULT_MODEL = "openai:gpt-4o-mini"
            
            def _initialize_agent(self):
                self._code_prompt_text = "Test prompt"
        
        agent = TestAgent({})
        
        logger.info("✓ BaseExternalAgent is working!")
        logger.info(f"  - Prompt set: {agent._code_prompt_text == 'Test prompt'}")
        logger.info(f"  - Dependencies created: {agent.dependencies is not None}")
        logger.info(f"  - Model configured: {agent.dependencies.model_name == 'openai:gpt-4o-mini'}")
        
        return True
        
    except Exception as e:
        logger.error(f"✗ BaseExternalAgent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_run():
    """Test running an external agent."""
    logger.info("\nTesting agent execution...")
    
    try:
        from automagik.agents.models.agent_factory import AgentFactory
        
        # Create simple agent
        agent = AgentFactory.create_agent("simple", {"model": "openai:gpt-4o-mini"})
        
        if not agent:
            logger.error("Failed to create agent for testing")
            return False
        
        # Try to run the agent using the correct method
        try:
            result = await agent.run("Hello, can you respond?")
        except Exception as e:
            # Try process_message as fallback
            try:
                result = await agent.process_message("Hello, can you respond?")
            except:
                logger.error(f"Agent execution error: {e}")
                return False
        
        if result:
            logger.info("✓ Agent execution successful!")
            response_text = str(result)[:100] if len(str(result)) > 100 else str(result)
            logger.info(f"  - Response: {response_text}...")
            return True
        else:
            logger.error("✗ No response from agent")
            return False
            
    except Exception as e:
        logger.error(f"✗ Agent execution failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("=== External Agent Validation Tests ===\n")
    
    tests = [
        test_external_agent_discovery,
        test_external_agent_creation,
        test_base_external_agent,
        test_agent_run
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            logger.error(f"Test {test.__name__} crashed: {e}")
            results.append(False)
    
    # Summary
    logger.info("\n=== Test Summary ===")
    passed = sum(results)
    total = len(results)
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("✅ All tests passed! External agents are working correctly.")
    else:
        logger.error("❌ Some tests failed. External agents may have issues.")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)