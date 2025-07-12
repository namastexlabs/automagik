#!/usr/bin/env python3
"""Debug test for Claude SDK to see detailed execution."""

import asyncio
import logging
import sys
from pathlib import Path
from claude_code_sdk import query, ClaudeCodeOptions

# Set up very detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Enable debug logging for the SDK
logging.getLogger('claude_code_sdk').setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_claude_sdk():
    """Test Claude SDK with maximum debugging."""
    
    # Create options with brain workflow workspace
    options = ClaudeCodeOptions()
    options.cwd = "/home/cezar/automagik/am-agents-labs/worktrees/main-brain-36faafc4-36faafc4"
    
    # Load prompt from brain workflow
    prompt_file = Path(options.cwd) / "prompt.md"
    if prompt_file.exists():
        with open(prompt_file) as f:
            options.system_prompt = f.read()
            logger.info(f"Loaded prompt: {len(options.system_prompt)} chars")
    
    # Simple test query
    test_prompt = "Hello brain, test message"
    logger.info(f"Testing with prompt: {test_prompt}")
    logger.info(f"Working directory: {options.cwd}")
    logger.info(f"System prompt set: {bool(options.system_prompt)}")
    
    message_count = 0
    error_count = 0
    
    try:
        logger.info("Starting query...")
        async for message in query(prompt=test_prompt, options=options):
            message_count += 1
            logger.info(f"Message {message_count}: {type(message).__name__}")
            
            # Log message details
            if hasattr(message, '__dict__'):
                logger.debug(f"Message attributes: {message.__dict__}")
            
            # Stop after receiving a few messages
            if message_count >= 3:
                logger.info("Received enough messages, stopping...")
                break
                
    except Exception as e:
        error_count += 1
        logger.error(f"Error during query: {e}", exc_info=True)
        
    logger.info(f"Test complete - Messages: {message_count}, Errors: {error_count}")
    
    # Return success if we got any messages
    return message_count > 0

if __name__ == "__main__":
    # Run the test
    success = asyncio.run(test_claude_sdk())
    
    if success:
        print("\n✅ SUCCESS: Claude SDK is working properly")
        sys.exit(0)
    else:
        print("\n❌ FAILURE: Claude SDK did not return any messages")
        sys.exit(1)