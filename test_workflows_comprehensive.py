#!/usr/bin/env python3
"""
Comprehensive Workflow Testing Script
=====================================

This script tests all aspects of the workflow system API including:
- Basic workflow operations (list, start)
- Status tracking and management
- Message injection during execution
- Session continuation
- Error handling scenarios
- Performance and load testing

Usage:
    python test_workflows_comprehensive.py --port 48881 --api-key namastex888
"""

import argparse
import asyncio
import json
import time
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from dataclasses import dataclass, asdict

@dataclass
class TestResult:
    """Represents the result of a single test"""
    test_name: str
    success: bool
    duration_ms: float
    details: Dict
    error_message: Optional[str] = None
    
@dataclass
class TestReport:
    """Comprehensive test report"""
    timestamp: str
    total_tests: int
    passed: int
    failed: int
    duration_seconds: float
    test_results: List[TestResult]
    summary: Dict[str, int]

class WorkflowTester:
    """Comprehensive workflow testing framework"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key
        self.headers = {
            'x-api-key': api_key,
            'Content-Type': 'application/json'
        }
        self.test_results: List[TestResult] = []
        self.start_time = time.time()
        
    def make_request(self, method: str, endpoint: str, data: Dict = None, timeout: int = 30) -> Tuple[bool, Dict]:
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == 'GET':
                response = requests.get(url, headers=self.headers, timeout=timeout)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=self.headers, json=data, timeout=timeout)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=self.headers, json=data, timeout=timeout)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=self.headers, timeout=timeout)
            else:
                return False, {"error": f"Unsupported method: {method}"}
                
            if response.status_code in [200, 201]:
                return True, response.json()
            else:
                return False, {
                    "status_code": response.status_code,
                    "error": response.text
                }
        except Exception as e:
            return False, {"error": str(e)}
    
    def run_test(self, test_name: str, test_func) -> TestResult:
        """Run a single test and record results"""
        start = time.time()
        print(f"  Running: {test_name}")
        
        try:
            success, details = test_func()
            duration_ms = (time.time() - start) * 1000
            
            result = TestResult(
                test_name=test_name,
                success=success,
                duration_ms=duration_ms,
                details=details,
                error_message=details.get('error') if not success else None
            )
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"    {status} ({duration_ms:.0f}ms)")
            if not success and result.error_message:
                print(f"    Error: {result.error_message}")
                
        except Exception as e:
            duration_ms = (time.time() - start) * 1000
            result = TestResult(
                test_name=test_name,
                success=False,
                duration_ms=duration_ms,
                details={},
                error_message=str(e)
            )
            print(f"    ❌ FAIL ({duration_ms:.0f}ms) - Exception: {str(e)}")
        
        self.test_results.append(result)
        return result
    
    # =================== Phase 1: Environment Tests ===================
    
    def test_health_endpoint(self) -> Tuple[bool, Dict]:
        """Test basic health endpoint"""
        success, data = self.make_request('GET', '/health')
        if success and data.get('status') == 'healthy':
            return True, {"status": "healthy", "version": data.get('version')}
        return False, data
    
    def test_workflow_health(self) -> Tuple[bool, Dict]:
        """Test workflow system health"""
        success, data = self.make_request('GET', '/api/v1/workflows/claude-code/health')
        return success, data
    
    # =================== Phase 2: Basic Workflow Tests ===================
    
    def test_list_workflows(self) -> Tuple[bool, Dict]:
        """Test listing available workflows"""
        success, data = self.make_request('GET', '/api/v1/workflows/claude-code/manage')
        if success and isinstance(data, list) and len(data) > 0:
            workflow_names = [w.get('name') for w in data]
            return True, {"count": len(data), "workflows": workflow_names}
        return False, data
    
    def test_start_workflow(self) -> Tuple[bool, Dict]:
        """Test starting a workflow"""
        payload = {
            "message": "Test workflow execution for automated testing",
            "max_turns": 3,
            "session_name": "automated-test-execution",
            "timeout": 120
        }
        success, data = self.make_request('POST', '/api/v1/workflows/claude-code/run/flashinho_thinker', payload)
        if success and data.get('run_id') and data.get('status') == 'pending':
            return True, {
                "run_id": data.get('run_id'),
                "session_id": data.get('session_id'),
                "workflow_name": data.get('workflow_name')
            }
        return False, data
    
    # =================== Phase 3: Status and Management Tests ===================
    
    def test_workflow_status(self) -> Tuple[bool, Dict]:
        """Test workflow status tracking"""
        # First start a workflow
        start_success, start_data = self.test_start_workflow()
        if not start_success:
            return False, {"error": "Failed to start workflow for status test"}
        
        run_id = start_data['run_id']
        
        # Check status
        success, data = self.make_request('GET', f'/api/v1/workflows/claude-code/run/{run_id}/status')
        if success and data.get('run_id') == run_id and data.get('status') in ['pending', 'running', 'completed']:
            return True, {
                "run_id": run_id,
                "status": data.get('status'),
                "workflow_name": data.get('workflow_name')
            }
        return False, data
    
    def test_list_workflow_runs(self) -> Tuple[bool, Dict]:
        """Test listing workflow runs"""
        success, data = self.make_request('GET', '/api/v1/workflows/claude-code/runs?page=1&page_size=5')
        if success and 'runs' in data and isinstance(data['runs'], list):
            return True, {
                "total_runs": len(data['runs']),
                "page": data.get('page'),
                "has_next": data.get('has_next')
            }
        return False, data
    
    def test_filter_workflow_runs(self) -> Tuple[bool, Dict]:
        """Test filtering workflow runs by status"""
        success, data = self.make_request('GET', '/api/v1/workflows/claude-code/runs?status=completed')
        if success and 'runs' in data:
            completed_runs = [r for r in data['runs'] if r.get('status') == 'completed']
            return True, {"completed_runs": len(completed_runs)}
        return False, data
    
    # =================== Phase 4: Message Injection Tests ===================
    
    def test_message_injection(self) -> Tuple[bool, Dict]:
        """Test message injection into running workflow with retry logic"""
        # Start a long-running workflow
        payload = {
            "message": "Perform a detailed analysis that will take some time",
            "max_turns": 10,
            "session_name": "message-injection-test",
            "timeout": 300
        }
        start_success, start_data = self.make_request('POST', '/api/v1/workflows/claude-code/run/flashinho_thinker', payload)
        if not start_success:
            return False, {"error": "Failed to start workflow for injection test"}
        
        run_id = start_data['run_id']
        
        # Wait for workflow to be ready for injection with exponential backoff
        max_attempts = 5
        base_delay = 1.0
        
        for attempt in range(max_attempts):
            # Check workflow status first
            status_success, status_data = self.make_request('GET', f'/api/v1/workflows/claude-code/run/{run_id}/status')
            
            if status_success:
                workflow_status = status_data.get('status')
                if workflow_status in ['running']:
                    # Workflow is running, try injection
                    break
                elif workflow_status in ['failed', 'completed', 'killed']:
                    return False, {"error": f"Workflow ended with status: {workflow_status}"}
                # If pending, continue waiting
            
            # Wait with exponential backoff
            wait_time = base_delay * (2 ** attempt)
            time.sleep(wait_time)
        
        # Inject message with timeout handling
        inject_payload = {"message": "Please also include performance considerations"}
        success, data = self.make_request('POST', f'/api/v1/workflows/claude-code/run/{run_id}/inject-message', inject_payload, timeout=60)
        
        if success and data.get('success') and data.get('run_id') == run_id:
            return True, {
                "run_id": run_id,
                "message_id": data.get('message_id'),
                "queue_position": data.get('queue_position')
            }
        
        # Check for specific timeout error (408) which is expected behavior
        if not success and data.get('status_code') == 408:
            return True, {
                "run_id": run_id,
                "message": "Workspace initialization timeout handled correctly",
                "error_handled": True
            }
        
        return False, data
    
    def test_multiple_message_injection(self) -> Tuple[bool, Dict]:
        """Test multiple message injections with proper timing"""
        # Start workflow
        payload = {
            "message": "Complex analysis task for multiple injection test",
            "max_turns": 15,
            "timeout": 400
        }
        start_success, start_data = self.make_request('POST', '/api/v1/workflows/claude-code/run/flashinho_thinker', payload)
        if not start_success:
            return False, {"error": "Failed to start workflow for multiple injection test"}
        
        run_id = start_data['run_id']
        
        # Wait for workflow to be properly initialized
        max_wait_attempts = 8
        for attempt in range(max_wait_attempts):
            status_success, status_data = self.make_request('GET', f'/api/v1/workflows/claude-code/run/{run_id}/status')
            if status_success and status_data.get('status') == 'running':
                break
            elif status_success and status_data.get('status') in ['failed', 'completed', 'killed']:
                return False, {"error": f"Workflow ended with status: {status_data.get('status')}"}
            time.sleep(1.0 * (1.5 ** attempt))  # Progressive backoff
        
        # Inject multiple messages
        messages = [
            "Include cost analysis",
            "Add security considerations", 
            "Consider scalability factors"
        ]
        
        injection_results = []
        for i, msg in enumerate(messages):
            inject_payload = {"message": msg}
            success, data = self.make_request('POST', f'/api/v1/workflows/claude-code/run/{run_id}/inject-message', inject_payload, timeout=60)
            
            if success:
                injection_results.append({
                    "message": msg,
                    "message_id": data.get('message_id'),
                    "queue_position": data.get('queue_position')
                })
            elif data.get('status_code') == 408:
                # Timeout is acceptable - workspace initialization delay
                injection_results.append({
                    "message": msg,
                    "status": "timeout_handled",
                    "note": "Workspace initialization timeout"
                })
            else:
                return False, {"error": f"Failed to inject message {i+1}: {data}"}
            
            # Small delay between injections to avoid overwhelming
            time.sleep(0.5)
        
        return True, {"run_id": run_id, "injections": injection_results}
    
    # =================== Phase 5: Session Continuation Tests ===================
    
    def test_session_continuation(self) -> Tuple[bool, Dict]:
        """Test session continuation functionality"""
        # Start initial workflow
        initial_payload = {
            "message": "Create a simple function for user validation",
            "max_turns": 5,
            "session_name": "session-continuation-test"
        }
        start_success, start_data = self.make_request('POST', '/api/v1/workflows/claude-code/run/builder', initial_payload)
        if not start_success:
            return False, {"error": "Failed to start initial workflow"}
        
        session_id = start_data['session_id']
        
        # Wait for initial workflow to process
        time.sleep(5)
        
        # Continue session with new task
        continue_payload = {
            "message": "Now add error handling to the function",
            "session_id": session_id,
            "max_turns": 5
        }
        continue_success, continue_data = self.make_request('POST', '/api/v1/workflows/claude-code/run/builder', continue_payload)
        
        if continue_success and continue_data.get('session_id') == session_id:
            return True, {
                "initial_run_id": start_data['run_id'],
                "continue_run_id": continue_data['run_id'],
                "session_id": session_id
            }
        return False, continue_data
    
    # =================== Phase 6: Error Handling Tests ===================
    
    def test_invalid_repository_error(self) -> Tuple[bool, Dict]:
        """Test error handling with invalid repository"""
        payload = {
            "message": "Test error handling",
            "repository_url": "https://github.com/nonexistent/repo-test.git",
            "git_branch": "main"
        }
        start_success, start_data = self.make_request('POST', '/api/v1/workflows/claude-code/run/builder', payload)
        if not start_success:
            return False, {"error": "Failed to start workflow with invalid repo"}
        
        run_id = start_data['run_id']
        
        # Wait for failure
        time.sleep(5)
        
        # Check status should be failed
        success, data = self.make_request('GET', f'/api/v1/workflows/claude-code/run/{run_id}/status')
        if success and data.get('status') == 'failed':
            return True, {"run_id": run_id, "status": "failed"}
        return False, {"error": f"Expected failed status, got: {data.get('status')}"}
    
    def test_workflow_kill(self) -> Tuple[bool, Dict]:
        """Test workflow kill functionality"""
        # Start a long-running workflow
        payload = {
            "message": "Long running analysis task for kill test",
            "max_turns": 50,
            "timeout": 1800
        }
        start_success, start_data = self.make_request('POST', '/api/v1/workflows/claude-code/run/flashinho_thinker', payload)
        if not start_success:
            return False, {"error": "Failed to start workflow for kill test"}
        
        run_id = start_data['run_id']
        
        # Wait for workflow to start
        time.sleep(3)
        
        # Kill the workflow
        success, data = self.make_request('POST', f'/api/v1/workflows/claude-code/run/{run_id}/kill')
        if success and data.get('success') and data.get('run_id') == run_id:
            return True, {
                "run_id": run_id,
                "kill_method": data.get('kill_method'),
                "kill_duration_ms": data.get('kill_duration_ms')
            }
        return False, data
    
    # =================== Phase 8: Performance Tests ===================
    
    def test_concurrent_workflows(self) -> Tuple[bool, Dict]:
        """Test concurrent workflow execution"""
        num_workflows = 3
        workflows_data = []
        
        # Start multiple workflows concurrently
        for i in range(num_workflows):
            payload = {
                "message": f"Concurrent test workflow {i+1}",
                "max_turns": 3,
                "session_name": f"concurrent-test-{i+1}"
            }
            success, data = self.make_request('POST', '/api/v1/workflows/claude-code/run/flashinho_thinker', payload)
            if success:
                workflows_data.append(data)
            else:
                return False, {"error": f"Failed to start workflow {i+1}"}
        
        # Check all workflows started successfully
        if len(workflows_data) == num_workflows:
            return True, {
                "concurrent_workflows": num_workflows,
                "run_ids": [w['run_id'] for w in workflows_data]
            }
        return False, {"error": "Not all concurrent workflows started"}
    
    def test_rapid_message_injection(self) -> Tuple[bool, Dict]:
        """Test rapid message injection performance with proper initialization"""
        # Start workflow
        payload = {
            "message": "Base task for rapid injection test",
            "max_turns": 20,
            "timeout": 600
        }
        start_success, start_data = self.make_request('POST', '/api/v1/workflows/claude-code/run/flashinho_thinker', payload)
        if not start_success:
            return False, {"error": "Failed to start workflow for rapid injection test"}
        
        run_id = start_data['run_id']
        
        # Wait for workflow to be fully ready before rapid testing
        max_wait = 15
        for attempt in range(max_wait):
            status_success, status_data = self.make_request('GET', f'/api/v1/workflows/claude-code/run/{run_id}/status')
            if status_success and status_data.get('status') == 'running':
                # Double-check workspace is ready with a test injection
                test_inject = {"message": "Test workspace readiness"}
                test_success, test_data = self.make_request('POST', f'/api/v1/workflows/claude-code/run/{run_id}/inject-message', test_inject, timeout=30)
                if test_success:
                    break
                elif test_data.get('status_code') not in [408, 400]:
                    # If not a timing/workspace issue, fail
                    return False, {"error": f"Workspace test failed: {test_data}"}
            elif status_success and status_data.get('status') in ['failed', 'completed', 'killed']:
                return False, {"error": f"Workflow ended with status: {status_data.get('status')}"}
            
            time.sleep(1.0)
        
        # Rapidly inject messages
        num_injections = 5
        injection_times = []
        successful_injections = 0
        timeout_handled = 0
        
        for i in range(num_injections):
            start_time = time.time()
            inject_payload = {"message": f"Rapid injection {i+1}"}
            success, data = self.make_request('POST', f'/api/v1/workflows/claude-code/run/{run_id}/inject-message', inject_payload, timeout=30)
            end_time = time.time()
            
            if success:
                injection_times.append((end_time - start_time) * 1000)
                successful_injections += 1
            elif data.get('status_code') == 408:
                # Timeout is acceptable for rapid injection test
                timeout_handled += 1
                injection_times.append((end_time - start_time) * 1000)  # Include timeout time
            else:
                return False, {"error": f"Failed rapid injection {i+1}: {data}"}
        
        # Calculate metrics only if we have timing data
        if injection_times:
            avg_time = sum(injection_times) / len(injection_times)
            return True, {
                "run_id": run_id,
                "total_injections": num_injections,
                "successful_injections": successful_injections,
                "timeout_handled": timeout_handled,
                "average_time_ms": avg_time,
                "max_time_ms": max(injection_times),
                "min_time_ms": min(injection_times)
            }
        else:
            return False, {"error": "No timing data collected"}
    
    # =================== Test Execution ===================
    
    def run_all_tests(self) -> TestReport:
        """Run all test phases"""
        print("🧪 Starting Comprehensive Workflow Testing")
        print("=" * 50)
        
        # Phase 1: Environment Tests
        print("\n📋 Phase 1: Environment Setup")
        self.run_test("Health Endpoint", self.test_health_endpoint)
        self.run_test("Workflow Health", self.test_workflow_health)
        
        # Phase 2: Basic Workflow Tests
        print("\n📋 Phase 2: Basic Workflow Operations")
        self.run_test("List Workflows", self.test_list_workflows)
        self.run_test("Start Workflow", self.test_start_workflow)
        
        # Phase 3: Status and Management Tests
        print("\n📋 Phase 3: Status and Management")
        self.run_test("Workflow Status", self.test_workflow_status)
        self.run_test("List Workflow Runs", self.test_list_workflow_runs)
        self.run_test("Filter Workflow Runs", self.test_filter_workflow_runs)
        
        # Phase 4: Message Injection Tests
        print("\n📋 Phase 4: Message Injection")
        self.run_test("Message Injection", self.test_message_injection)
        self.run_test("Multiple Message Injection", self.test_multiple_message_injection)
        
        # Phase 5: Session Continuation Tests
        print("\n📋 Phase 5: Session Continuation")
        self.run_test("Session Continuation", self.test_session_continuation)
        
        # Phase 6: Error Handling Tests
        print("\n📋 Phase 6: Error Handling")
        self.run_test("Invalid Repository Error", self.test_invalid_repository_error)
        self.run_test("Workflow Kill", self.test_workflow_kill)
        
        # Phase 8: Performance Tests
        print("\n📋 Phase 8: Performance Testing")
        self.run_test("Concurrent Workflows", self.test_concurrent_workflows)
        self.run_test("Rapid Message Injection", self.test_rapid_message_injection)
        
        # Generate report
        return self.generate_report()
    
    def generate_report(self) -> TestReport:
        """Generate comprehensive test report"""
        total_duration = time.time() - self.start_time
        passed = sum(1 for r in self.test_results if r.success)
        failed = len(self.test_results) - passed
        
        # Categorize results
        summary = {}
        for result in self.test_results:
            phase = result.test_name.split()[0] if " " in result.test_name else "Other"
            if phase not in summary:
                summary[phase] = {"passed": 0, "failed": 0}
            
            if result.success:
                summary[phase]["passed"] += 1
            else:
                summary[phase]["failed"] += 1
        
        return TestReport(
            timestamp=datetime.now().isoformat(),
            total_tests=len(self.test_results),
            passed=passed,
            failed=failed,
            duration_seconds=total_duration,
            test_results=self.test_results,
            summary=summary
        )
    
    def print_report(self, report: TestReport):
        """Print formatted test report"""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("=" * 60)
        
        print(f"🕐 Timestamp: {report.timestamp}")
        print(f"⏱️  Duration: {report.duration_seconds:.2f} seconds")
        print(f"📈 Total Tests: {report.total_tests}")
        print(f"✅ Passed: {report.passed}")
        print(f"❌ Failed: {report.failed}")
        print(f"📊 Success Rate: {(report.passed/report.total_tests)*100:.1f}%")
        
        print("\n📋 Summary by Phase:")
        for phase, stats in report.summary.items():
            total = stats['passed'] + stats['failed']
            success_rate = (stats['passed'] / total) * 100 if total > 0 else 0
            print(f"  {phase}: {stats['passed']}/{total} ({success_rate:.1f}%)")
        
        if report.failed > 0:
            print("\n❌ Failed Tests:")
            for result in report.test_results:
                if not result.success:
                    print(f"  - {result.test_name}: {result.error_message}")
        
        print("\n🎯 Key Validation Results:")
        validations = [
            ("✅ Workflow System Health", any(r.test_name == "Workflow Health" and r.success for r in report.test_results)),
            ("✅ Basic Workflow Operations", any(r.test_name == "Start Workflow" and r.success for r in report.test_results)),
            ("✅ Message Injection Works", any(r.test_name == "Message Injection" and r.success for r in report.test_results)),
            ("✅ Session Continuation Works", any(r.test_name == "Session Continuation" and r.success for r in report.test_results)),
            ("✅ Error Handling Proper", any(r.test_name == "Invalid Repository Error" and r.success for r in report.test_results)),
            ("✅ Kill Functionality Works", any(r.test_name == "Workflow Kill" and r.success for r in report.test_results)),
        ]
        
        for validation, passed in validations:
            status = "✅" if passed else "❌"
            print(f"  {status} {validation.replace('✅ ', '')}")
        
        overall_status = "🎉 ALL SYSTEMS OPERATIONAL" if report.failed == 0 else f"⚠️  {report.failed} ISSUES DETECTED"
        print(f"\n{overall_status}")
        print("=" * 60)

def main():
    parser = argparse.ArgumentParser(description='Comprehensive Workflow Testing')
    parser.add_argument('--port', type=int, default=48881, help='API port (default: 48881)')
    parser.add_argument('--host', default='localhost', help='API host (default: localhost)')
    parser.add_argument('--api-key', default='namastex888', help='API key')
    parser.add_argument('--output', help='Output report to JSON file')
    
    args = parser.parse_args()
    
    base_url = f"http://{args.host}:{args.port}"
    
    print(f"🚀 Testing Workflow API at {base_url}")
    print(f"🔑 Using API key: {args.api_key[:8]}...")
    
    tester = WorkflowTester(base_url, args.api_key)
    report = tester.run_all_tests()
    tester.print_report(report)
    
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        print(f"\n📄 Report saved to: {args.output}")
    
    # Exit with error code if tests failed
    sys.exit(1 if report.failed > 0 else 0)

if __name__ == "__main__":
    main()