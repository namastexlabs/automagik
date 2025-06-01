#!/usr/bin/env python3
"""Test script for Slack integration with agent orchestration.

This script demonstrates how the Slack integration works by:
1. Creating a test orchestration session
2. Sending messages as different agents
3. Showing how humans can participate
"""

import asyncio
import sys
import uuid
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.langgraph.shared.slack_messenger import (
    SlackOrchestrationMessenger, 
    SlackAgentAdapter
)


async def test_slack_integration():
    """Test the Slack integration components."""
    
    print("🧪 Testing Slack Integration for Agent Orchestration\n")
    
    # Test parameters
    orchestration_id = str(uuid.uuid4())
    epic_name = "Test Slack Integration"
    epic_id = "TEST-001"
    agents = ["alpha", "beta", "delta", "epsilon", "gamma"]
    
    print(f"📋 Test Parameters:")
    print(f"   Orchestration ID: {orchestration_id}")
    print(f"   Epic: {epic_name} ({epic_id})")
    print(f"   Agents: {', '.join(agents)}")
    print()
    
    # Step 1: Create orchestration thread
    print("1️⃣ Creating Slack orchestration thread...")
    try:
        thread_ts = await SlackOrchestrationMessenger.create_orchestration_thread(
            orchestration_id=orchestration_id,
            epic_name=epic_name,
            epic_id=epic_id,
            agents=agents
        )
        
        if thread_ts:
            print(f"✅ Thread created: {thread_ts}\n")
        else:
            print("❌ Failed to create thread\n")
            return
    except Exception as e:
        print(f"❌ Error creating thread: {str(e)}\n")
        return
    
    # Step 2: Test agent messages
    print("2️⃣ Testing agent messages...")
    
    # Alpha's task assignment
    alpha_adapter = SlackAgentAdapter("alpha", thread_ts)
    success = await alpha_adapter.send_message(
        message="Team, I've analyzed the epic. Here's the task breakdown:\n" +
                "• @beta: Implement core user model\n" +
                "• @delta: Create REST API endpoints\n" +
                "• @epsilon: Build authentication tools\n" +
                "• @gamma: Set up test framework",
        message_type="task"
    )
    print(f"   Alpha task assignment: {'✅' if success else '❌'}")
    
    # Beta's acknowledgment
    beta_adapter = SlackAgentAdapter("beta", thread_ts)
    success = await beta_adapter.send_message(
        message="Acknowledged. Starting user model implementation with email validation and bcrypt hashing.",
        recipient="alpha",
        message_type="communication"
    )
    print(f"   Beta acknowledgment: {'✅' if success else '❌'}")
    
    # Delta's question
    delta_adapter = SlackAgentAdapter("delta", thread_ts)
    success = await delta_adapter.ask_question(
        question="Should the API use JWT or session-based authentication? Need to know for endpoint design.",
        recipient=None  # Ask everyone
    )
    print(f"   Delta question: {'✅' if success else '❌'}")
    
    # Epsilon's status update
    epsilon_adapter = SlackAgentAdapter("epsilon", thread_ts)
    success = await epsilon_adapter.send_status(
        status="JWT token generator implemented. Supports 24-hour expiry with refresh tokens.",
        details={"completion": 75, "next_task": "implement token validation"}
    )
    print(f"   Epsilon status: {'✅' if success else '❌'}")
    
    # Gamma's discovery
    gamma_adapter = SlackAgentAdapter("gamma", thread_ts)
    success = await gamma_adapter.send_message(
        message="Found existing test utilities in tests/utils/. Will reuse for auth tests.",
        message_type="communication"
    )
    print(f"   Gamma discovery: {'✅' if success else '❌'}")
    
    print()
    
    # Step 3: Test coordination messages
    print("3️⃣ Testing coordination...")
    
    # Beta announces completion
    success = await beta_adapter.send_message(
        message="@delta User model complete and migrated. Ready for API integration:\n" +
                "```python\nclass User(BaseModel):\n    email: EmailStr\n    password_hash: str\n    created_at: datetime\n```",
        recipient="delta",
        message_type="communication"
    )
    print(f"   Beta completion announcement: {'✅' if success else '❌'}")
    
    # Alpha coordinates integration
    success = await alpha_adapter.send_message(
        message="Great progress team! Beta and Delta, please coordinate on the API integration. " +
                "Epsilon, your JWT tool will be needed by Delta soon.",
        message_type="communication"
    )
    print(f"   Alpha coordination: {'✅' if success else '❌'}")
    
    print()
    
    # Step 4: Test orchestration summary
    print("4️⃣ Testing orchestration summary...")
    
    summary = {
        "status": "completed",
        "duration": "2 hours (test)",
        "results": {
            "alpha": {"success": True, "summary": "Successfully coordinated team"},
            "beta": {"success": True, "summary": "User model implemented"},
            "delta": {"success": True, "summary": "API endpoints created"},
            "epsilon": {"success": True, "summary": "JWT tools built"},
            "gamma": {"success": True, "summary": "Test framework ready"}
        },
        "metrics": {
            "messages_sent": 7,
            "tasks_completed": 5,
            "coordination_score": "excellent"
        }
    }
    
    success = await SlackOrchestrationMessenger.send_orchestration_summary(
        thread_ts=thread_ts,
        orchestration_id=orchestration_id,
        summary=summary
    )
    print(f"   Orchestration summary: {'✅' if success else '❌'}")
    
    print()
    
    # Step 5: Demonstrate human interaction
    print("5️⃣ Simulating human interaction...")
    print("   ℹ️  In real usage, humans would:")
    print("   • Answer Delta's authentication question")
    print("   • Provide guidance on implementation details")
    print("   • Approve architectural decisions")
    print("   • Help resolve any blockers")
    
    print("\n✨ Test complete!")
    print(f"\n📌 To see the results, check Slack thread: {thread_ts}")
    print("   (Note: Actual Slack posting requires MCP server to be running)")


async def test_port_management():
    """Test the port management system."""
    from src.agents.langgraph.shared.port_manager import PortManager
    
    print("\n🔌 Testing Port Management\n")
    
    # Test port allocation
    agents = ["alpha", "beta", "delta", "epsilon", "gamma"]
    allocated_ports = {}
    
    print("Allocating ports for agents:")
    for agent in agents:
        port = PortManager.allocate_port(agent)
        if port:
            allocated_ports[agent] = port
            print(f"   {agent}: {port} ✅")
        else:
            print(f"   {agent}: Failed ❌")
    
    # Show all allocations
    print("\nCurrent port allocations:")
    all_ports = PortManager.get_all_allocations()
    for agent, port in all_ports.items():
        available = "🟢" if PortManager.is_port_available(port) else "🔴"
        print(f"   {agent}: {port} {available}")
    
    # Test environment creation
    print("\nTesting environment creation for alpha:")
    try:
        env_file = PortManager.write_agent_env_file("alpha")
        print(f"   Created: {env_file} ✅")
        
        # Show key environment variables
        env_vars = PortManager.create_agent_env("alpha")
        print("   Key variables:")
        print(f"     AM_PORT: {env_vars.get('AM_PORT')}")
        print(f"     AM_AGENT_NAME: {env_vars.get('AM_AGENT_NAME')}")
        print(f"     SLACK_CHANNEL_ID: {env_vars.get('SLACK_CHANNEL_ID')}")
    except Exception as e:
        print(f"   Failed: {str(e)} ❌")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Automagik Agents - Slack Integration Test Suite")
    print("=" * 60)
    
    # Test Slack integration
    await test_slack_integration()
    
    # Test port management
    await test_port_management()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())