#!/usr/bin/env python3
"""Test script for the enhanced workflow manage endpoint."""

import requests
import json
from typing import Dict, Any

# API configuration
BASE_URL = "http://localhost:8000/api/v1"
API_KEY = "test-api-key"  # Replace with your actual API key

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}


def test_list_workflows():
    """Test GET /workflows/claude-code/manage endpoint."""
    print("\n=== Testing GET /workflows/claude-code/manage ===")
    
    response = requests.get(
        f"{BASE_URL}/workflows/claude-code/manage",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        workflows = response.json()
        print(f"Found {len(workflows)} workflows\n")
        
        for workflow in workflows:
            print(f"Workflow: {workflow['name']}")
            print(f"  Display Name: {workflow.get('displayName', 'N/A')}")
            print(f"  Icon: {workflow.get('icon', 'N/A')}")
            print(f"  Color: {workflow.get('mainColour', 'N/A')}")
            print(f"  Category: {workflow.get('category', 'N/A')}")
            print(f"  Emoji: {workflow.get('emoji', 'N/A')}")
            print(f"  Capabilities: {workflow.get('capabilities', [])}")
            print(f"  Suggested Turns: {workflow.get('suggestedTurns', 'N/A')}")
            print()
    else:
        print(f"Error: {response.text}")


def test_create_workflow():
    """Test POST /workflows/claude-code/manage endpoint."""
    print("\n=== Testing POST /workflows/claude-code/manage ===")
    
    workflow_data = {
        "name": "test-custom-workflow",
        "display_name": "Test Custom Workflow",
        "description": "A test workflow to verify enhanced metadata",
        "category": "testing",
        "prompt_template": "You are a test workflow assistant...",
        "allowed_tools": ["Read", "Write", "Edit"],
        "icon": "TestTube",
        "mainColour": "#FF6B6B",
        "emoji": "🧪",
        "capabilities": ["testing", "validation", "experimentation"],
        "suggestedTurns": 25,
        "active": True
    }
    
    response = requests.post(
        f"{BASE_URL}/workflows/claude-code/manage",
        headers=headers,
        json=workflow_data
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code in [200, 201]:
        result = response.json()
        print(f"Success: {result.get('success')}")
        print(f"Message: {result.get('message')}")
        if result.get('workflow'):
            print(f"Created Workflow: {json.dumps(result['workflow'], indent=2)}")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code in [200, 201]


def test_update_workflow():
    """Test PUT /workflows/claude-code/manage endpoint."""
    print("\n=== Testing PUT /workflows/claude-code/manage ===")
    
    workflow_update = {
        "name": "test-custom-workflow",
        "display_name": "Updated Test Workflow",
        "description": "Updated description with enhanced metadata",
        "category": "testing",
        "prompt_template": "You are an updated test workflow assistant...",
        "allowed_tools": ["Read", "Write", "Edit", "TodoWrite"],
        "icon": "FlaskConical",
        "mainColour": "#4ECDC4",
        "emoji": "⚗️",
        "capabilities": ["advanced-testing", "validation", "experimentation", "analysis"],
        "suggestedTurns": 30,
        "active": True
    }
    
    response = requests.put(
        f"{BASE_URL}/workflows/claude-code/manage",
        headers=headers,
        json=workflow_update
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result.get('success')}")
        print(f"Message: {result.get('message')}")
        if result.get('workflow'):
            print(f"Updated Workflow: {json.dumps(result['workflow'], indent=2)}")
    else:
        print(f"Error: {response.text}")


def test_delete_workflow():
    """Test DELETE /workflows/claude-code/manage endpoint."""
    print("\n=== Testing DELETE /workflows/claude-code/manage ===")
    
    response = requests.delete(
        f"{BASE_URL}/workflows/claude-code/manage?name=test-custom-workflow",
        headers=headers
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Success: {result.get('success')}")
        print(f"Message: {result.get('message')}")
    else:
        print(f"Error: {response.text}")


if __name__ == "__main__":
    print("Testing Enhanced Workflow Management Endpoints")
    print("=" * 50)
    
    # Test listing workflows
    test_list_workflows()
    
    # Test creating a custom workflow
    created = test_create_workflow()
    
    # If creation succeeded, test update and delete
    if created:
        test_update_workflow()
        test_delete_workflow()
    
    print("\n✅ Testing completed!")