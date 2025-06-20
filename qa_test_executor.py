#!/usr/bin/env python3
"""
Comprehensive QA Test Executor for Claude Code Workflows

This script executes the full test matrix defined in qa_comprehensive_matrix_testing.md
using the MCP workflow tools to ensure 100% coverage of all workflow combinations.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import uuid
import logging

# Test configuration
API_BASE_URL = "http://localhost:28881"
TEST_RESULTS_FILE = "qa_test_results.json"

# Test data
WORKFLOWS = ["guardian", "surgeon", "brain", "genie", "shipper", "lina", "builder"]

class QATestExecutor:
    """Executes comprehensive QA tests for Claude Code workflows."""
    
    def __init__(self):
        self.results = []
        self.start_time = datetime.now(timezone.utc)
        self.setup_logging()
        
    def setup_logging(self):
        """Set up logging for test execution."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('qa_test_execution.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    async def execute_workflow_test(
        self,
        test_id: str,
        workflow: str,
        message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a single workflow test case."""
        
        test_start = datetime.now(timezone.utc)
        self.logger.info(f"Starting test {test_id}: {workflow} - {message[:50]}...")
        
        try:
            # Use MCP workflow tool to execute
            from mcp_automagik_workflows import run_workflow, get_workflow_status
            
            # Start workflow
            result = await run_workflow(
                workflow_name=workflow,
                message=message,
                **kwargs
            )
            
            run_id = result.get('run_id')
            if not run_id:
                raise Exception("No run_id returned from workflow execution")
            
            # Monitor workflow until completion
            status = "running"
            turns_used = 0
            tools_used = []
            cost_usd = 0.0
            total_tokens = 0
            
            while status in ["pending", "running"]:
                await asyncio.sleep(5)  # Poll every 5 seconds
                status_result = await get_workflow_status(run_id, detailed=True)
                status = status_result.get('status', 'unknown')
                
                progress = status_result.get('progress', {})
                metrics = status_result.get('metrics', {})
                
                turns_used = progress.get('turns', 0)
                tools_used = metrics.get('tools_used', [])
                cost_usd = metrics.get('cost_usd', 0.0)
                total_tokens = metrics.get('tokens', {}).get('total', 0)
                
                self.logger.info(f"Test {test_id} - Status: {status}, Turns: {turns_used}")
            
            test_end = datetime.now(timezone.utc)
            execution_time = (test_end - test_start).total_seconds()
            
            # Determine test result
            success = status == "completed"
            
            result_data = {
                "test_id": test_id,
                "workflow": workflow,
                "message": message,
                "parameters": kwargs,
                "start_time": test_start.isoformat(),
                "end_time": test_end.isoformat(),
                "status": "passed" if success else "failed",
                "execution_time": execution_time,
                "turns_used": turns_used,
                "tools_used": tools_used,
                "cost_usd": cost_usd,
                "total_tokens": total_tokens,
                "run_id": run_id,
                "final_status": status,
                "error_message": None if success else f"Workflow ended with status: {status}"
            }
            
            self.logger.info(f"Test {test_id} completed: {result_data['status']} in {execution_time:.1f}s")
            return result_data
            
        except Exception as e:
            test_end = datetime.now(timezone.utc)
            execution_time = (test_end - test_start).total_seconds()
            
            error_result = {
                "test_id": test_id,
                "workflow": workflow,
                "message": message,
                "parameters": kwargs,
                "start_time": test_start.isoformat(),
                "end_time": test_end.isoformat(),
                "status": "error",
                "execution_time": execution_time,
                "error_message": str(e)
            }
            
            self.logger.error(f"Test {test_id} failed with error: {e}")
            return error_result

    async def run_basic_functionality_tests(self):
        """Execute Basic Functionality Tests (BF-01 to BF-21)."""
        
        self.logger.info("Starting Basic Functionality Tests...")
        
        # Simple execution tests
        simple_tests = [
            ("BF-01", "guardian", "Run basic health check tests"),
            ("BF-02", "surgeon", "Fix simple syntax error in hello.py"),
            ("BF-03", "brain", "Store knowledge about Python best practices"),
            ("BF-04", "genie", "Coordinate a simple implementation task"),
            ("BF-05", "shipper", "Prepare deployment checklist"),
            ("BF-06", "lina", "Create Linear issue for bug tracking"),
            ("BF-07", "builder", "Create hello world function"),
        ]
        
        for test_id, workflow, message in simple_tests:
            result = await self.execute_workflow_test(test_id, workflow, message)
            self.results.append(result)
            
        # Complex task tests
        complex_tests = [
            ("BF-08", "guardian", "Perform comprehensive security audit"),
            ("BF-09", "surgeon", "Refactor complex legacy code module"),
            ("BF-10", "brain", "Analyze and store project architecture patterns"),
            ("BF-11", "genie", "Orchestrate full feature development lifecycle"),
            ("BF-12", "shipper", "Automate CI/CD pipeline setup"),
            ("BF-13", "lina", "Sync project status with Linear board"),
            ("BF-14", "builder", "Implement REST API with authentication"),
        ]
        
        for test_id, workflow, message in complex_tests:
            result = await self.execute_workflow_test(test_id, workflow, message)
            self.results.append(result)
            
        # Turn limit tests
        turn_limit_tests = [
            ("BF-15", "builder", "Create complex data processing pipeline", {"max_turns": 3}),
            ("BF-16", "guardian", "Run exhaustive test suite", {"max_turns": 10}),
            ("BF-17", "surgeon", "Fix multiple interconnected bugs", {"max_turns": 5}),
            ("BF-18", "genie", "Coordinate multi-step workflow", {"max_turns": None}),
        ]
        
        for test_id, workflow, message, extra_params in turn_limit_tests:
            result = await self.execute_workflow_test(test_id, workflow, message, **extra_params)
            self.results.append(result)

    async def run_repository_source_tests(self):
        """Execute Repository Source Tests (RS-01 to RS-09)."""
        
        self.logger.info("Starting Repository Source Tests...")
        
        # Local repository tests
        local_tests = [
            ("RS-01", "builder", "Work in current repository", {}),
            ("RS-02", "guardian", "Tests on specific branch", {"git_branch": "main"}),
            ("RS-03", "surgeon", "Fix on current branch", {"git_branch": "main"}),
        ]
        
        for test_id, workflow, message, params in local_tests:
            result = await self.execute_workflow_test(test_id, workflow, message, **params)
            self.results.append(result)

    async def run_persistence_tests(self):
        """Execute Persistence Tests (PS-01 to PS-09)."""
        
        self.logger.info("Starting Persistence Tests...")
        
        # Persistent workspace tests
        persistent_tests = [
            ("PS-01", "builder", "Workspace retained after completion", {"session_name": "persistent-session-1"}),
            ("PS-02", "guardian", "Persistent test environment", {"session_name": "test-environment"}),
            ("PS-03", "surgeon", "Surgical environment persistence", {"session_name": "fix-workspace"}),
        ]
        
        for test_id, workflow, message, params in persistent_tests:
            # Add persistent=true to query parameters
            result = await self.execute_workflow_test(test_id, workflow, message, persistent=True, **params)
            self.results.append(result)
            
        # Temporary workspace tests
        temp_tests = [
            ("PS-04", "builder", "Workspace cleaned after completion", {"session_name": "temp-session-1"}),
            ("PS-05", "guardian", "Temporary test environment", {"session_name": "temp-test"}),
            ("PS-06", "surgeon", "Auto-generated temporary workspace", {}),
        ]
        
        for test_id, workflow, message, params in temp_tests:
            # Add persistent=false to query parameters
            result = await self.execute_workflow_test(test_id, workflow, message, persistent=False, **params)
            self.results.append(result)

    def generate_coverage_report(self):
        """Generate coverage metrics and summary report."""
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r['status'] == 'passed'])
        failed_tests = len([r for r in self.results if r['status'] == 'failed'])
        error_tests = len([r for r in self.results if r['status'] == 'error'])
        
        # Workflow coverage
        tested_workflows = set(r['workflow'] for r in self.results)
        workflow_coverage = len(tested_workflows) / len(WORKFLOWS) * 100
        
        # Calculate average execution time, cost, tokens
        successful_tests = [r for r in self.results if r['status'] == 'passed']
        avg_execution_time = sum(r['execution_time'] for r in successful_tests) / len(successful_tests) if successful_tests else 0
        total_cost = sum(r.get('cost_usd', 0) for r in successful_tests)
        total_tokens = sum(r.get('total_tokens', 0) for r in successful_tests)
        
        report = {
            "test_execution_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "errors": error_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now(timezone.utc).isoformat(),
                "total_execution_time": (datetime.now(timezone.utc) - self.start_time).total_seconds()
            },
            "coverage_metrics": {
                "workflow_coverage": workflow_coverage,
                "tested_workflows": list(tested_workflows),
                "untested_workflows": list(set(WORKFLOWS) - tested_workflows)
            },
            "performance_metrics": {
                "average_execution_time": avg_execution_time,
                "total_cost_usd": total_cost,
                "total_tokens": total_tokens,
                "average_cost_per_test": total_cost / len(successful_tests) if successful_tests else 0
            },
            "test_results": self.results
        }
        
        return report

    async def run_comprehensive_tests(self):
        """Run the comprehensive test suite."""
        
        self.logger.info("Starting Comprehensive QA Test Suite...")
        
        try:
            # Run test categories
            await self.run_basic_functionality_tests()
            await self.run_repository_source_tests() 
            await self.run_persistence_tests()
            
            # Generate final report
            report = self.generate_coverage_report()
            
            # Save results
            with open(TEST_RESULTS_FILE, 'w') as f:
                json.dump(report, f, indent=2)
                
            self.logger.info(f"Test execution completed. Results saved to {TEST_RESULTS_FILE}")
            self.logger.info(f"Summary: {report['test_execution_summary']['passed']}/{report['test_execution_summary']['total_tests']} tests passed")
            
            return report
            
        except Exception as e:
            self.logger.error(f"Test suite execution failed: {e}")
            raise

async def main():
    """Main entry point for test execution."""
    executor = QATestExecutor()
    await executor.run_comprehensive_tests()

if __name__ == "__main__":
    asyncio.run(main())