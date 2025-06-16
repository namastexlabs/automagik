#!/usr/bin/env python3
"""Test the final Claude Code API after cleanup."""

import asyncio
import httpx

# API configuration
BASE_URL = "http://localhost:28881/api/v1"
API_KEY = "namastex888"

async def test_api():
    """Test all Claude Code API endpoints."""
    
    async with httpx.AsyncClient() as client:
        headers = {"x-api-key": API_KEY}
        
        print("🧪 Testing Claude Code API after cleanup...")
        print("=" * 60)
        
        # 1. Test health endpoint
        print("\n1️⃣ Testing /health endpoint...")
        response = await client.get(
            f"{BASE_URL}/workflows/claude-code/health",
            headers=headers
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Health: {health.get('status')}")
            print(f"   Claude CLI: {health.get('feature_enabled')}")
            print(f"   Agent Available: {health.get('agent_available')}")
        else:
            print(f"❌ Error: {response.text}")
        
        # 2. Test workflows endpoint
        print("\n2️⃣ Testing /workflows endpoint...")
        response = await client.get(
            f"{BASE_URL}/workflows/claude-code/workflows",
            headers=headers
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            workflows = response.json()
            print(f"✅ Found {len(workflows)} workflows:")
            for wf in workflows[:3]:  # Show first 3
                print(f"   - {wf['name']}: {wf['description'][:50]}...")
        else:
            print(f"❌ Error: {response.text}")
        
        # 3. Test run endpoint with workflow in body
        print("\n3️⃣ Testing /run endpoint (workflow in body)...")
        run_data = {
            "workflow_name": "test",
            "message": "Hello! What are your top 3 tools?",
            "max_turns": 1,
            "repository_url": "https://github.com/anthropics/claude-cli.git"
        }
        response = await client.post(
            f"{BASE_URL}/workflows/claude-code/run",
            headers=headers,
            json=run_data
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            run_response = response.json()
            run_id = run_response.get("run_id")
            print(f"✅ Run started: {run_id}")
            print(f"   Status: {run_response.get('status')}")
            print(f"   Workflow: {run_response.get('workflow_name')}")
            
            # 4. Test status endpoint (should include logs)
            print("\n4️⃣ Testing /run/{run_id}/status endpoint...")
            print("   Waiting 5 seconds for execution...")
            await asyncio.sleep(5)
            
            response = await client.get(
                f"{BASE_URL}/workflows/claude-code/run/{run_id}/status",
                headers=headers
            )
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                status = response.json()
                print(f"✅ Run Status: {status.get('status')}")
                print(f"   Execution Time: {status.get('execution_time')}s")
                
                # Check if logs are included
                logs = status.get('logs', '')
                if logs:
                    log_lines = logs.split('\n')
                    print(f"   Logs Included: ✅ ({len(log_lines)} lines)")
                    print(f"   First log: {log_lines[0][:100]}..." if log_lines else "")
                    print(f"   Last log: {log_lines[-1][:100]}..." if len(log_lines) > 1 else "")
                else:
                    print("   Logs Included: ❌ (empty)")
                
                # Check result
                if status.get('result'):
                    print(f"   Result: {status.get('result')[:200]}...")
            else:
                print(f"❌ Error: {response.text}")
        else:
            print(f"❌ Error: {response.text}")
        
        # 5. Test that removed endpoints are gone
        print("\n5️⃣ Testing that removed endpoints return 404...")
        removed_endpoints = [
            "/workflows/claude-code/run/test",  # Old path-based workflow
            "/workflows/claude-code/run/test_run/logs",  # Removed logs endpoint
            "/workflows/claude-code/run/test_run/logs/summary",  # Removed summary
            "/workflows/claude-code/logs"  # Removed list logs
        ]
        
        for endpoint in removed_endpoints:
            response = await client.get(f"{BASE_URL}{endpoint}", headers=headers)
            if response.status_code == 404:
                print(f"   ✅ {endpoint} -> 404 (correctly removed)")
            else:
                print(f"   ❌ {endpoint} -> {response.status_code} (should be 404)")
        
        print("\n" + "=" * 60)
        print("✅ API cleanup test completed!")


if __name__ == "__main__":
    asyncio.run(test_api())