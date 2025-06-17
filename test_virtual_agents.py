#!/usr/bin/env python3
"""Test script for virtual agent functionality."""

import json
import requests
import time

# API base URL
BASE_URL = "http://localhost:8000"

def test_virtual_agent_creation():
    """Test creating a virtual agent."""
    print("🧪 Testing virtual agent creation...")
    
    # Create a virtual agent
    virtual_agent_config = {
        "name": "test_virtual_assistant",
        "type": "pydanticai",
        "model": "openai:gpt-4o-mini",
        "description": "A test virtual agent for customer support",
        "config": {
            "agent_source": "virtual",
            "default_model": "openai:gpt-4o",
            "tool_config": {
                "enabled_tools": ["memory", "datetime"],
                "tool_permissions": {
                    "memory": {"max_results": 10},
                    "datetime": {}
                }
            }
        }
    }
    
    try:
        response = requests.post(f"{BASE_URL}/agent/create", json=virtual_agent_config)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Virtual agent creation successful!")
            return True
        else:
            print("❌ Virtual agent creation failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing virtual agent creation: {e}")
        return False

def test_tool_discovery():
    """Test tool discovery endpoint."""
    print("🔧 Testing tool discovery...")
    
    try:
        response = requests.get(f"{BASE_URL}/tools")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            tools = response.json()
            print(f"Found {len(tools)} tools:")
            for tool in tools:
                print(f"  - {tool['name']} ({tool['type']}): {tool['description']}")
            print("✅ Tool discovery successful!")
            return True
        else:
            print("❌ Tool discovery failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing tool discovery: {e}")
        return False

def test_virtual_agent_execution():
    """Test executing a virtual agent."""
    print("🚀 Testing virtual agent execution...")
    
    execution_request = {
        "message_content": "Hello! Can you help me with something?",
        "session_name": "test_virtual_session",
        "user_id": "test_user"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/agent/test_virtual_assistant/run", json=execution_request)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Virtual agent execution successful!")
            return True
        else:
            print("❌ Virtual agent execution failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing virtual agent execution: {e}")
        return False

def test_agent_copy():
    """Test copying an agent with new prompt."""
    print("📋 Testing agent copy with new prompt...")
    
    copy_request = {
        "new_name": "test_virtual_assistant_friendly",
        "description": "Friendly version of test virtual assistant",
        "system_prompt": "You are an extremely friendly and enthusiastic AI assistant! Use lots of emojis 😊 and always be super positive and helpful! Make every interaction delightful! 🌟"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/agent/test_virtual_assistant/copy", json=copy_request)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Agent copy successful!")
            return True
        else:
            print("❌ Agent copy failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing agent copy: {e}")
        return False

def test_agent_listing():
    """Test listing agents."""
    print("📋 Testing agent listing...")
    
    try:
        response = requests.get(f"{BASE_URL}/agent/list")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            agents = response.json()
            print(f"Found {len(agents)} agents:")
            for agent in agents:
                print(f"  - {agent['name']}: {agent.get('description', 'No description')}")
            print("✅ Agent listing successful!")
            return True
        else:
            print("❌ Agent listing failed")
            return False
            
    except Exception as e:
        print(f"❌ Error testing agent listing: {e}")
        return False

def main():
    """Run all tests."""
    print("🎯 Starting Virtual Agent Tests")
    print("=" * 50)
    
    tests = [
        ("Tool Discovery", test_tool_discovery),
        ("Agent Listing", test_agent_listing),
        ("Virtual Agent Creation", test_virtual_agent_creation),
        ("Agent Copy with New Prompt", test_agent_copy),
        ("Virtual Agent Execution", test_virtual_agent_execution),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{test_name}")
        print("-" * len(test_name))
        success = test_func()
        results.append((test_name, success))
        time.sleep(1)  # Brief pause between tests
    
    print("\n" + "=" * 50)
    print("📊 Test Results Summary")
    print("=" * 50)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Virtual agents are working!")
    else:
        print("⚠️  Some tests failed. Check the output above.")

if __name__ == "__main__":
    main()