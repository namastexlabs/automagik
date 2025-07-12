#!/usr/bin/env python3
"""End-to-end integration tests for Claude Code workflow system.

This module tests complete workflow execution with real API calls,
workspace creation, and automatic cleanup to prevent cluttering.
"""

import asyncio
import json
import os
import sys
import time
import tempfile
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import subprocess

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automagik.utils.project import get_project_root, resolve_workspace_from_run_id


class IntegrationTestRunner:
    """End-to-end integration test runner with automatic cleanup."""
    
    def __init__(self, api_base_url: str = "http://localhost:18881", api_key: str = "namastex888"):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        self.test_results = []
        self.created_runs = []  # Track created runs for cleanup
        self.cleanup_errors = []
        
    def log_result(self, category: str, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        status = "✅" if passed else "❌"
        print(f"  {status} {test_name}: {details}")
        self.test_results.append((category, test_name, passed, details))
        
    def make_request(self, method: str, endpoint: str, data: Dict = None, timeout: int = 30) -> requests.Response:
        """Make API request with timeout."""
        url = f"{self.api_base_url}{endpoint}"
        
        try:
            if method.upper() == "POST":
                response = requests.post(url, headers=self.headers, json=data, timeout=timeout)
            elif method.upper() == "GET":
                response = requests.get(url, headers=self.headers, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            return response
        except requests.exceptions.Timeout:
            # Create a mock response for timeout
            mock_response = requests.Response()
            mock_response.status_code = 408
            mock_response._content = b'{"error": "Request timeout"}'
            return mock_response
        except Exception as e:
            # Create a mock response for other errors
            mock_response = requests.Response()
            mock_response.status_code = 500
            mock_response._content = f'{{"error": "{str(e)}"}}'.encode()
            return mock_response
            
    def wait_for_completion(self, run_id: str, max_wait_time: int = 300) -> Dict[str, Any]:
        """Wait for workflow to complete or timeout."""
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.make_request("GET", f"/api/v1/workflows/claude-code/run/{run_id}/status")
                
                if response.status_code == 200:
                    status_data = response.json()
                    current_status = status_data.get("status", "unknown")
                    
                    if current_status != last_status:
                        print(f"    Status: {current_status}")
                        last_status = current_status
                    
                    if current_status in ["completed", "failed", "killed"]:
                        return status_data
                        
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                print(f"    Error checking status: {e}")
                time.sleep(5)
        
        # Timeout reached
        return {"status": "timeout", "error": "Max wait time exceeded"}
        
    def cleanup_workflow(self, run_id: str, force: bool = True) -> bool:
        """Clean up workflow workspace and resources."""
        try:
            print(f"    🧹 Cleaning up workspace for {run_id}")
            
            # Use the cleanup endpoint
            cleanup_url = f"/api/v1/workflows/claude-code/run/{run_id}/cleanup"
            if force:
                cleanup_url += "?force=true"
                
            response = self.make_request("POST", cleanup_url)
            
            if response.status_code == 200:
                cleanup_data = response.json()
                success = cleanup_data.get("success", False)
                
                if success:
                    print(f"    ✅ Cleanup successful for {run_id}")
                    return True
                else:
                    errors = cleanup_data.get("cleanup_details", {}).get("errors", [])
                    print(f"    ⚠️ Cleanup completed with errors: {errors}")
                    return False
            else:
                error_msg = f"Cleanup API call failed: {response.status_code}"
                print(f"    ❌ {error_msg}")
                self.cleanup_errors.append(f"{run_id}: {error_msg}")
                
                # Fallback: manual workspace cleanup
                return self._manual_cleanup(run_id)
                
        except Exception as e:
            error_msg = f"Cleanup failed: {str(e)}"
            print(f"    ❌ {error_msg}")
            self.cleanup_errors.append(f"{run_id}: {error_msg}")
            
            # Fallback: manual workspace cleanup
            return self._manual_cleanup(run_id)
            
    def _manual_cleanup(self, run_id: str) -> bool:
        """Manual workspace cleanup as fallback."""
        try:
            print(f"    🔧 Attempting manual cleanup for {run_id}")
            
            # Find workspace directories
            workspace_candidates = resolve_workspace_from_run_id(run_id)
            
            cleanup_success = True
            for workspace_path in workspace_candidates:
                try:
                    if workspace_path.exists():
                        # Check if it's a git worktree
                        project_root = get_project_root()
                        if (workspace_path.parent.name == "worktrees" and 
                            (workspace_path / ".git").exists()):
                            
                            # Try git worktree remove
                            try:
                                subprocess.run([
                                    "git", "worktree", "remove", "--force", str(workspace_path)
                                ], cwd=str(project_root), check=True, capture_output=True)
                                print(f"    ✅ Removed git worktree: {workspace_path}")
                            except subprocess.CalledProcessError:
                                # Fallback to directory removal
                                import shutil
                                shutil.rmtree(workspace_path)
                                print(f"    ✅ Removed directory: {workspace_path}")
                        else:
                            # Regular directory removal
                            import shutil
                            shutil.rmtree(workspace_path)
                            print(f"    ✅ Removed directory: {workspace_path}")
                            
                except Exception as e:
                    print(f"    ❌ Failed to remove {workspace_path}: {e}")
                    cleanup_success = False
                    
            return cleanup_success
            
        except Exception as e:
            print(f"    ❌ Manual cleanup failed: {e}")
            return False
    
    def test_simple_workflow_execution(self):
        """Test simple workflow execution with automatic cleanup."""
        print(f"\n🧪 Testing simple workflow execution...")
        
        request_data = {
            "message": "Create a simple hello.py file that prints 'Hello from integration test!'",
            "max_turns": 5,
            "timeout": 180,  # 3 minutes
            "persistent": True
        }
        
        try:
            # Start workflow
            response = self.make_request("POST", "/api/v1/workflows/claude-code/run/builder", request_data)
            
            success = response.status_code == 200
            self.log_result("Simple Workflow", "workflow_started", success, f"Status: {response.status_code}")
            
            if not success:
                return
                
            result = response.json()
            run_id = result.get("run_id")
            
            if not run_id:
                self.log_result("Simple Workflow", "run_id_received", False, "No run_id in response")
                return
                
            self.created_runs.append(run_id)
            self.log_result("Simple Workflow", "run_id_received", True, run_id)
            
            # Wait for completion
            print(f"    ⏳ Waiting for workflow {run_id} to complete...")
            final_status = self.wait_for_completion(run_id, max_wait_time=180)
            
            completed = final_status.get("status") == "completed"
            self.log_result("Simple Workflow", "workflow_completed", completed, 
                          f"Final status: {final_status.get('status')}")
            
            if completed:
                # Check if workspace was created
                workspaces = resolve_workspace_from_run_id(run_id)
                workspace_created = len(workspaces) > 0
                self.log_result("Simple Workflow", "workspace_created", workspace_created,
                              f"Found {len(workspaces)} workspaces")
                
                # Check if hello.py was created
                if workspace_created:
                    for workspace in workspaces:
                        hello_file = workspace / "hello.py"
                        if hello_file.exists():
                            self.log_result("Simple Workflow", "file_created", True, str(hello_file))
                            break
                    else:
                        self.log_result("Simple Workflow", "file_created", False, "hello.py not found")
            
            # Clean up workspace
            cleanup_success = self.cleanup_workflow(run_id, force=True)
            self.log_result("Simple Workflow", "cleanup_successful", cleanup_success)
            
        except Exception as e:
            self.log_result("Simple Workflow", "execution_error", False, str(e))
            
    def test_custom_branch_workflow(self):
        """Test workflow with custom branch creation."""
        print(f"\n🧪 Testing custom branch workflow...")
        
        custom_branch = f"integration-test-{int(datetime.now().timestamp())}"
        
        request_data = {
            "message": "Create a test file for custom branch integration test",
            "git_branch": custom_branch,
            "max_turns": 5,
            "timeout": 180,
            "persistent": True
        }
        
        try:
            response = self.make_request("POST", "/api/v1/workflows/claude-code/run/surgeon", request_data)
            
            success = response.status_code == 200
            self.log_result("Custom Branch", "workflow_started", success, f"Status: {response.status_code}")
            
            if not success:
                return
                
            result = response.json()
            run_id = result.get("run_id")
            
            if run_id:
                self.created_runs.append(run_id)
                self.log_result("Custom Branch", "run_id_received", True, run_id)
                
                # Wait for completion
                print(f"    ⏳ Waiting for workflow {run_id} to complete...")
                final_status = self.wait_for_completion(run_id, max_wait_time=180)
                
                completed = final_status.get("status") == "completed"
                self.log_result("Custom Branch", "workflow_completed", completed,
                              f"Final status: {final_status.get('status')}")
                
                if completed:
                    # Check if custom branch workspace exists
                    workspaces = resolve_workspace_from_run_id(run_id)
                    branch_workspace_found = False
                    
                    for workspace in workspaces:
                        if custom_branch.replace("/", "-") in workspace.name:
                            branch_workspace_found = True
                            break
                            
                    self.log_result("Custom Branch", "custom_branch_workspace", branch_workspace_found)
                
                # Clean up
                cleanup_success = self.cleanup_workflow(run_id, force=True)
                self.log_result("Custom Branch", "cleanup_successful", cleanup_success)
            else:
                self.log_result("Custom Branch", "run_id_received", False, "No run_id in response")
                
        except Exception as e:
            self.log_result("Custom Branch", "execution_error", False, str(e))
            
    def test_workflow_kill_and_cleanup(self):
        """Test killing a workflow and cleaning up resources."""
        print(f"\n🧪 Testing workflow kill and cleanup...")
        
        request_data = {
            "message": "Create multiple files and run a long task that we will kill",
            "max_turns": 20,  # High turn count so it doesn't complete quickly
            "timeout": 600,   # 10 minutes
            "persistent": True
        }
        
        try:
            response = self.make_request("POST", "/api/v1/workflows/claude-code/run/builder", request_data)
            
            success = response.status_code == 200
            self.log_result("Kill Test", "workflow_started", success, f"Status: {response.status_code}")
            
            if not success:
                return
                
            result = response.json()
            run_id = result.get("run_id")
            
            if not run_id:
                self.log_result("Kill Test", "run_id_received", False, "No run_id in response")
                return
                
            self.created_runs.append(run_id)
            self.log_result("Kill Test", "run_id_received", True, run_id)
            
            # Wait a bit for workflow to start
            print(f"    ⏳ Waiting for workflow {run_id} to start...")
            time.sleep(10)
            
            # Kill the workflow
            print(f"    🛑 Killing workflow {run_id}")
            kill_response = self.make_request("POST", f"/api/v1/workflows/claude-code/run/{run_id}/kill")
            
            kill_success = kill_response.status_code == 200
            self.log_result("Kill Test", "workflow_killed", kill_success,
                          f"Kill status: {kill_response.status_code}")
            
            if kill_success:
                # Wait a moment for kill to complete
                time.sleep(5)
                
                # Check final status
                status_response = self.make_request("GET", f"/api/v1/workflows/claude-code/run/{run_id}/status")
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    final_status = status_data.get("status")
                    is_killed = final_status == "killed"
                    self.log_result("Kill Test", "status_is_killed", is_killed,
                                  f"Final status: {final_status}")
            
            # Clean up workspace
            cleanup_success = self.cleanup_workflow(run_id, force=True)
            self.log_result("Kill Test", "cleanup_successful", cleanup_success)
            
        except Exception as e:
            self.log_result("Kill Test", "execution_error", False, str(e))
            
    def test_concurrent_workflows(self):
        """Test multiple concurrent workflows."""
        print(f"\n🧪 Testing concurrent workflow execution...")
        
        concurrent_runs = []
        
        try:
            # Start 3 concurrent workflows
            for i in range(3):
                request_data = {
                    "message": f"Create a test file number {i+1} for concurrent execution test",
                    "max_turns": 5,
                    "timeout": 180,
                    "persistent": True
                }
                
                response = self.make_request("POST", "/api/v1/workflows/claude-code/run/builder", request_data)
                
                if response.status_code == 200:
                    result = response.json()
                    run_id = result.get("run_id")
                    if run_id:
                        concurrent_runs.append(run_id)
                        self.created_runs.append(run_id)
                        
            workflows_started = len(concurrent_runs)
            self.log_result("Concurrent", "workflows_started", workflows_started == 3,
                          f"Started {workflows_started}/3 workflows")
            
            if workflows_started > 0:
                # Wait for all to complete
                print(f"    ⏳ Waiting for {workflows_started} concurrent workflows to complete...")
                
                completed_count = 0
                for run_id in concurrent_runs:
                    final_status = self.wait_for_completion(run_id, max_wait_time=180)
                    if final_status.get("status") == "completed":
                        completed_count += 1
                        
                all_completed = completed_count == workflows_started
                self.log_result("Concurrent", "all_completed", all_completed,
                              f"Completed {completed_count}/{workflows_started}")
                
                # Check unique workspaces
                all_workspaces = []
                for run_id in concurrent_runs:
                    workspaces = resolve_workspace_from_run_id(run_id)
                    all_workspaces.extend(workspaces)
                    
                unique_workspaces = len(set(str(w) for w in all_workspaces))
                workspaces_unique = unique_workspaces == len(all_workspaces)
                self.log_result("Concurrent", "workspaces_unique", workspaces_unique,
                              f"Found {unique_workspaces} unique workspaces")
                
                # Clean up all workspaces
                cleanup_count = 0
                for run_id in concurrent_runs:
                    if self.cleanup_workflow(run_id, force=True):
                        cleanup_count += 1
                        
                all_cleaned = cleanup_count == workflows_started
                self.log_result("Concurrent", "all_cleaned_up", all_cleaned,
                              f"Cleaned {cleanup_count}/{workflows_started}")
                              
        except Exception as e:
            self.log_result("Concurrent", "execution_error", False, str(e))
            
    def cleanup_remaining_workspaces(self):
        """Clean up any remaining test workspaces."""
        print(f"\n🧹 Final cleanup of remaining test workspaces...")
        
        cleanup_count = 0
        for run_id in self.created_runs:
            try:
                if self.cleanup_workflow(run_id, force=True):
                    cleanup_count += 1
            except Exception as e:
                print(f"    ❌ Failed to cleanup {run_id}: {e}")
                
        print(f"    ✅ Final cleanup completed: {cleanup_count}/{len(self.created_runs)} workspaces")
        
        if self.cleanup_errors:
            print(f"    ⚠️ Cleanup errors encountered:")
            for error in self.cleanup_errors:
                print(f"      - {error}")
    
    def print_summary(self):
        """Print comprehensive test summary."""
        print("\n" + "="*60)
        print("📊 Integration Test Summary")
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
            print("\n✅ All integration tests passed!")
        else:
            print(f"\n❌ {total_tests - total_passed} integration tests failed.")
            
        # Show summary of created runs
        if self.created_runs:
            print(f"\n📋 Tested {len(self.created_runs)} workflow runs:")
            for run_id in self.created_runs:
                print(f"  🆔 {run_id}")
                
    def run_all_tests(self):
        """Run all integration tests."""
        print("🚀 Starting end-to-end integration tests...\n")
        print("⚠️  Note: These tests create real workspaces and execute actual workflows.")
        print("🧹 Automatic cleanup is enabled to prevent workspace clutter.\n")
        
        # Run test API connectivity first
        try:
            response = self.make_request("GET", "/health")
            api_available = response.status_code == 200
            
            if not api_available:
                print("❌ API not available. Please ensure the server is running on http://localhost:18881")
                return
                
            print("✅ API connectivity confirmed\n")
            
        except Exception as e:
            print(f"❌ Failed to connect to API: {e}")
            return
        
        try:
            # Run all integration tests
            self.test_simple_workflow_execution()
            self.test_custom_branch_workflow()
            self.test_workflow_kill_and_cleanup()
            self.test_concurrent_workflows()
            
        finally:
            # Always run final cleanup
            self.cleanup_remaining_workspaces()
            self.print_summary()


def main():
    """Run integration tests."""
    runner = IntegrationTestRunner()
    runner.run_all_tests()


if __name__ == "__main__":
    main()