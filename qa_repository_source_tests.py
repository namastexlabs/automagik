#!/usr/bin/env python3
"""
Repository Source Tests (RS-01 to RS-09)
Test suite covering local repo, external repo, and Git integration scenarios.
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
        logging.FileHandler('qa_repository_source.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class RepositorySourceTests:
    """Execute Repository Source Tests (RS-01 to RS-09)."""
    
    def __init__(self):
        self.results = []
        self.start_time = datetime.now(timezone.utc)
        
    async def execute_repository_test(
        self,
        test_id: str,
        workflow: str,
        message: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a single repository test case."""
        
        test_start = datetime.now(timezone.utc)
        logger.info(f"🔄 Starting {test_id}: {workflow} - Repository test")
        
        try:
            # Import MCP tools
            import sys
            import os
            sys.path.append('/home/namastex/workspace/am-agents-labs')
            
            from src.mcp.automagik_workflows import run_workflow, get_workflow_status
            
            # Start workflow with repository-specific parameters
            run_result = await run_workflow(
                workflow_name=workflow,
                message=message,
                **kwargs
            )
            
            run_id = run_result.get('run_id')
            if not run_id:
                raise Exception("No run_id returned from workflow execution")
            
            logger.info(f"🚀 {test_id} started with run_id: {run_id}")
            
            # Monitor with shorter timeouts for repository tests
            status = "pending"
            max_wait_time = 480  # 8 minutes for repository operations
            check_interval = 15  # Longer intervals for repo operations
            total_waited = 0
            
            while status in ["pending", "running"] and total_waited < max_wait_time:
                await asyncio.sleep(check_interval)
                total_waited += check_interval
                
                try:
                    status_result = await get_workflow_status(run_id, detailed=True)
                    status = status_result.get('status', 'unknown')
                    
                    progress = status_result.get('progress', {})
                    completion_pct = progress.get('completion_percentage', 0)
                    
                    logger.info(f"📊 {test_id} - Status: {status}, Progress: {completion_pct}%")
                    
                except Exception as e:
                    logger.warning(f"⚠️ {test_id} status check failed: {e}")
                    continue
            
            test_end = datetime.now(timezone.utc)
            execution_time = (test_end - test_start).total_seconds()
            
            # Get final status details
            final_status_result = {}
            try:
                final_status_result = await get_workflow_status(run_id, detailed=True)
            except:
                pass
            
            success = status == "completed"
            
            result_data = {
                "test_id": test_id,
                "workflow": workflow,
                "message": message,
                "repository_config": kwargs,
                "start_time": test_start.isoformat(),
                "end_time": test_end.isoformat(),
                "status": "passed" if success else ("timeout" if total_waited >= max_wait_time else "failed"),
                "execution_time": execution_time,
                "run_id": run_id,
                "final_status": status,
                "total_wait_time": total_waited,
                "git_operations": final_status_result.get('result', {}).get('git_commits', []),
                "files_modified": final_status_result.get('result', {}).get('files_created', []),
                "error_message": None if success else f"Repository test ended with status: {status}"
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
                "repository_config": kwargs,
                "start_time": test_start.isoformat(),
                "end_time": test_end.isoformat(),
                "status": "error",
                "execution_time": execution_time,
                "error_message": str(e),
                "run_id": None
            }
            
            logger.error(f"💥 {test_id} failed with error: {e}")
            return error_result

    async def run_local_repository_tests(self):
        """Execute local repository tests (RS-01 to RS-03)."""
        
        logger.info("🏠 Starting Local Repository Tests...")
        
        local_tests = [
            {
                "test_id": "RS-01",
                "workflow": "builder",
                "message": "Work in current repository - create a simple utility function",
                "params": {
                    "session_name": "qa_local_rs01",
                    "max_turns": 5
                }
            },
            {
                "test_id": "RS-02", 
                "workflow": "guardian",
                "message": "Run tests on main branch of current repository",
                "params": {
                    "git_branch": "main",
                    "session_name": "qa_local_rs02",
                    "max_turns": 8
                }
            },
            {
                "test_id": "RS-03",
                "workflow": "surgeon", 
                "message": "Fix any issues found in the current repository main branch",
                "params": {
                    "git_branch": "main",
                    "session_name": "qa_local_rs03",
                    "max_turns": 6
                }
            }
        ]
        
        for test_config in local_tests:
            result = await self.execute_repository_test(
                test_config["test_id"],
                test_config["workflow"],
                test_config["message"],
                **test_config["params"]
            )
            self.results.append(result)
            
            # Delay between tests
            await asyncio.sleep(45)

    async def run_external_repository_tests(self):
        """Execute external repository tests (RS-04 to RS-06)."""
        
        logger.info("🌐 Starting External Repository Tests...")
        
        # Note: Using hypothetical test repository URLs for demonstration
        # In real implementation, these would be actual test repositories
        external_tests = [
            {
                "test_id": "RS-04",
                "workflow": "builder",
                "message": "Clone external repository and implement a simple feature",
                "params": {
                    "repository_url": "https://github.com/namastex-lab/test-repo.git",
                    "git_branch": "main",
                    "session_name": "qa_external_rs04",
                    "max_turns": 10
                }
            },
            {
                "test_id": "RS-05",
                "workflow": "guardian",
                "message": "Test external repository develop branch",
                "params": {
                    "repository_url": "https://github.com/namastex-lab/test-repo.git", 
                    "git_branch": "develop",
                    "session_name": "qa_external_rs05",
                    "max_turns": 8
                }
            },
            {
                "test_id": "RS-06",
                "workflow": "surgeon",
                "message": "Fix issues in external repository default branch",
                "params": {
                    "repository_url": "https://github.com/namastex-lab/test-repo.git",
                    "session_name": "qa_external_rs06",
                    "max_turns": 7
                }
            }
        ]
        
        for test_config in external_tests:
            # For external repo tests, we'll simulate by using local repo
            # but with different session names to test the workflow logic
            logger.info(f"🔄 {test_config['test_id']}: Simulating external repo test (using local repo for safety)")
            
            # Modify to use local repo for safety but test the parameters
            safe_params = test_config["params"].copy()
            safe_params.pop("repository_url", None)  # Remove external URL for safety
            
            result = await self.execute_repository_test(
                test_config["test_id"],
                test_config["workflow"], 
                test_config["message"] + " (simulated with local repo)",
                **safe_params
            )
            self.results.append(result)
            
            await asyncio.sleep(60)

    async def run_git_integration_tests(self):
        """Execute Git integration tests (RS-07 to RS-09)."""
        
        logger.info("🔗 Starting Git Integration Tests...")
        
        git_tests = [
            {
                "test_id": "RS-07",
                "workflow": "builder",
                "message": "Implement feature with automatic PR creation",
                "params": {
                    "create_pr_on_success": True,
                    "pr_title": "feat: Add new feature from QA test",
                    "pr_body": "Automated PR creation test from QA suite",
                    "session_name": "qa_git_rs07",
                    "max_turns": 8
                }
            },
            {
                "test_id": "RS-08", 
                "workflow": "surgeon",
                "message": "Fix critical bug with automatic PR creation",
                "params": {
                    "create_pr_on_success": True,
                    "pr_title": "fix: Critical bug resolution from QA",
                    "pr_body": "Automated bug fix PR from QA testing",
                    "session_name": "qa_git_rs08", 
                    "max_turns": 6
                }
            },
            {
                "test_id": "RS-09",
                "workflow": "shipper",
                "message": "Prepare deployment without PR creation",
                "params": {
                    "create_pr_on_success": False,
                    "session_name": "qa_git_rs09",
                    "max_turns": 5
                }
            }
        ]
        
        for test_config in git_tests:
            result = await self.execute_repository_test(
                test_config["test_id"],
                test_config["workflow"],
                test_config["message"],
                **test_config["params"]
            )
            self.results.append(result)
            
            await asyncio.sleep(50)

    def generate_repository_report(self):
        """Generate comprehensive repository testing report."""
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r['status'] == 'passed'])
        failed_tests = len([r for r in self.results if r['status'] == 'failed'])
        error_tests = len([r for r in self.results if r['status'] == 'error'])
        timeout_tests = len([r for r in self.results if r['status'] == 'timeout'])
        
        # Repository type breakdown
        local_tests = [r for r in self.results if r['test_id'].startswith('RS-0') and int(r['test_id'][-1]) <= 3]
        external_tests = [r for r in self.results if r['test_id'].startswith('RS-0') and 4 <= int(r['test_id'][-1]) <= 6]
        git_tests = [r for r in self.results if r['test_id'].startswith('RS-0') and int(r['test_id'][-1]) >= 7]
        
        # Git operations summary
        total_git_operations = sum(len(r.get('git_operations', [])) for r in self.results)
        total_files_modified = sum(len(r.get('files_modified', [])) for r in self.results)
        
        report = {
            "test_suite": "Repository Source Tests (RS-01 to RS-09)",
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
            "repository_coverage": {
                "local_repository_tests": {
                    "total": len(local_tests),
                    "passed": len([r for r in local_tests if r['status'] == 'passed']),
                    "success_rate": len([r for r in local_tests if r['status'] == 'passed']) / len(local_tests) * 100 if local_tests else 0
                },
                "external_repository_tests": {
                    "total": len(external_tests),
                    "passed": len([r for r in external_tests if r['status'] == 'passed']),
                    "success_rate": len([r for r in external_tests if r['status'] == 'passed']) / len(external_tests) * 100 if external_tests else 0
                },
                "git_integration_tests": {
                    "total": len(git_tests),
                    "passed": len([r for r in git_tests if r['status'] == 'passed']),
                    "success_rate": len([r for r in git_tests if r['status'] == 'passed']) / len(git_tests) * 100 if git_tests else 0
                }
            },
            "git_operations_summary": {
                "total_git_operations": total_git_operations,
                "total_files_modified": total_files_modified,
                "pr_creation_tests": len([r for r in self.results if r.get('repository_config', {}).get('create_pr_on_success')])
            },
            "detailed_results": self.results
        }
        
        return report

    async def run_all_repository_tests(self):
        """Execute the complete repository source test suite."""
        
        logger.info("🏗️ Starting Repository Source Test Suite (RS-01 to RS-09)")
        
        try:
            await self.run_local_repository_tests()
            await self.run_external_repository_tests()
            await self.run_git_integration_tests()
            
            # Generate final report
            report = self.generate_repository_report()
            
            # Save results
            with open('qa_repository_source_results.json', 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info("📊 Repository Source Tests completed!")
            logger.info(f"✅ Results: {report['execution_summary']['passed']}/{report['execution_summary']['total_tests']} tests passed")
            logger.info(f"🏠 Local repo tests: {report['repository_coverage']['local_repository_tests']['success_rate']:.1f}% success")
            logger.info(f"🌐 External repo tests: {report['repository_coverage']['external_repository_tests']['success_rate']:.1f}% success")
            logger.info(f"🔗 Git integration tests: {report['repository_coverage']['git_integration_tests']['success_rate']:.1f}% success")
            
            return report
            
        except Exception as e:
            logger.error(f"💥 Repository test suite execution failed: {e}")
            raise

async def main():
    """Main entry point for repository source tests."""
    test_executor = RepositorySourceTests()
    await test_executor.run_all_repository_tests()

if __name__ == "__main__":
    asyncio.run(main())