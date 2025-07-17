#!/usr/bin/env python3
"""Test script to demonstrate error handling with custom messages."""

import asyncio
from automagik.agents.models.automagik_agent import AutomagikAgent
from automagik.agents.models.response import AgentResponse
from automagik.agents.models.dependencies import BaseDependencies
from automagik.db import Agent, create_agent
import uuid


class ErrorTestAgent(AutomagikAgent):
    """Test agent that always throws an error."""
    
    def __init__(self):
        super().__init__(
            name="error_test",
            description="Agent for testing error handling",
            version="1.0.0",
            system_prompt="Test agent",
            model="openai:gpt-4o-mini"
        )
    
    async def _run_agent(self, *args, **kwargs):
        """Always throw an error to test handling."""
        raise Exception("Test error - This is a simulated error for testing")


async def test_error_handling():
    """Test the error handling system."""
    
    # Create test agent in database with custom error settings
    test_agent = Agent(
        name="error_test",
        type="pydanticai",
        model="openai:gpt-4o-mini",
        description="Test agent for error handling",
        error_message="🚨 Custom Error: Our system is temporarily unavailable. Please try again in a few minutes or contact support@example.com for assistance.",
        error_webhook_url="https://webhook.site/unique-test-id"  # Replace with your webhook.site URL
    )
    
    agent_id = create_agent(test_agent)
    print(f"Created test agent with ID: {agent_id}")
    
    # Create agent instance
    agent = ErrorTestAgent()
    agent.db_id = agent_id
    
    # Create mock dependencies
    deps = BaseDependencies()
    deps.user_id = uuid.uuid4()
    deps.session_id = str(uuid.uuid4())
    deps.agent_name = "error_test"
    
    # Test the agent (this will fail and trigger error handling)
    try:
        response = await agent._run_agent(
            input_text="Test message",
            system_prompt="Test prompt",
            dependencies=deps
        )
        
        print(f"Response success: {response.success}")
        print(f"Response text: {response.text}")
        print(f"Error message: {response.error_message}")
        
    except Exception as e:
        print(f"Caught exception: {e}")
    
    # Wait a bit for async notifications to complete
    await asyncio.sleep(2)
    
    print("\nCheck your webhook URL to see if the error notification was sent!")
    print("The response should show the custom error message instead of the raw error.")


if __name__ == "__main__":
    asyncio.run(test_error_handling())