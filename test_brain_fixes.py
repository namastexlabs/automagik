#!/usr/bin/env python3
"""Test brain workflow fixes vs other workflows."""

import requests
import time
import json

API_BASE = "http://localhost:48881/api/v1/workflows/claude-code"
API_KEY = "namastex888"
HEADERS = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY
}

def start_workflow(workflow_name, message, max_turns=2):
    """Start a workflow and return run_id."""
    payload = {
        "message": message,
        "sessionName": f"{workflow_name}_test_session",
        "maxTurns": max_turns
    }
    
    response = requests.post(
        f"{API_BASE}/run/{workflow_name}",
        headers=HEADERS,
        json=payload
    )
    
    if response.status_code == 200:
        data = response.json()
        return data["run_id"]
    else:
        print(f"Failed to start {workflow_name}: {response.text}")
        return None

def check_workflow_status(run_id):
    """Check workflow status."""
    response = requests.get(
        f"{API_BASE}/run/{run_id}/status",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get status for {run_id}: {response.text}")
        return None

def test_workflow(workflow_name, message, max_turns=2, timeout=60):
    """Test a workflow and return results."""
    print(f"\n🧪 Testing {workflow_name} workflow...")
    
    # Start workflow
    run_id = start_workflow(workflow_name, message, max_turns)
    if not run_id:
        return {"workflow": workflow_name, "status": "failed_to_start"}
    
    print(f"   Started with run_id: {run_id}")
    
    # Wait for completion
    start_time = time.time()
    while time.time() - start_time < timeout:
        status = check_workflow_status(run_id)
        if not status:
            break
            
        if status["status"] in ["completed", "failed"]:
            execution_time = status.get("execution_time_seconds", 0)
            cost = status.get("metrics", {}).get("cost_usd", 0)
            turns = status.get("progress", {}).get("turns", 0)
            
            result = {
                "workflow": workflow_name,
                "status": status["status"],
                "execution_time": execution_time,
                "cost_usd": cost,
                "turns": turns,
                "run_id": run_id
            }
            
            if status["status"] == "completed":
                print(f"   ✅ COMPLETED in {execution_time}s, {turns} turns, ${cost:.4f}")
            else:
                print(f"   ❌ FAILED in {execution_time}s, {turns} turns, ${cost:.4f}")
            
            return result
        
        time.sleep(2)
    
    # Timeout
    print(f"   ⏰ TIMEOUT after {timeout}s")
    return {"workflow": workflow_name, "status": "timeout", "run_id": run_id}

def main():
    """Run comprehensive workflow testing."""
    print("🔬 Testing Brain Workflow Fixes vs Other Workflows")
    print("=" * 60)
    
    # Test cases for different workflows
    test_cases = [
        {
            "workflow": "builder",
            "message": "Create a simple calculator function",
            "max_turns": 3
        },
        {
            "workflow": "guardian", 
            "message": "Check if there are any Python files in the current directory",
            "max_turns": 2
        },
        {
            "workflow": "brain",
            "message": "Store this pattern data using chunked processing: {\"patterns\": [{\"name\": \"test_fix\", \"problem\": \"streaming issues\", \"solution\": \"buffer management\"}]}",
            "max_turns": 3
        },
        {
            "workflow": "brain",
            "message": "Process this small memory data: {\"learnings\": [{\"insight\": \"chunked processing works\", \"context\": \"testing\"}]}",
            "max_turns": 2
        }
    ]
    
    results = []
    
    # Run tests
    for test_case in test_cases:
        result = test_workflow(
            test_case["workflow"],
            test_case["message"],
            test_case.get("max_turns", 2),
            timeout=90
        )
        results.append(result)
        time.sleep(1)  # Brief pause between tests
    
    # Summary
    print("\n📊 SUMMARY")
    print("=" * 60)
    
    successful = sum(1 for r in results if r["status"] == "completed")
    failed = sum(1 for r in results if r["status"] == "failed")
    timeouts = sum(1 for r in results if r["status"] == "timeout")
    
    print(f"✅ Successful: {successful}/{len(results)}")
    print(f"❌ Failed: {failed}/{len(results)}")
    print(f"⏰ Timeouts: {timeouts}/{len(results)}")
    
    # Brain workflow specific analysis
    brain_results = [r for r in results if r["workflow"] == "brain"]
    other_results = [r for r in results if r["workflow"] != "brain"]
    
    print(f"\n🧠 Brain Workflow: {len([r for r in brain_results if r['status'] == 'completed'])}/{len(brain_results)} successful")
    print(f"🤖 Other Workflows: {len([r for r in other_results if r['status'] == 'completed'])}/{len(other_results)} successful")
    
    # Detailed results
    print(f"\n📋 DETAILED RESULTS")
    print("-" * 60)
    for result in results:
        status_icon = "✅" if result["status"] == "completed" else "❌" if result["status"] == "failed" else "⏰"
        workflow = result["workflow"].ljust(10)
        status = result["status"].ljust(10)
        execution_time = result.get("execution_time", 0)
        turns = result.get("turns", 0)
        cost = result.get("cost_usd", 0)
        
        print(f"{status_icon} {workflow} {status} {execution_time:>6.1f}s {turns:>2d} turns ${cost:>7.4f}")

if __name__ == "__main__":
    main()