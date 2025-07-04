#!/usr/bin/env python3
"""Test external agents through the API."""
import os
import sys
import requests
import json
import logging
from pathlib import Path

# Setup
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = "http://localhost:8000"
API_KEY = os.environ.get("AUTOMAGIK_API_KEY", "namastex888")


def test_api_health():
    """Test API is running."""
    logger.info("Testing API health...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code == 200:
            logger.info("✓ API is healthy")
            return True
        else:
            logger.error(f"✗ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        logger.error(f"✗ API not running: {e}")
        logger.info("Start the API with: automagik api")
        return False


def test_list_agents():
    """Test listing all agents including external ones."""
    logger.info("\nTesting agent list...")
    try:
        response = requests.get(
            f"{API_BASE_URL}/api/v1/agent/list",
            headers={"X-API-Key": API_KEY}
        )
        
        if response.status_code == 200:
            agents = response.json()
            external_agents = [a for a in agents if 'flashinho' in a.get('name', '').lower()]
            
            logger.info(f"✓ Found {len(agents)} total agents")
            logger.info(f"✓ Found {len(external_agents)} external agents: {[a['name'] for a in external_agents]}")
            return len(external_agents) > 0
        else:
            logger.error(f"✗ Failed to list agents: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error listing agents: {e}")
        return False


def test_run_external_agent():
    """Test running an external agent."""
    logger.info("\nTesting external agent execution...")
    
    agent_name = "flashinho_pro_external"
    payload = {
        "message_content": "Hello, I'm testing the external agent!",
        "session_name": "test_session",
        "message_type": "text"
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/agent/{agent_name}/run",
            headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"✓ External agent responded successfully")
            logger.info(f"  - Message: {result.get('message', '')[:100]}...")
            logger.info(f"  - Success: {result.get('success', False)}")
            return True
        else:
            logger.error(f"✗ Agent execution failed: {response.status_code}")
            logger.error(f"  - Response: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error running agent: {e}")
        return False


def test_external_agent_with_tools():
    """Test that external agents have their tools registered."""
    logger.info("\nTesting external agent tools...")
    
    # This would require inspecting the agent internally
    # For now, we'll test that the agent can handle tool-related queries
    
    agent_name = "flashinho_pro_external"
    payload = {
        "message_content": "What tools do you have available?",
        "session_name": "test_tools",
        "message_type": "text"
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/api/v1/agent/{agent_name}/run",
            headers={"X-API-Key": API_KEY, "Content-Type": "application/json"},
            json=payload
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info("✓ Agent responded about tools")
            return True
        else:
            logger.error(f"✗ Tool test failed: {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"✗ Error testing tools: {e}")
        return False


def main():
    """Run all API tests."""
    logger.info("=== External Agent API Tests ===\n")
    
    tests = [
        test_api_health,
        test_list_agents,
        test_run_external_agent,
        test_external_agent_with_tools
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            logger.error(f"Test {test.__name__} crashed: {e}")
            results.append(False)
    
    # Summary
    logger.info("\n=== API Test Summary ===")
    passed = sum(results)
    total = len(results)
    logger.info(f"Passed: {passed}/{total}")
    
    if passed == total:
        logger.info("✅ All API tests passed! External agents work through the API.")
    else:
        logger.error("❌ Some API tests failed.")
        if not results[0]:  # API health failed
            logger.info("\nTo start the API server:")
            logger.info("  1. source .venv/bin/activate")
            logger.info("  2. automagik api")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)