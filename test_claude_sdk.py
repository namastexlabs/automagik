#!/usr/bin/env python3
"""Test Claude SDK directly to isolate the issue."""

import asyncio
import logging
from pathlib import Path
from claude_code_sdk import query, ClaudeCodeOptions

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_claude_sdk():
    """Test Claude SDK with minimal setup."""
    
    # Create options with brain workflow workspace
    options = ClaudeCodeOptions()
    options.cwd = "/home/cezar/automagik/automagik/worktrees/main-brain-36faafc4-36faafc4"
    
    # Load prompt from brain workflow
    prompt_file = Path(options.cwd) / "prompt.md"
    if prompt_file.exists():
        with open(prompt_file) as f:
            options.system_prompt = f.read()
            logger.info(f"Loaded prompt: {len(options.system_prompt)} chars")
    
    # Simple test query
    test_prompt = "Hello brain, can you hear me?"
    logger.info(f"Testing with prompt: {test_prompt}")
    
    message_count = 0
    try:
        async for message in query(prompt=test_prompt, options=options):
            message_count += 1
            logger.info(f"Received message {message_count}: {type(message).__name__}")
            
            # Print message content
            if hasattr(message, 'content'):
                logger.info(f"Content: {message.content[:200]}...")
            elif hasattr(message, 'text'):
                logger.info(f"Text: {message.text[:200]}...")
            elif hasattr(message, 'data'):
                logger.info(f"Data: {message.data}")
            else:
                logger.info(f"Message attributes: {dir(message)}")
                
            # Don't break - continue receiving all messages
            # if message_count >= 1:
            #     break
                
    except Exception as e:
        logger.error(f"Error during query: {e}", exc_info=True)
        
    logger.info(f"Total messages received: {message_count}")
    
if __name__ == "__main__":
    asyncio.run(test_claude_sdk())