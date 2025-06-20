#!/usr/bin/env python3
"""
Basic Functionality Tests (BF-01 to BF-21)
Comprehensive test suite for all 7 workflows with various complexity levels.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import uuid
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('qa_basic_functionality.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BasicFunctionalityTests:
    """Execute Basic Functionality Tests (BF-01 to BF-21)."""
    
    def __init__(self):
        self.results = []
        self.start_time = datetime.now(timezone.utc)
        
    async def execute_single_test(
        self,
        test_id: str,
        workflow: str,
        message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a single test case using MCP workflow tools."""
        
        test_start = datetime.now(timezone.utc)
        logger.info(f"🧪 Starting {test_id}: {workflow} - {message[:50]}...")
        
        try:
            # Import MCP tools locally to avoid global dependencies
            import sys
            import os
            sys.path.append('/home/namastex/workspace/am-agents-labs')
            
            # Use MCP workflow tool directly
            from src.mcp.automagik_workflows import run_workflow, get_workflow_status
            
            # Start workflow
            run_result = await run_workflow(
                workflow_name=workflow,
                message=message,
                **kwargs
            )
            
            run_id = run_result.get('run_id')
            if not run_id:
                raise Exception("No run_id returned from workflow execution")
            
            logger.info(f"🚀 {test_id} started with run_id: {run_id}")
            
            # Monitor workflow until completion with progressive timeouts
            status = "pending"
            turns_used = 0
            tools_used = []
            cost_usd = 0.0
            total_tokens = 0
            max_wait_time = 600  # 10 minutes max
            check_interval = 10  # Start with 10 second intervals
            total_waited = 0
            
            while status in ["pending", "running"] and total_waited < max_wait_time:
                await asyncio.sleep(check_interval)
                total_waited += check_interval
                
                try:
                    status_result = await get_workflow_status(run_id, detailed=True)
                    status = status_result.get('status', 'unknown')
                    
                    progress = status_result.get('progress', {})
                    metrics = status_result.get('metrics', {})
                    
                    turns_used = progress.get('turns', 0)
                    tools_used = metrics.get('tools_used', [])
                    cost_usd = metrics.get('cost_usd', 0.0)
                    total_tokens = metrics.get('tokens', {}).get('total', 0)
                    
                    completion_pct = progress.get('completion_percentage', 0)
                    logger.info(f"📊 {test_id} - Status: {status}, Progress: {completion_pct}%, Turns: {turns_used}")
                    
                    # Adaptive check intervals
                    if completion_pct > 80:
                        check_interval = 5  # Check more frequently near completion
                    elif completion_pct > 50:
                        check_interval = 10
                    else:
                        check_interval = 15  # Check less frequently during setup
                        
                except Exception as e:
                    logger.warning(f"⚠️ {test_id} status check failed: {e}")
                    continue
            
            test_end = datetime.now(timezone.utc)
            execution_time = (test_end - test_start).total_seconds()
            
            # Determine final result
            success = status == "completed"
            
            result_data = {
                "test_id": test_id,
                "workflow": workflow,
                "message": message,
                "parameters": kwargs,
                "start_time": test_start.isoformat(),
                "end_time": test_end.isoformat(),
                "status": "passed" if success else ("timeout" if total_waited >= max_wait_time else "failed"),
                "execution_time": execution_time,
                "turns_used": turns_used,
                "tools_used": tools_used,
                "cost_usd": cost_usd,
                "total_tokens": total_tokens,
                "run_id": run_id,
                "final_status": status,
                "total_wait_time": total_waited,
                "error_message": None if success else f"Workflow ended with status: {status}"
            }
            
            status_emoji = "✅" if success else ("⏰" if total_waited >= max_wait_time else "❌")
            logger.info(f"{status_emoji} {test_id} completed: {result_data['status']} in {execution_time:.1f}s")
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
                "error_message": str(e),
                "run_id": None
            }
            
            logger.error(f"💥 {test_id} failed with error: {e}")
            return error_result

    async def run_simple_execution_tests(self):
        """Execute simple workflow tests (BF-01 to BF-07)."""
        
        logger.info("🚀 Starting Simple Execution Tests...")
        
        simple_tests = [
            ("BF-01", "guardian", "Run basic health check tests on the current codebase"),
            ("BF-02", "surgeon", "Fix any simple syntax errors found in Python files"),
            ("BF-03", "brain", "Store knowledge about Python best practices for this project"),
            ("BF-04", "genie", "Coordinate a simple documentation update task"),
            ("BF-05", "shipper", "Prepare a basic deployment checklist for the project"),
            ("BF-06", "lina", "Create a simple Linear issue for tracking test progress"),
            ("BF-07", "builder", "Create a simple hello world function with tests"),
        ]
        
        for test_id, workflow, message in simple_tests:
            result = await self.execute_single_test(
                test_id, 
                workflow, 
                message,
                session_name=f"qa_simple_{test_id.lower()}",
                max_turns=5
            )
            self.results.append(result)
            
            # Small delay between tests to avoid overwhelming the system
            await asyncio.sleep(30)

    async def run_complex_task_tests(self):
        """Execute complex workflow tests (BF-08 to BF-14)."""
        
        logger.info("🔧 Starting Complex Task Tests...")
        
        complex_tests = [
            ("BF-08", "guardian", "Perform comprehensive security audit of the authentication system"),
            ("BF-09", "surgeon", "Refactor any complex code modules to improve maintainability"),
            ("BF-10", "brain", "Analyze and store project architecture patterns and best practices"),
            ("BF-11", "genie", "Orchestrate a full feature development lifecycle for a small utility"),
            ("BF-12", "shipper", "Set up automated CI/CD pipeline configuration"),
            ("BF-13", "lina", "Sync current project status with Linear workspace"),
            ("BF-14", "builder", "Implement a comprehensive REST API endpoint with validation"),
        ]
        
        for test_id, workflow, message in complex_tests:
            result = await self.execute_single_test(
                test_id, 
                workflow, 
                message,
                session_name=f"qa_complex_{test_id.lower()}",
                max_turns=15
            )
            self.results.append(result)
            
            # Longer delay between complex tests
            await asyncio.sleep(60)

    async def run_turn_limit_tests(self):
        """Execute turn limit tests (BF-15 to BF-18)."""
        
        logger.info("🔄 Starting Turn Limit Tests...")
        
        turn_limit_tests = [
            ("BF-15", "builder", "Create a complex data processing pipeline", {"max_turns": 3}),
            ("BF-16", "guardian", "Run exhaustive test suite on existing code", {"max_turns": 10}),
            ("BF-17", "surgeon", "Fix multiple interconnected code issues", {"max_turns": 5}),
            ("BF-18", "genie", "Coordinate multi-step workflow optimization", {"max_turns": None}),
        ]
        
        for test_id, workflow, message, extra_params in turn_limit_tests:
            result = await self.execute_single_test(
                test_id, 
                workflow, 
                message,
                session_name=f"qa_turns_{test_id.lower()}",
                **extra_params
            )
            self.results.append(result)
            
            await asyncio.sleep(45)

    async def run_timeout_tests(self):
        """Execute timeout tests (BF-19 to BF-21)."""
        
        logger.info("⏱️ Starting Timeout Tests...")
        
        timeout_tests = [
            ("BF-19", "shipper", "Test deployment process with time constraints", {"timeout": 3600}),
            ("BF-20", "brain", "Process and organize large knowledge base", {"timeout": 7200}),
            ("BF-21", "builder", "Quick prototype implementation under time pressure", {"timeout": 300}),
        ]
        
        for test_id, workflow, message, extra_params in timeout_tests:
            result = await self.execute_single_test(
                test_id, 
                workflow, 
                message,
                session_name=f"qa_timeout_{test_id.lower()}",
                **extra_params
            )
            self.results.append(result)
            
            await asyncio.sleep(30)

    def generate_summary_report(self):
        """Generate summary report of all basic functionality tests."""
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r['status'] == 'passed'])
        failed_tests = len([r for r in self.results if r['status'] == 'failed'])
        error_tests = len([r for r in self.results if r['status'] == 'error'])
        timeout_tests = len([r for r in self.results if r['status'] == 'timeout'])
        
        # Calculate metrics for successful tests
        successful_tests = [r for r in self.results if r['status'] == 'passed']
        
        avg_execution_time = sum(r['execution_time'] for r in successful_tests) / len(successful_tests) if successful_tests else 0
        total_cost = sum(r.get('cost_usd', 0) for r in successful_tests)
        total_tokens = sum(r.get('total_tokens', 0) for r in successful_tests)
        avg_turns = sum(r.get('turns_used', 0) for r in successful_tests) / len(successful_tests) if successful_tests else 0
        
        # Workflow coverage
        tested_workflows = set(r['workflow'] for r in self.results)
        
        report = {
            "test_suite": "Basic Functionality Tests (BF-01 to BF-21)",
            "execution_summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "errors": error_tests,
                "timeouts": timeout_tests,
                "success_rate": (passed_tests / total_tests * 100) if total_tests > 0 else 0,
                "start_time": self.start_time.isoformat(),
                "end_time": datetime.now(timezone.utc).isoformat(),
                "total_execution_time": (datetime.now(timezone.utc) - self.start_time).total_seconds()
            },
            "performance_metrics": {
                "average_execution_time": avg_execution_time,
                "total_cost_usd": total_cost,
                "total_tokens": total_tokens,
                "average_turns_per_test": avg_turns,
                "workflow_coverage": len(tested_workflows)
            },
            "workflow_breakdown": {
                workflow: len([r for r in self.results if r['workflow'] == workflow])
                for workflow in tested_workflows
            },
            "detailed_results": self.results
        }
        
        return report

    async def run_all_tests(self):
        """Execute the complete basic functionality test suite."""
        
        logger.info("🎯 Starting Basic Functionality Test Suite (BF-01 to BF-21)")
        
        try:
            await self.run_simple_execution_tests()
            await self.run_complex_task_tests()
            await self.run_turn_limit_tests()
            await self.run_timeout_tests()
            
            # Generate final report
            report = self.generate_summary_report()
            
            # Save results
            with open('qa_basic_functionality_results.json', 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info("📊 Basic Functionality Tests completed!")
            logger.info(f"✅ Results: {report['execution_summary']['passed']}/{report['execution_summary']['total_tests']} tests passed")
            logger.info(f"💰 Total cost: ${report['performance_metrics']['total_cost_usd']:.4f}")
            logger.info(f"⏱️ Average execution time: {report['performance_metrics']['average_execution_time']:.1f}s")
            
            return report
            
        except Exception as e:
            logger.error(f"💥 Test suite execution failed: {e}")
            raise

async def main():
    """Main entry point for basic functionality tests."""
    test_executor = BasicFunctionalityTests()
    await test_executor.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main())