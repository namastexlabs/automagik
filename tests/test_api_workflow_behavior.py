#!/usr/bin/env python3
"""Test API workflow behavior with different parameters.

This validates how the API endpoints handle different workflow parameters
and what actual workspaces/branches/paths get created.
"""

import asyncio
import json
import requests
import sys
import time
from pathlib import Path
from typing import Dict, Any
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automagik.agents.claude_code.models import ClaudeCodeRunRequest


class APIWorkflowTester:
    """Test API workflow behavior with real requests."""
    
    def __init__(self, api_base_url: str = "http://localhost:18881", api_key: str = "namastex888"):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        self.test_results = []
        self.created_runs = []  # Track created runs
        
    def log_result(self, category: str, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        status = "✅" if passed else "❌"
        print(f"  {status} {test_name}: {details}")
        self.test_results.append((category, test_name, passed, details))
        
    def make_request(self, method: str, endpoint: str, data: Dict = None) -> requests.Response:
        """Make API request."""
        url = f"{self.api_base_url}{endpoint}"
        
        if method.upper() == "POST":
            response = requests.post(url, headers=self.headers, json=data)
        elif method.upper() == "GET":
            response = requests.get(url, headers=self.headers)
        else:
            raise ValueError(f"Unsupported method: {method}")
            
        return response
        
    def test_api_connectivity(self):
        """Test basic API connectivity."""
        print(f"\n🧪 Testing API connectivity...")
        
        try:
            response = self.make_request("GET", "/health")
            is_healthy = response.status_code == 200
            self.log_result("API Connectivity", "health_check", is_healthy, f"Status: {response.status_code}")
            
            if is_healthy:
                health_data = response.json()
                self.log_result("API Connectivity", "health_response", "status" in health_data)
                
        except Exception as e:
            self.log_result("API Connectivity", "connection", False, str(e))
            
    def test_worktree_workflow_creation(self):
        """Test creating a workflow with default worktree behavior."""
        print(f"\n🧪 Testing worktree workflow creation...")
        
        workflow_name = "builder"
        request_data = {
            "message": "Create a simple test file in worktree workspace",
            "max_turns": 5,
            "timeout": 300,
            "persistent": True
        }
        
        try:
            response = self.make_request("POST", f"/api/v1/workflows/claude-code/run/{workflow_name}", request_data)
            
            success = response.status_code == 200
            self.log_result("Worktree Workflow", "request_accepted", success, f"Status: {response.status_code}")
            
            if success:
                result = response.json()
                run_id = result.get("run_id")
                
                has_run_id = bool(run_id)
                self.log_result("Worktree Workflow", "has_run_id", has_run_id, run_id)
                
                has_workspace_path = "workspace_path" in result
                self.log_result("Worktree Workflow", "has_workspace_path", has_workspace_path)
                
                if has_workspace_path:
                    workspace_path = result["workspace_path"]
                    # Should be in worktrees directory for local development
                    is_worktree = "worktrees" in workspace_path
                    self.log_result("Worktree Workflow", "is_worktree_path", is_worktree, workspace_path)
                    
                    # Check if workspace actually exists
                    if Path(workspace_path).exists():
                        self.log_result("Worktree Workflow", "workspace_exists", True, workspace_path)
                    else:
                        self.log_result("Worktree Workflow", "workspace_exists", False, "Path not found")
                        
                if run_id:
                    self.created_runs.append(run_id)
                    
        except Exception as e:
            self.log_result("Worktree Workflow", "creation_error", False, str(e))
            
    def test_custom_branch_workflow(self):
        """Test creating a workflow with custom branch."""
        print(f"\n🧪 Testing custom branch workflow...")
        
        custom_branch = f"feature/api-test-{int(datetime.now().timestamp())}"
        workflow_name = "surgeon"
        
        request_data = {
            "message": "Test custom branch creation via API",
            "git_branch": custom_branch,
            "max_turns": 5,
            "timeout": 300,
            "persistent": True
        }
        
        try:
            response = self.make_request("POST", f"/api/v1/workflows/claude-code/run/{workflow_name}", request_data)
            
            success = response.status_code == 200
            self.log_result("Custom Branch", "request_accepted", success, f"Status: {response.status_code}")
            
            if success:
                result = response.json()
                run_id = result.get("run_id")
                workspace_path = result.get("workspace_path")
                
                self.log_result("Custom Branch", "has_run_id", bool(run_id), run_id)
                self.log_result("Custom Branch", "has_workspace_path", bool(workspace_path), workspace_path)
                
                # Branch name should be reflected in workspace path or result
                if workspace_path:
                    branch_in_path = custom_branch.replace("/", "-") in workspace_path
                    self.log_result("Custom Branch", "branch_reflected_in_path", branch_in_path)
                    
                if run_id:
                    self.created_runs.append(run_id)
                    
        except Exception as e:
            self.log_result("Custom Branch", "custom_branch_error", False, str(e))
            
    def test_temp_workspace_workflow(self):
        """Test creating a workflow with temporary workspace."""
        print(f"\n🧪 Testing temporary workspace workflow...")
        
        workflow_name = "builder"
        request_data = {
            "message": "Test temporary workspace creation",
            "temp_workspace": True,
            "max_turns": 3,
            "timeout": 300,
            "persistent": False
        }
        
        try:
            response = self.make_request("POST", f"/api/v1/workflows/claude-code/run/{workflow_name}", request_data)
            
            success = response.status_code == 200
            self.log_result("Temp Workspace", "request_accepted", success, f"Status: {response.status_code}")
            
            if success:
                result = response.json()
                run_id = result.get("run_id")
                workspace_path = result.get("workspace_path")
                
                self.log_result("Temp Workspace", "has_run_id", bool(run_id), run_id)
                
                if workspace_path:
                    # Should be in temp directory
                    is_temp_path = "/tmp" in workspace_path
                    self.log_result("Temp Workspace", "is_temp_path", is_temp_path, workspace_path)
                    
                if run_id:
                    self.created_runs.append(run_id)
                    
        except Exception as e:
            self.log_result("Temp Workspace", "temp_workspace_error", False, str(e))
            
    def test_parameter_validation(self):
        """Test parameter validation by the API."""
        print(f"\n🧪 Testing parameter validation...")
        
        # Test 1: Invalid combination (temp_workspace + git_branch)
        workflow_name = "builder"
        invalid_request = {
            "message": "This should fail",
            "temp_workspace": True,
            "git_branch": "feature/test"
        }
        
        try:
            response = self.make_request("POST", f"/api/v1/workflows/claude-code/run/{workflow_name}", invalid_request)
            
            should_fail = response.status_code != 200
            self.log_result("Parameter Validation", "invalid_temp_git_rejected", should_fail, 
                          f"Status: {response.status_code}")
                          
            if response.status_code != 200:
                error_response = response.json()
                has_error_message = "error" in error_response or "detail" in error_response
                self.log_result("Parameter Validation", "has_error_message", has_error_message)
                
        except Exception as e:
            self.log_result("Parameter Validation", "validation_test_error", False, str(e))
            
        # Test 2: Empty message
        empty_message_request = {
            "message": ""
        }
        
        try:
            response = self.make_request("POST", f"/api/v1/workflows/claude-code/run/{workflow_name}", empty_message_request)
            
            should_fail = response.status_code != 200
            self.log_result("Parameter Validation", "empty_message_rejected", should_fail, 
                          f"Status: {response.status_code}")
                          
        except Exception as e:
            self.log_result("Parameter Validation", "empty_message_test_error", False, str(e))
            
    def test_workflow_status_tracking(self):
        """Test workflow status tracking."""
        print(f"\n🧪 Testing workflow status tracking...")
        
        try:
            # Get list of workflows
            response = self.make_request("GET", "/api/v1/workflows/claude-code/runs")
            
            success = response.status_code == 200
            self.log_result("Status Tracking", "runs_list_accessible", success, f"Status: {response.status_code}")
            
            if success:
                runs_data = response.json()
                is_list = isinstance(runs_data, list)
                self.log_result("Status Tracking", "returns_list", is_list)
                
                if is_list and len(runs_data) > 0:
                    # Check structure of first run
                    first_run = runs_data[0]
                    has_run_id = "run_id" in first_run
                    has_status = "status" in first_run
                    has_workflow_name = "workflow_name" in first_run
                    
                    self.log_result("Status Tracking", "run_has_run_id", has_run_id)
                    self.log_result("Status Tracking", "run_has_status", has_status)
                    self.log_result("Status Tracking", "run_has_workflow_name", has_workflow_name)
                    
                    # Check if any of our created runs appear in the list
                    found_created_runs = 0
                    for run_id in self.created_runs:
                        for run_data in runs_data:
                            if run_data.get("run_id") == run_id:
                                found_created_runs += 1
                                break
                                
                    all_found = found_created_runs == len(self.created_runs)
                    self.log_result("Status Tracking", "created_runs_tracked", all_found, 
                                  f"Found {found_created_runs}/{len(self.created_runs)}")
                                  
        except Exception as e:
            self.log_result("Status Tracking", "status_tracking_error", False, str(e))
            
    def test_workflow_differences(self):
        """Test different workflow types produce different behavior."""
        print(f"\n🧪 Testing workflow differences...")
        
        workflows_to_test = ["builder", "surgeon", "guardian"]
        workflow_results = {}
        
        for workflow_name in workflows_to_test:
            request_data = {
                "message": f"Test {workflow_name} workflow behavior",
                "max_turns": 3,
                "timeout": 300,
                "persistent": True
            }
            
            try:
                response = self.make_request("POST", f"/api/v1/workflows/claude-code/run/{workflow_name}", request_data)
                
                if response.status_code == 200:
                    result = response.json()
                    workflow_results[workflow_name] = result
                    
                    run_id = result.get("run_id")
                    if run_id:
                        self.created_runs.append(run_id)
                        
                    self.log_result("Workflow Differences", f"{workflow_name}_created", True, 
                                  result.get("workspace_path", ""))
                else:
                    self.log_result("Workflow Differences", f"{workflow_name}_failed", False, 
                                  f"Status: {response.status_code}")
                    
            except Exception as e:
                self.log_result("Workflow Differences", f"{workflow_name}_error", False, str(e))
                
        # Compare results
        if len(workflow_results) >= 2:
            workspace_paths = [r.get("workspace_path", "") for r in workflow_results.values()]
            all_different = len(set(workspace_paths)) == len(workspace_paths)
            self.log_result("Workflow Differences", "different_workspaces", all_different,
                          f"Paths: {workspace_paths}")
                          
            # Check that workflow names are reflected in paths
            paths_contain_names = all(
                workflow_name in workspace_path 
                for workflow_name, result in workflow_results.items()
                for workspace_path in [result.get("workspace_path", "")]
                if workspace_path
            )
            self.log_result("Workflow Differences", "names_in_paths", paths_contain_names)
            
    def print_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "="*60)
        print("📊 API Workflow Behavior Test Summary")
        print("="*60)
        
        # Group by category
        categories = {}
        for category, test, passed, details in self.test_results:
            if category not in categories:
                categories[category] = []
            categories[category].append((test, passed, details))
            
        total_passed = 0
        total_tests = 0
        
        for category, tests in categories.items():
            passed = sum(1 for _, p, _ in tests if p)
            total = len(tests)
            total_passed += passed
            total_tests += total
            
            print(f"\n{category}: {passed}/{total} passed")
            for test, passed, details in tests:
                status = "✅" if passed else "❌"
                detail_str = f" - {details}" if details else ""
                print(f"  {status} {test}{detail_str}")
                
        print(f"\n{'='*60}")
        print(f"Total: {total_passed}/{total_tests} tests passed")
        
        if total_passed == total_tests:
            print("\n✅ All API workflow behavior tests passed!")
        else:
            print(f"\n❌ {total_tests - total_passed} API workflow behavior tests failed.")
            
        # Show created runs for inspection
        if self.created_runs:
            print(f"\n📋 Created runs for inspection:")
            for run_id in self.created_runs:
                print(f"  🆔 {run_id}")
                
    def run_all_tests(self):
        """Run all API workflow behavior tests."""
        print("🚀 Starting API workflow behavior validation...\n")
        
        self.test_api_connectivity()
        self.test_worktree_workflow_creation()
        self.test_custom_branch_workflow()
        self.test_temp_workspace_workflow()
        self.test_parameter_validation()
        self.test_workflow_status_tracking()
        self.test_workflow_differences()
        
        self.print_summary()


def main():
    """Run API workflow behavior validation."""
    tester = APIWorkflowTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()