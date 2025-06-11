#!/usr/bin/env python3
"""Test the consolidated Claude Code API endpoints."""

import asyncio
import aiohttp
import json
from typing import Dict, Any

BASE_URL = "http://localhost:8881/api/v1"


async def test_endpoint(
    session: aiohttp.ClientSession,
    method: str,
    endpoint: str,
    data: Dict[str, Any] = None,
    description: str = ""
) -> Dict[str, Any]:
    """Test a single endpoint."""
    print(f"\n🔍 Testing: {description}")
    print(f"   {method} {endpoint}")
    
    try:
        if method == "GET":
            async with session.get(f"{BASE_URL}{endpoint}") as response:
                result = await response.json()
                print(f"   ✅ Status: {response.status}")
                return {"success": True, "status": response.status, "data": result}
        elif method == "POST":
            async with session.post(f"{BASE_URL}{endpoint}", json=data) as response:
                result = await response.json()
                print(f"   ✅ Status: {response.status}")
                return {"success": True, "status": response.status, "data": result}
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {"success": False, "error": str(e)}


async def main():
    """Test all Claude Code API endpoints."""
    print("🚀 Testing Consolidated Claude Code API")
    print("=" * 50)
    
    async with aiohttp.ClientSession() as session:
        # 1. Test health endpoint
        health_result = await test_endpoint(
            session, "GET", "/agent/claude-code/health",
            description="Check Claude Code health"
        )
        
        # 2. Test workflows endpoint
        workflows_result = await test_endpoint(
            session, "GET", "/agent/claude-code/workflows",
            description="List available workflows"
        )
        
        # 3. Test run endpoint with workflow_name in body
        run_data = {
            "workflow_name": "architect",
            "message": "Design a simple test architecture",
            "max_turns": 1,
            "git_branch": "test-consolidated-api"
        }
        run_result = await test_endpoint(
            session, "POST", "/agent/claude-code/run",
            data=run_data,
            description="Start architect workflow (workflow_name in body)"
        )
        
        if run_result["success"] and run_result["data"].get("run_id"):
            run_id = run_result["data"]["run_id"]
            print(f"\n   📝 Run ID: {run_id}")
            
            # 4. Test status endpoint (should include logs)
            await asyncio.sleep(2)  # Give it time to start
            status_result = await test_endpoint(
                session, "GET", f"/agent/claude-code/run/{run_id}/status",
                description="Get run status (with logs included)"
            )
            
            if status_result["success"]:
                status_data = status_result["data"]
                print(f"\n   📊 Status Details:")
                print(f"      - Status: {status_data.get('status')}")
                print(f"      - Workflow: {status_data.get('workflow_name')}")
                print(f"      - Container ID: {status_data.get('container_id', 'Not yet assigned')}")
                
                # Check if logs are included
                if status_data.get("logs"):
                    log_lines = status_data["logs"].split('\n')
                    print(f"      - Logs: {len(log_lines)} lines included")
                    print(f"      - First log line: {log_lines[0] if log_lines else 'No logs'}")
                else:
                    print(f"      - Logs: No logs available yet")
        
        # 5. Verify removed endpoints return 404
        print("\n\n🔒 Verifying Removed Endpoints")
        print("=" * 50)
        
        removed_endpoints = [
            ("GET", f"/agent/claude-code/run/fake_run_id/logs", "Individual logs endpoint"),
            ("GET", f"/agent/claude-code/run/fake_run_id/logs/summary", "Log summary endpoint"),
            ("GET", "/agent/claude-code/logs", "List logs endpoint"),
        ]
        
        for method, endpoint, desc in removed_endpoints:
            result = await test_endpoint(session, method, endpoint, description=f"{desc} (should be 404)")
            if result.get("status") == 404:
                print("      ✅ Correctly returns 404")
            else:
                print(f"      ⚠️  Unexpected status: {result.get('status')}")
    
    print("\n\n✅ API consolidation test complete!")
    print("\nConsolidated endpoints:")
    print("  - POST /api/v1/agent/claude-code/run (workflow_name in body)")
    print("  - GET  /api/v1/agent/claude-code/run/{run_id}/status (includes logs)")
    print("  - GET  /api/v1/agent/claude-code/workflows")
    print("  - GET  /api/v1/agent/claude-code/health")


if __name__ == "__main__":
    asyncio.run(main())