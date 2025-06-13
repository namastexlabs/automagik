#!/usr/bin/env python3
"""
Edge case tests for Claude Code API endpoints.

This script tests various edge cases and error scenarios to ensure robust API behavior.

Usage:
    uv run python scripts/test_claude_code_edge_cases.py
"""

import asyncio
import os
from typing import Dict, Optional
import aiohttp


# Configuration
BASE_URL = os.getenv("AM_BASE_URL", "http://localhost:28881")
API_KEY = os.getenv("AM_API_KEY", "namastex888")


class Colors:
    """Terminal colors for output formatting."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'


def print_test_header(test_name: str):
    """Print a test section header."""
    print(f"\n{Colors.BLUE}--- {test_name} ---{Colors.RESET}")


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
    json_data: Optional[Dict] = None,
    headers: Optional[Dict] = None
) -> tuple[int, Dict, str]:
    """Make an HTTP request and return status code, response data, and error message."""
    url = f"{BASE_URL}{endpoint}"
    if headers is None:
        headers = {
            "x-api-key": API_KEY,
            "Content-Type": "application/json"
        }
    
    try:
        async with session.request(method, url, headers=headers, json=json_data) as response:
            try:
                data = await response.json()
            except Exception:
                data = {"raw_text": await response.text()}
            return response.status, data, ""
    except aiohttp.ClientError as e:
        return 0, {}, f"Connection error: {str(e)}"
    except Exception as e:
        return 0, {}, f"Unexpected error: {str(e)}"


async def test_authentication():
    """Test authentication edge cases."""
    print_test_header("Authentication Tests")
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Missing API key
        headers = {"Content-Type": "application/json"}
        status, data, error = await make_request(
            session, "GET", "/api/v1/agent/claude-code/workflows", headers=headers
        )
        expected = status == 401 and "x-api-key is missing" in str(data)
        print_result("Missing API key", expected, f"Status: {status}")
        
        # Test 2: Invalid API key
        headers = {"x-api-key": "invalid-key-123", "Content-Type": "application/json"}
        status, data, error = await make_request(
            session, "GET", "/api/v1/agent/claude-code/workflows", headers=headers
        )
        expected = status == 401 and "Invalid API" in str(data)
        print_result("Invalid API key", expected, f"Status: {status}")
        
        # Test 3: API key in query params
        status, data, error = await make_request(
            session, "GET", f"/api/v1/agent/claude-code/workflows?x-api-key={API_KEY}", 
            headers={"Content-Type": "application/json"}
        )
        expected = status == 200
        print_result("API key in query params", expected, f"Status: {status}")


async def test_invalid_endpoints():
    """Test invalid endpoint handling."""
    print_test_header("Invalid Endpoint Tests")
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Non-existent workflow
        status, data, error = await make_request(
            session, "POST", "/api/v1/agent/claude-code/nonexistent/run",
            json_data={"message": "test"}
        )
        expected = status == 404
        print_result("Non-existent workflow", expected, f"Status: {status}")
        
        # Test 2: Invalid run ID format
        status, data, error = await make_request(
            session, "GET", "/api/v1/agent/claude-code/run/invalid-id-format/status"
        )
        expected = status in [404, 422]
        print_result("Invalid run ID format", expected, f"Status: {status}")


async def test_invalid_payloads():
    """Test invalid request payloads."""
    print_test_header("Invalid Payload Tests")
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Empty payload
        status, data, error = await make_request(
            session, "POST", "/api/v1/agent/claude-code/architect/run",
            json_data={}
        )
        expected = status == 422  # Unprocessable Entity
        print_result("Empty payload", expected, f"Status: {status}, Error: {data.get('detail', '')}")
        
        # Test 2: Missing required field
        status, data, error = await make_request(
            session, "POST", "/api/v1/agent/claude-code/architect/run",
            json_data={"max_turns": 1}  # Missing 'message'
        )
        expected = status == 422
        print_result("Missing required field", expected, f"Status: {status}")
        
        # Test 3: Invalid max_turns
        status, data, error = await make_request(
            session, "POST", "/api/v1/agent/claude-code/architect/run",
            json_data={"message": "test", "max_turns": 0}
        )
        expected = status == 422
        print_result("Invalid max_turns (0)", expected, f"Status: {status}")
        
        # Test 4: Exceeding max_turns limit
        status, data, error = await make_request(
            session, "POST", "/api/v1/agent/claude-code/architect/run",
            json_data={"message": "test", "max_turns": 200}
        )
        expected = status == 422
        print_result("Exceeding max_turns (200)", expected, f"Status: {status}")
        
        # Test 5: Invalid timeout
        status, data, error = await make_request(
            session, "POST", "/api/v1/agent/claude-code/architect/run",
            json_data={"message": "test", "timeout": 30}  # Too short
        )
        expected = status == 422
        print_result("Invalid timeout (30s)", expected, f"Status: {status}")


async def test_edge_case_values():
    """Test edge case values in valid requests."""
    print_test_header("Edge Case Value Tests")
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Very long message
        long_message = "x" * 10000  # 10k characters
        status, data, error = await make_request(
            session, "POST", "/api/v1/agent/claude-code/architect/run",
            json_data={"message": long_message, "max_turns": 1}
        )
        expected = status in [200, 201]
        print_result("Very long message (10k chars)", expected, f"Status: {status}")
        
        # Test 2: Special characters in message
        special_message = "Test with 特殊文字 and emojis 🚀 and \n newlines"
        status, data, error = await make_request(
            session, "POST", "/api/v1/agent/claude-code/architect/run",
            json_data={"message": special_message, "max_turns": 1}
        )
        expected = status in [200, 201]
        print_result("Special characters in message", expected, f"Status: {status}")
        
        # Test 3: Boundary values for max_turns
        status, data, error = await make_request(
            session, "POST", "/api/v1/agent/claude-code/architect/run",
            json_data={"message": "test", "max_turns": 1}  # Minimum
        )
        expected = status in [200, 201]
        print_result("Minimum max_turns (1)", expected, f"Status: {status}")
        
        status, data, error = await make_request(
            session, "POST", "/api/v1/agent/claude-code/architect/run",
            json_data={"message": "test", "max_turns": 100}  # Maximum
        )
        expected = status in [200, 201]
        print_result("Maximum max_turns (100)", expected, f"Status: {status}")


async def test_concurrent_requests():
    """Test concurrent request handling."""
    print_test_header("Concurrent Request Tests")
    
    async with aiohttp.ClientSession() as session:
        # Launch multiple requests simultaneously
        tasks = []
        for i in range(5):
            task = make_request(
                session, "GET", "/api/v1/agent/claude-code/workflows"
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        success_count = sum(1 for status, _, _ in results if status == 200)
        
        expected = success_count == 5
        print_result("5 concurrent requests", expected, f"{success_count}/5 succeeded")


async def test_session_handling():
    """Test session-related edge cases."""
    print_test_header("Session Handling Tests")
    
    async with aiohttp.ClientSession() as session:
        # Test 1: Invalid session ID
        status, data, error = await make_request(
            session, "POST", "/api/v1/agent/claude-code/architect/run",
            json_data={
                "message": "test",
                "session_id": "invalid-session-123",
                "max_turns": 1
            }
        )
        # Should create new session or fail gracefully
        expected = status in [200, 201, 404]
        print_result("Invalid session ID", expected, f"Status: {status}")
        
        # Test 2: Very long session name
        long_name = "session_" + "x" * 500
        status, data, error = await make_request(
            session, "POST", "/api/v1/agent/claude-code/architect/run",
            json_data={
                "message": "test",
                "session_name": long_name,
                "max_turns": 1
            }
        )
        expected = status in [200, 201, 422]
        print_result("Very long session name", expected, f"Status: {status}")


async def main():
    """Run all edge case tests."""
    print(f"\n{Colors.BLUE}=== Claude Code API Edge Case Test Suite ==={Colors.RESET}")
    print(f"Target: {BASE_URL}")
    print(f"API Key: {'***' + API_KEY[-4:] if len(API_KEY) > 4 else '***'}")
    
    # Run test categories
    await test_authentication()
    await test_invalid_endpoints()
    await test_invalid_payloads()
    await test_edge_case_values()
    await test_concurrent_requests()
    await test_session_handling()
    
    print(f"\n{Colors.GREEN}Edge case testing completed!{Colors.RESET}")


if __name__ == "__main__":
    # Run async tests
    asyncio.run(main())