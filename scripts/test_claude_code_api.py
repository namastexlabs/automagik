#!/usr/bin/env python3
"""
Lightweight automated test script for Claude Code workflow API endpoints.

This script performs simple 1-turn tests with minimal token usage to validate
API functionality without expensive operations.

Usage:
    uv run python scripts/test_claude_code_api.py
"""

import asyncio
import json
import os
import time
import sys
from typing import Dict, Optional
import aiohttp


# Configuration
BASE_URL = os.getenv("AM_BASE_URL", "http://localhost:8881")
API_KEY = os.getenv("AM_API_KEY", "test-key")
TIMEOUT_SECONDS = 30  # Maximum time to wait for workflow completion
POLL_INTERVAL = 2  # Seconds between status checks


class Colors:
    """Terminal colors for output formatting."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_result(test_name: str, passed: bool, details: str = ""):
    """Print test result with color formatting."""
    icon = "✅" if passed else "❌"
    color = Colors.GREEN if passed else Colors.RED
    print(f"{color}{icon} {test_name}: {'PASS' if passed else 'FAIL'}{Colors.RESET}")
    if details:
        print(f"   {details}")


async def make_request(
    session: aiohttp.ClientSession,
    method: str,
    endpoint: str,
    json_data: Optional[Dict] = None
) -> tuple[bool, Dict, str]:
    """Make an HTTP request and return success status, response data, and error message."""
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "x-api-key": API_KEY,  # Fixed: Use x-api-key instead of Authorization
        "Content-Type": "application/json"
    }
    
    try:
        async with session.request(method, url, headers=headers, json=json_data) as response:
            data = await response.json()
            
            if response.status >= 200 and response.status < 300:
                return True, data, ""
            else:
                error_msg = data.get("detail", f"HTTP {response.status}")
                return False, data, error_msg
                
    except aiohttp.ClientError as e:
        return False, {}, f"Connection error: {str(e)}"
    except json.JSONDecodeError as e:
        return False, {}, f"Invalid JSON response: {str(e)}"
    except Exception as e:
        return False, {}, f"Unexpected error: {str(e)}"


async def test_health_check(session: aiohttp.ClientSession) -> bool:
    """Test the health check endpoint."""
    success, data, error = await make_request(session, "GET", "/api/v1/agent/claude-code/health")
    
    if success and data.get("status") == "healthy":
        details = f"Mode: {data.get('mode', 'unknown')}, CLI available: {data.get('claude_cli_available', False)}"
        print_result("Health check", True, details)
        return True
    else:
        print_result("Health check", False, error or "Unhealthy status")
        return False


async def test_list_workflows(session: aiohttp.ClientSession) -> bool:
    """Test listing available workflows."""
    success, data, error = await make_request(session, "GET", "/api/v1/agent/claude-code/workflows")
    
    if success:
        workflows = data if isinstance(data, list) else []
        workflow_names = [w.get("name", "unknown") for w in workflows]
        details = f"Found {len(workflows)} workflows: {', '.join(workflow_names[:5])}"
        if len(workflows) > 5:
            details += f" and {len(workflows) - 5} more"
        print_result("List workflows", True, details)
        return True
    else:
        print_result("List workflows", False, error)
        return False


async def test_architect_workflow(session: aiohttp.ClientSession) -> bool:
    """Test starting and monitoring the architect workflow."""
    # Start the workflow
    request_data = {
        "message": "Say hello",
        "max_turns": 1,
        "git_branch": "test-api"
    }
    
    print(f"{Colors.BLUE}Starting architect workflow...{Colors.RESET}")
    success, data, error = await make_request(
        session, "POST", "/api/v1/agent/claude-code/architect/run", request_data
    )
    
    if not success:
        print_result("Start architect", False, error)
        return False
    
    run_id = data.get("run_id")
    if not run_id:
        print_result("Start architect", False, "No run_id in response")
        return False
    
    print_result("Start architect", True, f"run_id: {run_id}")
    
    # Poll for completion
    print(f"{Colors.YELLOW}⏳ Checking status...{Colors.RESET}")
    start_time = time.time()
    
    while time.time() - start_time < TIMEOUT_SECONDS:
        await asyncio.sleep(POLL_INTERVAL)
        
        success, status_data, error = await make_request(
            session, "GET", f"/api/v1/agent/claude-code/run/{run_id}/status"
        )
        
        if not success:
            print_result("Check status", False, error)
            return False
        
        status = status_data.get("status", "unknown")
        
        if status == "completed":
            execution_time = status_data.get("execution_time", 0)
            result = status_data.get("result", "No result")
            print_result("Workflow completed", True, f"Time: {execution_time:.1f}s")
            return True
        elif status == "failed":
            error_msg = status_data.get("error", "Unknown error")
            print_result("Workflow completed", False, f"Failed: {error_msg}")
            return False
        elif status in ["pending", "running"]:
            # Still processing
            continue
        else:
            print_result("Workflow completed", False, f"Unknown status: {status}")
            return False
    
    print_result("Workflow completed", False, f"Timeout after {TIMEOUT_SECONDS}s")
    return False


async def main():
    """Run all tests."""
    print(f"\n{Colors.BLUE}=== Claude Code API Test Suite ==={Colors.RESET}")
    print(f"Target: {BASE_URL}")
    print(f"API Key: {'***' + API_KEY[-4:] if len(API_KEY) > 4 else '***'}")
    print()
    
    # Track results
    total_tests = 0
    passed_tests = 0
    
    # Create HTTP session
    async with aiohttp.ClientSession() as session:
        # Test 1: Health check
        total_tests += 1
        if await test_health_check(session):
            passed_tests += 1
        
        # Test 2: List workflows
        total_tests += 1
        if await test_list_workflows(session):
            passed_tests += 1
        
        # Test 3: Architect workflow
        total_tests += 1
        if await test_architect_workflow(session):
            passed_tests += 1
    
    # Summary
    print(f"\n{Colors.BLUE}=== Test Summary ==={Colors.RESET}")
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print(f"\n{Colors.GREEN}All tests passed! 🎉{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}Some tests failed.{Colors.RESET}")
        return 1


if __name__ == "__main__":
    # Check if server is accessible first
    import requests
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"{Colors.RED}❌ Server health check failed. Is the server running?{Colors.RESET}")
            print(f"   Try: make dev")
            sys.exit(1)
    except requests.exceptions.RequestException:
        print(f"{Colors.RED}❌ Cannot connect to server at {BASE_URL}{Colors.RESET}")
        print(f"   Make sure the server is running: make dev")
        sys.exit(1)
    
    # Run async tests
    exit_code = asyncio.run(main())
    sys.exit(exit_code)