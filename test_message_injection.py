#!/usr/bin/env python3
"""
Test script for workflow message injection functionality.

This script demonstrates how to inject messages into running workflows.
"""

import requests
import json
import time
from typing import Dict, Any

# Configuration
API_BASE_URL = "http://localhost:18881/api/v1"
API_KEY = "namastex888"
HEADERS = {
    "accept": "application/json",
    "x-api-key": API_KEY,
    "Content-Type": "application/json"
}

def start_workflow(workflow_name: str, message: str) -> Dict[str, Any]:
    """Start a new workflow and return the run_id."""
    
    url = f"{API_BASE_URL}/workflows/claude-code/run/{workflow_name}"
    
    payload = {
        "message": message,
        "max_turns": 10,
        "session_id": None,
        "session_name": "message-injection-test",
        "timeout": 7200
    }
    
    print(f"🚀 Starting workflow '{workflow_name}'...")
    response = requests.post(url, json=payload, headers=HEADERS)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Workflow started: {result['run_id']}")
        return result
    else:
        print(f"❌ Failed to start workflow: {response.status_code}")
        print(response.text)
        return {}

def inject_message(run_id: str, message: str) -> Dict[str, Any]:
    """Inject a message into a running workflow."""
    
    url = f"{API_BASE_URL}/workflows/claude-code/run/{run_id}/inject-message"
    
    payload = {
        "message": message
    }
    
    print(f"💉 Injecting message into {run_id}...")
    response = requests.post(url, json=payload, headers=HEADERS)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Message injected: {result['message_id']}")
        return result
    else:
        print(f"❌ Failed to inject message: {response.status_code}")
        print(response.text)
        return {}

def get_workflow_status(run_id: str) -> Dict[str, Any]:
    """Get the status of a workflow."""
    
    url = f"{API_BASE_URL}/workflows/claude-code/run/{run_id}/status"
    
    response = requests.get(url, headers=HEADERS)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"❌ Failed to get status: {response.status_code}")
        return {}

def main():
    """Test the message injection functionality."""
    
    print("🧪 Testing Workflow Message Injection")
    print("=" * 50)
    
    # Step 1: Start a workflow
    workflow_result = start_workflow(
        "flashinho_thinker",
        "Please analyze the benefits of microservices architecture"
    )
    
    if not workflow_result:
        return
    
    run_id = workflow_result["run_id"]
    
    # Step 2: Wait a moment for workflow to start
    print("\n⏳ Waiting for workflow to start...")
    time.sleep(5)
    
    # Step 3: Check initial status
    status = get_workflow_status(run_id)
    print(f"\n📊 Initial Status: {status.get('status', 'unknown')}")
    
    # Step 4: Inject a message
    inject_result = inject_message(
        run_id,
        "Please also compare microservices with monolithic architecture"
    )
    
    # Step 5: Inject another message
    time.sleep(2)
    inject_result_2 = inject_message(
        run_id,
        "Focus specifically on scalability differences"
    )
    
    # Step 6: Check final status
    time.sleep(3)
    final_status = get_workflow_status(run_id)
    print(f"\n📊 Final Status: {final_status.get('status', 'unknown')}")
    
    print("\n✅ Test completed!")
    print(f"Run ID: {run_id}")
    print("Check the workflow logs to see if messages were processed.")

if __name__ == "__main__":
    main()