#!/usr/bin/env python
"""
Test script for checking Pro user status and model/prompt selection
"""

import asyncio
import logging
import sys
import os

# Add parent directory to path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from automagik.tools.flashed.provider import FlashedProvider
from automagik.agents.pydanticai.flashinho_pro.agent import FlashinhoPro
from automagik.agents.pydanticai.flashinho_pro.prompts.prompt import AGENT_PROMPT, AGENT_FREE

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_pro_status():
    """Test Pro status check and model/prompt selection."""
    
    # Test with regular user (not in Pro list)
    regular_user_id = "556f422c-4296-4d99-95ba-c12ef69bbeaf"
    
    # Test with Pro user (from mock list)
    pro_user_id = "123e4567-e89b-12d3-a456-426614174000"
    
    # Create provider for direct testing
    provider = FlashedProvider()
    
    # Check status directly
    regular_status = await provider.check_user_pro_status(regular_user_id)
    pro_status = await provider.check_user_pro_status(pro_user_id)
    
    logger.info(f"Direct check - Regular user status: {regular_status}")
    logger.info(f"Direct check - Pro user status: {pro_status}")
    
    # Test with agent - Regular user
    logger.info("\n--- Testing with Regular User ---")
    regular_agent = FlashinhoPro({})
    
    # Check user status
    is_pro = await regular_agent._check_user_pro_status(regular_user_id)
    logger.info(f"Regular user Pro status: {is_pro}")
    
    # Update model based on status
    await regular_agent._update_model_and_prompt_based_on_status(regular_user_id)
    
    # Check which model would be used
    if regular_agent._is_pro_user:
        logger.info(f"Regular user is using Pro model: {regular_agent.pro_model}")
        logger.info(f"Regular user is using Pro prompt: {regular_agent._code_prompt_text[:50]}...")
    else:
        logger.info(f"Regular user is using Free model: {regular_agent.free_model}")
        logger.info(f"Regular user is using Free prompt: {regular_agent._code_prompt_text[:50]}...")
    
    # Verify prompt is correct
    is_using_pro_prompt = regular_agent._code_prompt_text == AGENT_PROMPT
    is_using_free_prompt = regular_agent._code_prompt_text == AGENT_FREE
    logger.info(f"Regular user prompt verification - Pro: {is_using_pro_prompt}, Free: {is_using_free_prompt}")
    
    # Test with agent - Pro user
    logger.info("\n--- Testing with Pro User ---")
    pro_agent = FlashinhoPro({})
    
    # Check user status
    is_pro = await pro_agent._check_user_pro_status(pro_user_id)
    logger.info(f"Pro user Pro status: {is_pro}")
    
    # Update model based on status
    await pro_agent._update_model_and_prompt_based_on_status(pro_user_id)
    
    # Check which model would be used
    if pro_agent._is_pro_user:
        logger.info(f"Pro user is using Pro model: {pro_agent.pro_model}")
        logger.info(f"Pro user is using Pro prompt: {pro_agent._code_prompt_text[:50]}...")
    else:
        logger.info(f"Pro user is using Free model: {pro_agent.free_model}")
        logger.info(f"Pro user is using Free prompt: {pro_agent._code_prompt_text[:50]}...")
    
    # Verify prompt is correct
    is_using_pro_prompt = pro_agent._code_prompt_text == AGENT_PROMPT
    is_using_free_prompt = pro_agent._code_prompt_text == AGENT_FREE
    logger.info(f"Pro user prompt verification - Pro: {is_using_pro_prompt}, Free: {is_using_free_prompt}")
    
    # Test with invalid UUID
    logger.info("\n--- Testing with Invalid UUID ---")
    invalid_agent = FlashinhoPro({})
    
    # Check user status
    is_pro = await invalid_agent._check_user_pro_status("not-a-uuid")
    logger.info(f"Invalid UUID Pro status: {is_pro}")
    
    # Update model based on status
    await invalid_agent._update_model_and_prompt_based_on_status("not-a-uuid")
    
    # Check which model would be used
    if invalid_agent._is_pro_user:
        logger.info(f"Invalid UUID user is using Pro model: {invalid_agent.pro_model}")
        logger.info(f"Invalid UUID user is using Pro prompt: {invalid_agent._code_prompt_text[:50]}...")
    else:
        logger.info(f"Invalid UUID user is using Free model: {invalid_agent.free_model}")
        logger.info(f"Invalid UUID user is using Free prompt: {invalid_agent._code_prompt_text[:50]}...")
    
    # Verify prompt is correct
    is_using_pro_prompt = invalid_agent._code_prompt_text == AGENT_PROMPT
    is_using_free_prompt = invalid_agent._code_prompt_text == AGENT_FREE
    logger.info(f"Invalid UUID prompt verification - Pro: {is_using_pro_prompt}, Free: {is_using_free_prompt}")

if __name__ == "__main__":
    asyncio.run(test_pro_status()) 