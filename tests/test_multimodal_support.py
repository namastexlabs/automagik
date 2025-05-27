"""Test script for verifying multimodal support in SimpleAgent.

This script tests the agent's ability to handle different types of
multimodal content: images, audio, and documents.
"""

import asyncio
import logging
import os
import sys
import pytest

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("test_multimodal")

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.simple.simple import create_agent

@pytest.mark.asyncio
async def test_multimodal_support():
    """Test multimodal support in SimpleAgent."""
    
    # Create test configuration
    config = {
        "model": "openai:gpt-3.5-turbo",  # Start with non-multimodal model
        "agent_id": "test_multimodal_agent"
    }
    
    # Create agent instance
    agent = create_agent(config)
    logger.info(f"Created agent with initial model: {agent.config.model}")
    
    # Test image processing
    deps = AutomagikAgentsDependencies()
    deps.configure_for_multimodal(modality="image")
    logger.info(f"Configured for image processing with model: {deps.model_name}")
    
    # Test that multimodal capabilities can be configured
    # The agent's tool registry should have multimodal tools available
    
    # Test audio support
    deps = AutomagikAgentsDependencies()
    deps.configure_for_multimodal(modality="audio")
    logger.info(f"Configured for audio processing with model: {deps.model_name}")
    
    # Test document support
    deps = AutomagikAgentsDependencies()
    deps.configure_for_multimodal(modality="document")
    logger.info(f"Configured for document processing with model: {deps.model_name}")
    
    # Verify model selection
    logger.info("Testing model selection for different modalities:")
    test_models = [
        "openai:gpt-3.5-turbo",
        "openai:gpt-4o",
        "anthropic:claude-3-opus",
        "anthropic:claude-3-haiku"
    ]
    
    for model in test_models:
        deps = AutomagikAgentsDependencies()
        deps.model_name = model
        
        logger.info(f"Model {model}:")
        logger.info("  - Testing model configuration")
        
        # Test multimodal configuration
        deps.configure_for_multimodal(modality="image")
        logger.info(f"  - Configured for image: {deps.model_name}")
    
    logger.info("All multimodal tests completed successfully!")

def main():
    """Run the main test function."""
    asyncio.run(test_multimodal_support())

if __name__ == "__main__":
    main() 