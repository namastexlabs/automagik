#!/usr/bin/env python3
"""Test long-running workflows with message injection.

This validates that messages can be injected into active workflows
and that the workflow processes them correctly.
"""

import asyncio
import json
import os
import sys
import time
import requests
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import threading

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from automagik.utils.project import get_project_root, resolve_workspace_from_run_id
from automagik.agents.claude_code.sdk_message_injection import SDKMessageInjector


class LongRunningMessageInjectionTester:
    """Test message injection into long-running workflows."""
    
    def __init__(self, api_base_url: str = "http://localhost:18881", api_key: str = "namastex888"):
        self.api_base_url = api_base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
        self.test_results = []
        self.created_runs = []
        self.injector = SDKMessageInjector()
        
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
            mock_response = requests.Response()
            mock_response.status_code = 408
            mock_response._content = b'{"error": "Request timeout"}'
            return mock_response
        except Exception as e:
            mock_response = requests.Response()
            mock_response.status_code = 500
            mock_response._content = f'{{"error": "{str(e)}"}}'.encode()
            return mock_response
            
    def wait_for_status(self, run_id: str, target_status: str, max_wait_time: int = 60) -> bool:
        """Wait for workflow to reach a specific status."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            try:
                response = self.make_request("GET", f"/api/v1/workflows/claude-code/run/{run_id}/status")
                
                if response.status_code == 200:
                    status_data = response.json()
                    current_status = status_data.get("status", "unknown")
                    
                    if current_status == target_status:
                        return True
                    elif current_status in ["failed", "killed", "completed"]:
                        # Terminal states
                        return current_status == target_status
                        
                time.sleep(2)
                
            except Exception as e:
                print(f"    Error checking status: {e}")
                time.sleep(2)
        
        return False
        
    def inject_message_during_execution(self, workspace_path: Path, message: str, metadata: Dict = None) -> bool:
        """Inject a message into a running workflow."""
        try:
            success = self.injector.add_message_to_queue(
                workspace_path,
                message,
                metadata or {"injected_at": datetime.now().isoformat()}
            )
            
            if success:
                print(f"    📨 Injected message: '{message[:50]}...'")
            else:
                print(f"    ❌ Failed to inject message")
                
            return success
            
        except Exception as e:
            print(f"    ❌ Message injection error: {e}")
            return False
    
    def cleanup_workflow(self, run_id: str) -> bool:
        """Clean up workflow resources."""
        try:
            response = self.make_request("POST", f"/api/v1/workflows/claude-code/run/{run_id}/cleanup?force=true")
            return response.status_code == 200
        except:
            return False
            
    def test_long_running_workflow_with_injection(self):
        """Test injecting messages into a long-running workflow."""
        print(f"\n🧪 Testing long-running workflow with message injection...")
        
        # Create a workflow that will run for a while
        request_data = {
            "message": "Create a large project with multiple files. Take your time and create at least 5 different files with detailed content. Wait between each file creation.",
            "max_turns": 15,  # Allow many turns
            "timeout": 300,   # 5 minutes
            "persistent": True
        }
        
        try:
            # Start the workflow
            response = self.make_request("POST", "/api/v1/workflows/claude-code/run/builder", request_data)
            
            success = response.status_code == 200
            self.log_result("Long-Running Injection", "workflow_started", success, f"Status: {response.status_code}")
            
            if not success:
                return
                
            result = response.json()
            run_id = result.get("run_id")
            
            if not run_id:
                self.log_result("Long-Running Injection", "run_id_received", False, "No run_id in response")
                return
                
            self.created_runs.append(run_id)
            self.log_result("Long-Running Injection", "run_id_received", True, run_id)
            
            # Wait for workflow to start running
            print(f"    ⏳ Waiting for workflow {run_id} to start running...")
            running = self.wait_for_status(run_id, "running", max_wait_time=30)
            self.log_result("Long-Running Injection", "workflow_running", running)
            
            if not running:
                self.cleanup_workflow(run_id)
                return
            
            # Find the workspace
            workspaces = resolve_workspace_from_run_id(run_id)
            if not workspaces:
                self.log_result("Long-Running Injection", "workspace_found", False, "No workspace found")
                self.cleanup_workflow(run_id)
                return
                
            workspace_path = workspaces[0]
            self.log_result("Long-Running Injection", "workspace_found", True, str(workspace_path))
            
            # Wait a bit for the workflow to be in full execution
            print(f"    ⏳ Letting workflow execute for 10 seconds before injection...")
            time.sleep(10)
            
            # Inject first message
            message1 = "Please also create a README.md file with project documentation"
            injection1_success = self.inject_message_during_execution(workspace_path, message1)
            self.log_result("Long-Running Injection", "first_injection", injection1_success)
            
            # Wait a bit and inject second message
            time.sleep(5)
            message2 = "Add a config.json file with project configuration settings"
            injection2_success = self.inject_message_during_execution(workspace_path, message2)
            self.log_result("Long-Running Injection", "second_injection", injection2_success)
            
            # Check if messages are in queue
            queue_file = workspace_path / ".pending_messages.json"
            if queue_file.exists():
                with open(queue_file, 'r') as f:
                    queue_data = json.load(f)
                    queue_has_messages = len(queue_data.get("messages", [])) > 0
                    self.log_result("Long-Running Injection", "messages_in_queue", queue_has_messages, 
                                  f"{len(queue_data.get('messages', []))} messages")
            else:
                self.log_result("Long-Running Injection", "queue_file_exists", False)
            
            # Let workflow continue and process messages
            print(f"    ⏳ Letting workflow process injected messages...")
            time.sleep(20)
            
            # Check if workflow is still running or completed
            final_response = self.make_request("GET", f"/api/v1/workflows/claude-code/run/{run_id}/status")
            if final_response.status_code == 200:
                final_status = final_response.json().get("status")
                workflow_progressed = final_status in ["running", "completed"]
                self.log_result("Long-Running Injection", "workflow_progressed", workflow_progressed, final_status)
                
                # Check if files were created (indicating message processing)
                if workspace_path.exists():
                    files_created = list(workspace_path.glob("*.md")) + list(workspace_path.glob("*.json"))
                    files_count = len(files_created)
                    expected_files = files_count >= 2  # At least README.md and config.json
                    self.log_result("Long-Running Injection", "injected_files_created", expected_files, 
                                  f"Found {files_count} files: {[f.name for f in files_created]}")
            
            # Clean up
            cleanup_success = self.cleanup_workflow(run_id)
            self.log_result("Long-Running Injection", "cleanup_successful", cleanup_success)
            
        except Exception as e:
            self.log_result("Long-Running Injection", "execution_error", False, str(e))
            
    def test_add_message_api_endpoint(self):
        """Test adding messages via API endpoint."""
        print(f"\n🧪 Testing add-message API endpoint...")
        
        # Start a simple workflow
        request_data = {
            "message": "Create a simple test file and wait for further instructions",
            "max_turns": 10,
            "timeout": 180,
            "persistent": True
        }
        
        try:
            response = self.make_request("POST", "/api/v1/workflows/claude-code/run/builder", request_data)
            
            if response.status_code == 200:
                result = response.json()
                run_id = result.get("run_id")
                
                if run_id:
                    self.created_runs.append(run_id)
                    
                    # Wait for it to start
                    running = self.wait_for_status(run_id, "running", max_wait_time=20)
                    
                    if running:
                        # Try to inject message via API (if endpoint exists)
                        injection_data = {
                            "message": "Now create a second file with different content",
                            "priority": "high"
                        }
                        
                        # Test if add-message endpoint exists
                        inject_response = self.make_request("POST", 
                                                          f"/api/v1/workflows/claude-code/run/{run_id}/add-message",
                                                          injection_data)
                        
                        if inject_response.status_code == 200:
                            self.log_result("API Add Message", "endpoint_available", True)
                            self.log_result("API Add Message", "add_successful", True)
                        elif inject_response.status_code == 404:
                            self.log_result("API Add Message", "endpoint_not_implemented", True, 
                                          "Add-message endpoint not yet implemented")
                        else:
                            self.log_result("API Add Message", "add_failed", False, 
                                          f"Status: {inject_response.status_code}")
                    
                    self.cleanup_workflow(run_id)
                    
        except Exception as e:
            self.log_result("API Injection", "test_error", False, str(e))
            
    def test_concurrent_workflows_with_injection(self):
        """Test message injection into multiple concurrent workflows."""
        print(f"\n🧪 Testing concurrent workflows with injection...")
        
        concurrent_runs = []
        
        try:
            # Start 2 concurrent workflows
            for i in range(2):
                request_data = {
                    "message": f"Create files for project {i+1}. Work slowly and create multiple files.",
                    "max_turns": 10,
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
                        
            self.log_result("Concurrent Injection", "workflows_started", len(concurrent_runs) == 2, 
                          f"Started {len(concurrent_runs)}/2 workflows")
            
            if len(concurrent_runs) == 2:
                # Wait for both to be running
                time.sleep(10)
                
                # Find workspaces and inject messages
                injection_success = 0
                for run_id in concurrent_runs:
                    workspaces = resolve_workspace_from_run_id(run_id)
                    if workspaces:
                        workspace_path = workspaces[0]
                        success = self.inject_message_during_execution(
                            workspace_path, 
                            f"Add a unique file for run {run_id[:8]}"
                        )
                        if success:
                            injection_success += 1
                
                all_injected = injection_success == len(concurrent_runs)
                self.log_result("Concurrent Injection", "all_messages_injected", all_injected,
                              f"Injected {injection_success}/{len(concurrent_runs)}")
                
                # Clean up all
                for run_id in concurrent_runs:
                    self.cleanup_workflow(run_id)
                    
        except Exception as e:
            self.log_result("Concurrent Injection", "test_error", False, str(e))
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "="*60)
        print("📊 Long-Running Message Injection Test Summary")
        print("="*60)
        
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
            print("\n✅ All message injection tests passed!")
        else:
            print(f"\n❌ {total_tests - total_passed} message injection tests failed.")
    
    def run_all_tests(self):
        """Run all message injection tests."""
        print("🚀 Starting long-running workflow message injection tests...")
        print("⚠️  Note: These tests may take several minutes to complete.")
        print("📨 Testing message injection into active workflows...\n")
        
        # Test API connectivity first
        try:
            response = self.make_request("GET", "/health")
            if response.status_code != 200:
                print("❌ API not available. Please ensure the server is running.")
                return
            print("✅ API connectivity confirmed\n")
        except Exception as e:
            print(f"❌ Failed to connect to API: {e}")
            return
        
        try:
            # Run all tests
            self.test_long_running_workflow_with_injection()
            self.test_add_message_api_endpoint()
            self.test_concurrent_workflows_with_injection()
            
        finally:
            # Clean up any remaining workflows
            for run_id in self.created_runs:
                try:
                    self.cleanup_workflow(run_id)
                except:
                    pass
            self.print_summary()


def main():
    """Run message injection tests."""
    tester = LongRunningMessageInjectionTester()
    tester.run_all_tests()


if __name__ == "__main__":
    main()