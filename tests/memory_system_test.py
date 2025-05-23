import asyncio
import sys
import logging
import os
import time
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import pytest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("memory_system_test")

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.simple.simple_agent.agent import SimpleAgent
from src.tools.memory.provider import MemoryProvider

@pytest.mark.asyncio
async def test_memory_provider():
    """Test the memory provider directly."""
    logger.info("Testing memory provider functionality")
    
    # Create a memory provider for a test agent
    agent_id = 9999  # Use a high ID unlikely to conflict
    provider = MemoryProvider(agent_id)
    
    # The provider should start with an empty cache
    initial_memories = provider.get_all_memories()
    logger.info(f"Initial memories count: {len(initial_memories)}")
    
    # Add a test memory to the cache
    test_memory_name = f"test_memory_{uuid.uuid4().hex[:8]}"
    test_memory_value = f"This is a test memory created at {datetime.now()}"
    
    # Update the cache directly for testing
    provider._memory_cache[test_memory_name] = test_memory_value
    provider._cache_expiry = datetime.now() + timedelta(seconds=30)  # Set expiry 30 seconds in the future
    
    # Retrieve the memory
    retrieved_memory = provider.get_memory(test_memory_name)
    
    if retrieved_memory == test_memory_value:
        logger.info(f"✅ PASSED: Memory retrieval works - value matches expected")
    else:
        logger.error(f"❌ FAILED: Memory retrieval failed or values don't match")
        logger.error(f"Expected: {test_memory_value}")
        logger.error(f"Got: {retrieved_memory}")
        return False
    
    # Test cache invalidation
    provider.invalidate_cache()
    
    # After invalidation, the memory should no longer be in the cache
    post_invalidation = provider.get_memory(test_memory_name)
    
    if post_invalidation is None:
        logger.info(f"✅ PASSED: Cache invalidation works correctly")
    else:
        logger.error(f"❌ FAILED: Cache not properly invalidated")
        logger.error(f"Expected: None")
        logger.error(f"Got: {post_invalidation}")
        return False
    
    # Test system prompt function creation
    prompt_fn = provider.create_system_prompt_function(test_memory_name, "Memory content: {value}")
    
    # The function should exist and have the right name
    if prompt_fn.__name__ == f"memory_{test_memory_name}":
        logger.info(f"✅ PASSED: System prompt function correctly named")
    else:
        logger.error(f"❌ FAILED: System prompt function has wrong name")
        logger.error(f"Expected: memory_{test_memory_name}")
        logger.error(f"Got: {prompt_fn.__name__}")
        return False
    
    # We'll set a value in the cache and check the function returns formatted value
    test_memory_value2 = "Dynamic memory content test"
    provider._memory_cache[test_memory_name] = test_memory_value2
    
    prompt_text = prompt_fn()
    expected_text = f"Memory content: {test_memory_value2}"
    
    if prompt_text == expected_text:
        logger.info(f"✅ PASSED: System prompt function returns correctly formatted memory")
    else:
        logger.error(f"❌ FAILED: System prompt function returned wrong text")
        logger.error(f"Expected: '{expected_text}'")
        logger.error(f"Got: '{prompt_text}'")
        return False
    
    logger.info("✅ All memory provider tests PASSED")
    return True

@pytest.mark.asyncio
async def test_template_extraction():
    """Test the template variable extraction from SimpleAgent."""
    logger.info("Testing template variable extraction")
    
    # Create a minimal SimpleAgent instance for testing
    agent = SimpleAgent({})
    
    # Test template with variables
    test_template = """
    # Test Template
    
    This is a test template with {{variable1}} and {{variable2}} placeholders.
    It also has a repeated variable {{variable1}} to test deduplication.
    
    And here's a {{third_variable}} with underscores.
    """
    
    # Import the correct method
    from src.agents.common.prompt_builder import PromptBuilder
    vars = PromptBuilder.extract_template_variables(test_template)
    expected_vars = {"variable1", "variable2", "third_variable"}
    
    if set(vars) == expected_vars:
        logger.info(f"✅ PASSED: Template variable extraction works correctly")
        logger.info(f"Extracted variables: {vars}")
    else:
        logger.error(f"❌ FAILED: Template variable extraction didn't work as expected")
        logger.error(f"Expected: {sorted(list(expected_vars))}")
        logger.error(f"Got: {sorted(vars)}")
        return False
    
    logger.info("✅ All template extraction tests PASSED")
    return True

if __name__ == "__main__":
    logger.info("=== Dynamic Memory System Test ===")
    
    # Run the focused tests
    provider_result = asyncio.run(test_memory_provider())
    template_result = asyncio.run(test_template_extraction())
    
    if provider_result and template_result:
        logger.info("🎉 All tests passed successfully!")
        sys.exit(0)
    else:
        logger.error("💔 Some tests failed.")
        sys.exit(1) 