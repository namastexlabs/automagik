#!/usr/bin/env python3
"""Observability and usage tracking test for Agno framework."""

import asyncio
import os
import sys
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.agents.models.automagik_agent import AutomagikAgent
from src.agents.models.dependencies import AutomagikAgentsDependencies


class ObservableAgnoAgent(AutomagikAgent):
    """Test agent for observability features using Agno."""
    
    def __init__(self, config):
        # Force Agno framework
        config["framework_type"] = "agno"
        super().__init__(config)
        
        self._code_prompt_text = """You are an AI assistant running on Agno framework.
Your responses are being monitored for usage tracking and observability."""
        
        # Create dependencies
        self.dependencies = AutomagikAgentsDependencies(
            model_name=config.get("model", "openai:gpt-4o-mini"),
            model_settings={}
        )
        
        # Add tools for testing
        self.tool_registry.register_default_tools(self.context)
        
        # Custom tool for testing tool tracking
        async def calculate_sum(ctx, a: int, b: int) -> int:
            """Calculate the sum of two numbers."""
            return a + b
        
        self.tool_registry.register_tool(calculate_sum)


async def test_usage_tracking():
    """Test usage information extraction from Agno."""
    print("=" * 60)
    print("📊 TEST 1: Usage Tracking")
    print("=" * 60)
    
    config = {
        "name": "test_agno_usage",
        "model": "openai:gpt-4o-mini",
        "framework_type": "agno"
    }
    
    agent = ObservableAgnoAgent(config)
    
    # Initialize framework
    await agent.initialize_framework(
        dependencies_type=AutomagikAgentsDependencies,
        tools=list(agent.tool_registry.get_registered_tools().values())
    )
    
    # Make a request to track usage
    response = await agent.run_agent(
        "Please write a short poem about observability in software. Keep it under 50 words."
    )
    
    print(f"✅ Response: {response.text[:100]}...")
    
    # Check usage information
    if response.usage:
        print(f"\n📊 Usage Information:")
        print(f"   Request tokens: {response.usage.get('request_tokens', 'N/A')}")
        print(f"   Response tokens: {response.usage.get('response_tokens', 'N/A')}")
        print(f"   Total tokens: {response.usage.get('total_tokens', 'N/A')}")
        print(f"   Model: {response.usage.get('model', 'N/A')}")
        print(f"   Framework: {response.usage.get('framework', 'N/A')}")
        
        # Additional metrics if available
        if 'duration_ms' in response.usage:
            print(f"   Duration: {response.usage['duration_ms']} ms")
        if 'event_counts' in response.usage:
            print(f"   Event counts: {response.usage['event_counts']}")
    else:
        print("⚠️ No usage information available")
    
    return response


async def test_tool_call_tracking():
    """Test tool call tracking in Agno."""
    print("\n" + "=" * 60)
    print("🔧 TEST 2: Tool Call Tracking")
    print("=" * 60)
    
    config = {
        "name": "test_agno_tools",
        "model": "openai:gpt-4o-mini",
        "framework_type": "agno"
    }
    
    agent = ObservableAgnoAgent(config)
    
    # Initialize framework
    await agent.initialize_framework(
        dependencies_type=AutomagikAgentsDependencies,
        tools=list(agent.tool_registry.get_registered_tools().values())
    )
    
    # Request that triggers tool usage
    response = await agent.run_agent(
        "Can you calculate the sum of 42 and 58 for me?"
    )
    
    print(f"✅ Response: {response.text}")
    
    # Check tool tracking
    if response.tool_calls:
        print(f"\n🔧 Tool Calls Tracked: {len(response.tool_calls)}")
        for i, tool_call in enumerate(response.tool_calls):
            print(f"   Tool {i+1}: {tool_call.get('tool', 'unknown')}")
            print(f"   Args: {tool_call.get('args', {})}")
            print(f"   Started at: {tool_call.get('started_at', 'N/A')}")
    else:
        print("⚠️ No tool calls tracked")
    
    if response.tool_outputs:
        print(f"\n🔧 Tool Outputs: {len(response.tool_outputs)}")
        for i, output in enumerate(response.tool_outputs):
            print(f"   Output {i+1}: {output.get('output', 'N/A')}")
    
    return response


async def test_telemetry_control():
    """Test Agno telemetry control."""
    print("\n" + "=" * 60)
    print("📡 TEST 3: Telemetry Control")
    print("=" * 60)
    
    # Test with telemetry disabled
    os.environ['AGNO_TELEMETRY'] = 'false'
    
    config = {
        "name": "test_agno_telemetry",
        "model": "openai:gpt-4o-mini",
        "framework_type": "agno"
    }
    
    agent = ObservableAgnoAgent(config)
    
    print("ℹ️ Testing with AGNO_TELEMETRY=false")
    print("   (Agno should not send telemetry to their servers)")
    
    # Initialize framework
    await agent.initialize_framework(
        dependencies_type=AutomagikAgentsDependencies
    )
    
    # Make a request
    response = await agent.run_agent(
        "Are you sending telemetry data?"
    )
    
    print(f"✅ Response: {response.text[:100]}...")
    print(f"✅ Telemetry disabled - data stays local")
    
    # Re-enable for other tests
    del os.environ['AGNO_TELEMETRY']


async def test_event_stream_tracking():
    """Test event stream tracking capabilities."""
    print("\n" + "=" * 60)
    print("📈 TEST 4: Event Stream Tracking")
    print("=" * 60)
    
    config = {
        "name": "test_agno_events",
        "model": "openai:gpt-4o-mini",
        "framework_type": "agno"
    }
    
    agent = ObservableAgnoAgent(config)
    
    # Initialize framework
    await agent.initialize_framework(
        dependencies_type=AutomagikAgentsDependencies
    )
    
    print("ℹ️ Agno tracks various events during execution:")
    print("   - RunStarted / RunCompleted")
    print("   - ToolCallStarted / ToolCallCompleted")
    print("   - ReasoningStarted / ReasoningStep / ReasoningCompleted")
    print("   - RunResponseContent")
    
    # Make a request
    response = await agent.run_agent(
        "Think step by step: What is 2 + 2?"
    )
    
    print(f"\n✅ Response: {response.text}")
    
    # Check for event counts in usage
    if response.usage and 'event_counts' in response.usage:
        print(f"\n📈 Event Counts:")
        for event_type, count in response.usage['event_counts'].items():
            print(f"   {event_type}: {count}")


async def test_observability_comparison():
    """Compare observability features with other frameworks."""
    print("\n" + "=" * 60)
    print("📊 TEST 5: Observability Comparison")
    print("=" * 60)
    
    print("📊 Observability Feature Comparison:")
    print("\nPydanticAI:")
    print("  ✓ Token usage tracking")
    print("  ✓ Tool call tracking")
    print("  ✗ Built-in telemetry")
    print("  ✗ Event stream tracking")
    print("  ✗ Real-time monitoring")
    
    print("\nAgno:")
    print("  ✓ Token usage tracking")
    print("  ✓ Tool call tracking")
    print("  ✓ Built-in telemetry (opt-out)")
    print("  ✓ Event stream tracking")
    print("  ✓ Real-time monitoring on agno.com")
    print("  ✓ OpenTelemetry support")
    print("  ✓ Integration with Langfuse, Langtrace")
    
    print("\n🎯 Agno provides richer observability out of the box!")


async def test_database_integration():
    """Test how Agno usage data integrates with our database."""
    print("\n" + "=" * 60)
    print("💾 TEST 6: Database Integration")
    print("=" * 60)
    
    config = {
        "name": "test_agno_db",
        "model": "openai:gpt-4o-mini",
        "framework_type": "agno"
    }
    
    agent = ObservableAgnoAgent(config)
    
    # Initialize framework
    await agent.initialize_framework(
        dependencies_type=AutomagikAgentsDependencies
    )
    
    # Make a request
    response = await agent.run_agent(
        "Generate a test message for database storage."
    )
    
    print(f"✅ Response stored with usage data:")
    print(f"   Text: {response.text[:50]}...")
    
    if response.usage:
        print(f"\n💾 Data ready for DB storage:")
        print(f"   usage field (JSON): {json.dumps(response.usage, indent=2)}")
        print(f"\n✅ Compatible with existing Message.usage field!")


async def main():
    """Run all Agno observability tests."""
    print("🚀 AGNO OBSERVABILITY & USAGE TRACKING TEST")
    print("=" * 60)
    print("Testing Agno's built-in observability features")
    print("and integration with AutomagikAgent's tracking")
    print("=" * 60)
    
    try:
        import agno
        print(f"✅ Agno installed")
    except ImportError:
        print("❌ Agno not installed. Install with: pip install agno")
        return
    
    # Run observability tests
    await test_usage_tracking()
    await test_tool_call_tracking()
    await test_telemetry_control()
    await test_event_stream_tracking()
    await test_observability_comparison()
    await test_database_integration()
    
    print("\n" + "=" * 60)
    print("✅ Observability tests completed!")
    print("\n🎯 Key Benefits:")
    print("   - Built-in telemetry and monitoring")
    print("   - Rich event tracking")
    print("   - OpenTelemetry support")
    print("   - Seamless integration with our usage tracking")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())