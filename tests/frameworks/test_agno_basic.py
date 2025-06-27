#!/usr/bin/env python3
"""Basic test for Agno framework integration."""

import asyncio
import time
import tracemalloc
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies
from src.agents.common.tool_registry import ToolRegistry


class TestAgnoAgent(AutomagikAgent):
    """Test agent using Agno framework."""
    
    def __init__(self, config):
        # Force Agno framework
        config["framework_type"] = "agno"
        super().__init__(config)
        
        # Simple test prompt
        self._code_prompt_text = """You are a helpful AI assistant powered by Agno framework.
You should always mention that you're running on Agno when introducing yourself."""
        
        # Create dependencies
        self.dependencies = AutomagikAgentsDependencies(
            model_name=config.get("model", "openai:gpt-4o-mini"),
            model_settings={}
        )
        
        # Initialize tool registry
        self.tool_registry.register_default_tools(self.context)


async def test_basic_text_response():
    """Test basic text response with Agno."""
    print("=" * 60)
    print("🧪 TEST 1: Basic Text Response")
    print("=" * 60)
    
    config = {
        "name": "test_agno_basic",
        "model": "openai:gpt-4o-mini",
        "temperature": 0.7,
        "framework_type": "agno"
    }
    
    agent = TestAgnoAgent(config)
    
    # Initialize the framework
    await agent.initialize_framework(
        dependencies_type=AutomagikAgentsDependencies,
        tools=list(agent.tool_registry.get_registered_tools().values())
    )
    
    # Test simple response
    response = await agent.run_agent(
        "Hello! What framework are you running on? Please introduce yourself briefly."
    )
    
    print(f"✅ Response: {response.text[:200]}...")
    print(f"✅ Success: {response.success}")
    print(f"✅ Usage: {response.usage}")
    
    return response


async def test_performance_comparison():
    """Compare Agno performance with expected benchmarks."""
    print("\n" + "=" * 60)
    print("🧪 TEST 2: Performance Benchmarks")
    print("=" * 60)
    
    # Start memory tracking
    tracemalloc.start()
    
    # Time agent creation
    start_time = time.perf_counter()
    
    config = {
        "name": "test_agno_perf",
        "model": "openai:gpt-4o-mini",
        "framework_type": "agno"
    }
    
    agents = []
    for i in range(100):
        agent = TestAgnoAgent(config)
        agents.append(agent)
    
    creation_time = time.perf_counter() - start_time
    
    # Get memory usage
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    avg_creation_time_us = (creation_time / 100) * 1_000_000
    avg_memory_kb = (current / 100) / 1024
    
    print(f"📊 Performance Metrics (100 agents):")
    print(f"   Average creation time: {avg_creation_time_us:.2f} μs")
    print(f"   Average memory usage: {avg_memory_kb:.2f} KB")
    print(f"   Total creation time: {creation_time:.4f} seconds")
    
    # Compare with Agno's claimed performance
    print(f"\n📊 Comparison with Agno claims:")
    print(f"   Agno claim: ~2 μs per agent")
    print(f"   Our measurement: {avg_creation_time_us:.2f} μs")
    print(f"   Agno claim: ~3.75 KB per agent")
    print(f"   Our measurement: {avg_memory_kb:.2f} KB")
    
    # Note: Our measurements include AutomagikAgent overhead


async def test_tool_integration():
    """Test tool integration with Agno."""
    print("\n" + "=" * 60)
    print("🧪 TEST 3: Tool Integration")
    print("=" * 60)
    
    # Create agent with custom tool
    config = {
        "name": "test_agno_tools",
        "model": "openai:gpt-4o-mini",
        "framework_type": "agno"
    }
    
    agent = TestAgnoAgent(config)
    
    # Add a custom tool
    async def get_current_time(ctx):
        """Get the current time."""
        import datetime
        return f"Current time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    agent.tool_registry.register_tool(get_current_time)
    
    # Initialize framework
    await agent.initialize_framework(
        dependencies_type=AutomagikAgentsDependencies,
        tools=list(agent.tool_registry.get_registered_tools().values())
    )
    
    # Test tool usage
    response = await agent.run_agent(
        "What time is it right now?"
    )
    
    print(f"✅ Response: {response.text}")
    print(f"✅ Tool calls: {len(response.tool_calls)}")
    if response.tool_calls:
        print(f"✅ Tools used: {[tc.get('tool', 'unknown') for tc in response.tool_calls]}")


async def test_error_handling():
    """Test error handling in Agno framework."""
    print("\n" + "=" * 60)
    print("🧪 TEST 4: Error Handling")
    print("=" * 60)
    
    # Test with invalid model
    config = {
        "name": "test_agno_error",
        "model": "invalid:model-name",
        "framework_type": "agno"
    }
    
    try:
        agent = TestAgnoAgent(config)
        await agent.initialize_framework(
            dependencies_type=AutomagikAgentsDependencies
        )
        
        response = await agent.run_agent("Hello!")
        print(f"Response success: {response.success}")
        if not response.success:
            print(f"✅ Error properly handled: {response.error_message}")
    except Exception as e:
        print(f"✅ Exception caught: {type(e).__name__}: {e}")


async def main():
    """Run all Agno framework tests."""
    print("🚀 AGNO FRAMEWORK INTEGRATION TESTS")
    print("=" * 60)
    print("Testing Agno as an alternative framework to PydanticAI")
    print("Expected benefits: Ultra-fast performance, native multimodal support")
    print("=" * 60)
    
    try:
        # Check if Agno is installed
        import agno
        print(f"✅ Agno version: {agno.__version__ if hasattr(agno, '__version__') else 'unknown'}")
    except ImportError:
        print("❌ Agno not installed. Install with: pip install agno")
        return
    
    # Run tests
    await test_basic_text_response()
    await test_performance_comparison()
    await test_tool_integration()
    await test_error_handling()
    
    print("\n" + "=" * 60)
    print("✅ All basic Agno tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())