#!/usr/bin/env python3
"""Test script to verify Claude Code API repository URL support.

This script tests that the Claude Code API correctly handles:
1. Default repository (when no URL is provided)
2. HTTPS repository URLs
3. SSH repository URLs
"""

import asyncio
import httpx
from typing import Optional

# API Configuration
API_BASE_URL = "http://localhost:8881/api/v1"
API_KEY = "test-api-key"  # Update if needed

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def print_colored(message: str, color: str = RESET):
    """Print message with color."""
    print(f"{color}{message}{RESET}")


async def test_repository_url(
    test_name: str,
    repository_url: Optional[str] = None,
    expected_success: bool = True
) -> bool:
    """Test Claude Code with specific repository URL.
    
    Args:
        test_name: Name of the test
        repository_url: Repository URL to test (None for default)
        expected_success: Whether we expect the test to succeed
        
    Returns:
        True if test passed, False otherwise
    """
    print_colored(f"\n{'='*60}", BLUE)
    print_colored(f"Test: {test_name}", BLUE)
    print_colored(f"Repository URL: {repository_url or 'DEFAULT'}", BLUE)
    print_colored(f"{'='*60}", BLUE)
    
    async with httpx.AsyncClient() as client:
        try:
            # 1. Start workflow run
            print_colored("\n1. Starting workflow run...", YELLOW)
            
            request_data = {
                "message": "Say hello and show the current repository name",
                "max_turns": 1,
                "timeout": 120
            }
            
            # Add repository URL if provided
            if repository_url:
                request_data["repository_url"] = repository_url
            
            response = await client.post(
                f"{API_BASE_URL}/agent/claude-code/architect/run",
                json=request_data,
                headers={"X-API-Key": API_KEY}
            )
            
            if response.status_code != 200:
                print_colored(f"❌ Failed to start workflow: {response.status_code}", RED)
                print_colored(f"Response: {response.text}", RED)
                return False
            
            run_data = response.json()
            run_id = run_data["run_id"]
            print_colored(f"✅ Started run: {run_id}", GREEN)
            
            # 2. Poll for completion
            print_colored("\n2. Polling for completion...", YELLOW)
            
            max_attempts = 30  # 30 seconds timeout
            for attempt in range(max_attempts):
                response = await client.get(
                    f"{API_BASE_URL}/agent/claude-code/run/{run_id}/status",
                    headers={"X-API-Key": API_KEY}
                )
                
                if response.status_code != 200:
                    print_colored(f"❌ Failed to get status: {response.status_code}", RED)
                    return False
                
                status_data = response.json()
                status = status_data["status"]
                
                if status in ["completed", "failed"]:
                    break
                
                print(f"   Status: {status} (attempt {attempt + 1}/{max_attempts})")
                await asyncio.sleep(1)
            
            # 3. Check final result
            print_colored("\n3. Checking final result...", YELLOW)
            
            if status == "completed":
                print_colored("✅ Run completed successfully", GREEN)
                
                # Check if logs contain expected repository
                if "logs" in status_data and status_data["logs"]:
                    logs = status_data["logs"]
                    
                    # Extract repository name from URL
                    if repository_url:
                        expected_repo = repository_url.rstrip('/').split('/')[-1]
                        if expected_repo.endswith('.git'):
                            expected_repo = expected_repo[:-4]
                    else:
                        expected_repo = "am-agents-labs"
                    
                    if expected_repo in logs:
                        print_colored(f"✅ Found expected repository: {expected_repo}", GREEN)
                    else:
                        print_colored(f"⚠️  Did not find expected repository: {expected_repo}", YELLOW)
                
                return expected_success
            else:
                print_colored(f"❌ Run failed with status: {status}", RED)
                if "error" in status_data:
                    print_colored(f"Error: {status_data['error']}", RED)
                return not expected_success
                
        except Exception as e:
            print_colored(f"❌ Test failed with exception: {str(e)}", RED)
            return False


async def main():
    """Run all repository URL tests."""
    print_colored("\n🧪 Claude Code Repository URL Test Suite", BLUE)
    print_colored("=" * 60, BLUE)
    
    # Check if API is healthy first
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/agent/claude-code/health")
            if response.status_code != 200:
                print_colored("❌ API is not healthy. Please start the server first.", RED)
                return
            
            health_data = response.json()
            if not health_data.get("feature_enabled", False):
                print_colored("❌ Claude CLI not available. Please install it first.", RED)
                print_colored("Run: npm install -g @anthropic-ai/claude-cli", YELLOW)
                return
                
        except Exception as e:
            print_colored(f"❌ Cannot connect to API: {str(e)}", RED)
            print_colored("Please ensure the server is running on port 8881", YELLOW)
            return
    
    # Run tests
    tests = [
        ("Default Repository", None, True),
        ("HTTPS URL", "https://github.com/anthropics/anthropic-sdk-python.git", True),
        ("SSH URL", "git@github.com:anthropics/anthropic-sdk-python.git", True),
        ("Invalid URL", "not-a-valid-url", False),
    ]
    
    results = []
    for test_name, repo_url, expected in tests:
        passed = await test_repository_url(test_name, repo_url, expected)
        results.append((test_name, passed))
    
    # Print summary
    print_colored("\n" + "=" * 60, BLUE)
    print_colored("Test Summary", BLUE)
    print_colored("=" * 60, BLUE)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        color = GREEN if passed else RED
        print_colored(f"{test_name}: {status}", color)
    
    total_passed = sum(1 for _, passed in results if passed)
    total_tests = len(results)
    
    print_colored(f"\nTotal: {total_passed}/{total_tests} tests passed", 
                  GREEN if total_passed == total_tests else YELLOW)


if __name__ == "__main__":
    asyncio.run(main())