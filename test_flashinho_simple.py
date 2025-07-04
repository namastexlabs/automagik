#!/usr/bin/env python3
"""
Simple test script for Flashinho agents with channel payloads.
Shows how to install and test from a local build.
"""
import os
import sys
import json
import asyncio
from pathlib import Path

print("=== Flashinho Agent Test Script ===\n")

# Check if we're in the right environment
try:
    import automagik
    print("✅ Automagik is installed")
except ImportError:
    print("❌ Automagik not found!")
    print("\nTo install from local build:")
    print("  1. cd to am-agents-labs directory")
    print("  2. python3 -m venv test_env")
    print("  3. source test_env/bin/activate")
    print("  4. uv pip install -e .")
    print("     OR")
    print("     pip install -e .")
    sys.exit(1)

# Set up environment
os.environ['AUTOMAGIK_EXTERNAL_AGENTS_DIR'] = './agents_examples'
os.environ.setdefault('OPENAI_API_KEY', 'test-key')
os.environ.setdefault('GEMINI_API_KEY', 'test-key')

async def test_flashinho_basic():
    """Test basic Flashinho functionality."""
    print("\n1. Testing Basic Flashinho Agent...")
    
    try:
        from automagik.agents.models.agent_factory import AgentFactory
        
        # Create Flashinho agent
        agent = AgentFactory.create_agent("flashinho_pro_external", {
            "model": "google:gemini-2.5-pro",
            "temperature": 0.7
        })
        
        if not agent:
            print("❌ Failed to create agent")
            return False
            
        print(f"✅ Created agent: {agent.__class__.__name__}")
        
        # Test basic message
        response = await agent.run("Olá! Me ajuda com matemática?")
        print(f"✅ Agent responded: {str(response)[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_flashinho_with_channel():
    """Test Flashinho with channel payload (WhatsApp simulation)."""
    print("\n2. Testing Flashinho with WhatsApp Channel...")
    
    try:
        from automagik.agents.models.agent_factory import AgentFactory
        
        # Create agent
        agent = AgentFactory.create_agent("flashinho_pro_external", {})
        
        # Simulate WhatsApp message with channel context
        channel_payload = {
            "channel": "evolution",
            "instance": "flashinho-test",
            "phone_number": "5511999999999",
            "user_name": "Test Student",
            "message": {
                "key": {
                    "remoteJid": "5511999999999@s.whatsapp.net",
                    "fromMe": False,
                    "id": "TEST123"
                },
                "pushName": "Test Student",
                "message": {
                    "conversation": "Preciso de ajuda com equações"
                }
            }
        }
        
        # Process message with channel context
        response = await agent.process_message(
            "Preciso de ajuda com equações",
            channel_payload=channel_payload,
            session_name="whatsapp_5511999999999"
        )
        
        print(f"✅ Agent handled WhatsApp message: {str(response)[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_flashinho_with_evolution_payload():
    """Test with full Evolution API payload (Stan pattern)."""
    print("\n3. Testing with Evolution API Payload...")
    
    try:
        from automagik.agents.models.agent_factory import AgentFactory
        
        agent = AgentFactory.create_agent("flashinho_pro_external", {})
        
        # Full Evolution payload as used in production
        evolution_payload = {
            "data": {
                "key": {
                    "remoteJid": "5511987654321@s.whatsapp.net",
                    "fromMe": False,
                    "id": "3EB0ABCDEF123456"
                },
                "message": {
                    "conversation": "Quero aprender física quântica"
                },
                "messageType": "conversation",
                "pushName": "Maria Estudante",
                "owner": "flashinho-prod"
            },
            "instance": "flashinho-prod"
        }
        
        # Process with evolution payload
        response = await agent.process_message(
            "Quero aprender física quântica",
            evolution_payload=evolution_payload,
            user_id="test-user-456",
            session_name="flashinho-prod-5511987654321"
        )
        
        print(f"✅ Processed Evolution payload: {str(response)[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def show_api_examples():
    """Show examples of API calls."""
    print("\n4. API Call Examples:")
    print("\nTo test via API, first start the server:")
    print("  automagik api")
    print("\nThen use these curl commands:")
    
    print("\n📝 Simple test:")
    print("""curl -X POST http://localhost:8000/api/v1/agent/flashinho_pro_external/run \\
  -H "X-API-Key: namastex888" \\
  -H "Content-Type: application/json" \\
  -d '{"message_content": "Hello Flashinho!"}'""")
    
    print("\n📝 With channel payload:")
    example_payload = {
        "message_content": "Preciso de ajuda",
        "session_name": "whatsapp_5511999999999",
        "channel_payload": {
            "channel": "evolution",
            "phone_number": "5511999999999",
            "user_name": "João"
        }
    }
    print(f"""curl -X POST http://localhost:8000/api/v1/agent/flashinho_pro_external/run \\
  -H "X-API-Key: namastex888" \\
  -H "Content-Type: application/json" \\
  -d '{json.dumps(example_payload, indent=2)}'""")


async def main():
    """Run all tests."""
    print("\n🚀 Starting Flashinho Tests...\n")
    
    # Check environment
    ext_dir = os.environ.get('AUTOMAGIK_EXTERNAL_AGENTS_DIR')
    print(f"📁 External agents directory: {ext_dir}")
    
    if not Path(ext_dir).exists():
        print(f"❌ Directory {ext_dir} not found!")
        print("Make sure you're running from the am-agents-labs directory")
        return
    
    # Run tests
    results = []
    
    result1 = await test_flashinho_basic()
    results.append(("Basic Test", result1))
    
    result2 = await test_flashinho_with_channel()
    results.append(("Channel Test", result2))
    
    result3 = await test_flashinho_with_evolution_payload()
    results.append(("Evolution Payload Test", result3))
    
    # Summary
    print("\n=== Test Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Flashinho is working correctly.")
        show_api_examples()
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())