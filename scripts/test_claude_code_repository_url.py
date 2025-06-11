#!/usr/bin/env python3
"""Test script for Claude Code API with custom repository URL.

This script demonstrates the new repository_url parameter that allows
Claude Code to work with any Git repository.
"""
import asyncio
import json
import time
import httpx
from typing import Dict, Any
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8881/api/v1"
API_KEY = "test-api-key-123"  # Replace with your actual API key

# Test repositories to try
TEST_REPOSITORIES = [
    {
        "url": "https://github.com/namastexlabs/am-agents-labs.git",
        "branch": "main",
        "message": "List all Python files in the src directory"
    },
    {
        "url": "https://github.com/pydantic/pydantic.git", 
        "branch": "main",
        "message": "Show me the main Pydantic model classes"
    }
]


async def test_repository_url():
    """Test Claude Code with different repository URLs."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        headers = {"x-api-key": API_KEY}
        
        # First, check if Claude Code is available
        print("🔍 Checking Claude Code health...")
        try:
            response = await client.get(
                f"{API_BASE}/agent/claude-code/health",
                headers=headers
            )
            health = response.json()
            
            if not health.get("feature_enabled", False):
                print("❌ Claude Code is not enabled. Make sure Claude CLI is installed.")
                return
            
            print("✅ Claude Code is available")
            print(f"   Agent Available: {health.get('agent_available')}")
            print(f"   Workflows: {list(health.get('workflows', {}).keys())}")
            
        except Exception as e:
            print(f"❌ Failed to check health: {e}")
            return
        
        # Test each repository
        for i, test_repo in enumerate(TEST_REPOSITORIES, 1):
            print(f"\n📦 Test {i}/{len(TEST_REPOSITORIES)}: {test_repo['url']}")
            print(f"   Branch: {test_repo['branch']}")
            print(f"   Task: {test_repo['message']}")
            
            # Start the run
            print("\n🚀 Starting Claude Code run...")
            try:
                run_data = {
                    "message": test_repo["message"],
                    "git_branch": test_repo["branch"],
                    "repository_url": test_repo["url"],
                    "max_turns": 5,  # Keep it small for testing
                    "timeout": 300   # 5 minutes
                }
                
                response = await client.post(
                    f"{API_BASE}/agent/claude-code/architect/run",
                    headers=headers,
                    json=run_data
                )
                
                if response.status_code != 200:
                    print(f"❌ Failed to start run: {response.status_code}")
                    print(f"   Error: {response.text}")
                    continue
                    
                run_info = response.json()
                run_id = run_info["run_id"]
                print(f"✅ Run started: {run_id}")
                
                # Poll for status
                print("\n⏳ Waiting for completion...")
                max_polls = 60  # 5 minutes with 5-second intervals
                polls = 0
                
                while polls < max_polls:
                    await asyncio.sleep(5)
                    polls += 1
                    
                    response = await client.get(
                        f"{API_BASE}/agent/claude-code/run/{run_id}/status",
                        headers=headers
                    )
                    
                    if response.status_code != 200:
                        print(f"❌ Failed to get status: {response.status_code}")
                        break
                        
                    status_info = response.json()
                    status = status_info["status"]
                    
                    print(f"   Status: {status} (poll {polls}/{max_polls})")
                    
                    if status in ["completed", "failed"]:
                        print(f"\n{'✅' if status == 'completed' else '❌'} Run {status}")
                        
                        if status == "completed":
                            print(f"\n📝 Result:")
                            print("-" * 50)
                            result = status_info.get("result", "No result")
                            # Truncate long results
                            if len(result) > 500:
                                print(result[:500] + "...\n[Output truncated]")
                            else:
                                print(result)
                            print("-" * 50)
                            
                            # Show execution details
                            print(f"\n📊 Execution Details:")
                            print(f"   Container ID: {status_info.get('container_id', 'N/A')}")
                            print(f"   Execution Time: {status_info.get('execution_time', 'N/A')}s")
                            print(f"   Exit Code: {status_info.get('exit_code', 'N/A')}")
                            print(f"   Git Commits: {len(status_info.get('git_commits', []))}")
                        else:
                            print(f"\n❌ Error: {status_info.get('error', 'Unknown error')}")
                            
                        break
                        
                if polls >= max_polls:
                    print(f"\n⏱️ Timeout waiting for run to complete")
                    
            except Exception as e:
                print(f"❌ Error during test: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n✅ All tests completed!")


if __name__ == "__main__":
    print("🧪 Claude Code Repository URL Test")
    print("=" * 50)
    asyncio.run(test_repository_url())