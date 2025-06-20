#!/usr/bin/env python3
"""
Persistence Tests (PS-01 to PS-09)
Test suite covering persistent vs temporary workspaces and isolation.
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
        logging.FileHandler('qa_persistence.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PersistenceTests:
    """Execute Persistence Tests (PS-01 to PS-09)."""
    
    def __init__(self):
        self.results = []
        self.start_time = datetime.now(timezone.utc)
        
    async def execute_persistence_test(
        self,
        test_id: str,
        workflow: str,
        message: str,
        persistent: bool,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a single persistence test case."""
        
        test_start = datetime.now(timezone.utc)
        persistence_mode = "persistent" if persistent else "temporary"
        logger.info(f"💾 Starting {test_id}: {workflow} - {persistence_mode} workspace test")
        
        try:
            # Import MCP tools
            import sys
            import os
            sys.path.append('/home/namastex/workspace/am-agents-labs')
            
            from src.mcp.automagik_workflows import run_workflow, get_workflow_status
            
            # Start workflow with persistence parameter
            run_result = await run_workflow(
                workflow_name=workflow,
                message=message,
                persistent=persistent,
                **kwargs
            )
            
            run_id = run_result.get('run_id')
            if not run_id:
                raise Exception("No run_id returned from workflow execution")
            
            logger.info(f"🚀 {test_id} started with run_id: {run_id} (persistent={persistent})")
            
            # Monitor workflow with appropriate timeouts
            status = "pending"
            max_wait_time = 420  # 7 minutes for persistence tests
            check_interval = 12  # Check every 12 seconds
            total_waited = 0
            workspace_info = {}
            
            while status in ["pending", "running"] and total_waited < max_wait_time:
                await asyncio.sleep(check_interval)
                total_waited += check_interval
                
                try:
                    status_result = await get_workflow_status(run_id, detailed=True)
                    status = status_result.get('status', 'unknown')
                    
                    progress = status_result.get('progress', {})
                    completion_pct = progress.get('completion_percentage', 0)
                    
                    # Extract workspace information if available
                    debug_info = status_result.get('debug', {})
                    session_info = debug_info.get('session_info', {})
                    if 'workspace_path' in session_info:
                        workspace_info['workspace_path'] = session_info['workspace_path']
                    
                    logger.info(f"💾 {test_id} - Status: {status}, Progress: {completion_pct}%, Mode: {persistence_mode}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ {test_id} status check failed: {e}")
                    continue
            
            test_end = datetime.now(timezone.utc)
            execution_time = (test_end - test_start).total_seconds()
            
            # Get final status and workspace details
            final_status_result = {}
            try:
                final_status_result = await get_workflow_status(run_id, detailed=True)
                debug_info = final_status_result.get('debug', {})
                session_info = debug_info.get('session_info', {})
                workspace_info.update(session_info)
            except:
                pass
            
            success = status == "completed"
            
            result_data = {
                "test_id": test_id,
                "workflow": workflow,
                "message": message,
                "persistence_mode": persistence_mode,
                "persistent": persistent,
                "start_time": test_start.isoformat(),
                "end_time": test_end.isoformat(),
                "status": "passed" if success else ("timeout" if total_waited >= max_wait_time else "failed"),
                "execution_time": execution_time,
                "run_id": run_id,
                "final_status": status,
                "total_wait_time": total_waited,
                "workspace_info": workspace_info,
                "session_config": kwargs,
                "error_message": None if success else f"Persistence test ended with status: {status}"
            }
            
            status_emoji = "✅" if success else ("⏰" if total_waited >= max_wait_time else "❌")
            logger.info(f"{status_emoji} {test_id} completed: {result_data['status']} in {execution_time:.1f}s ({persistence_mode})")
            return result_data
            
        except Exception as e:
            test_end = datetime.now(timezone.utc)
            execution_time = (test_end - test_start).total_seconds()
            
            error_result = {
                "test_id": test_id,
                "workflow": workflow,
                "message": message,
                "persistence_mode": persistence_mode,
                "persistent": persistent,
                "start_time": test_start.isoformat(),
                "end_time": test_end.isoformat(),
                "status": "error",
                "execution_time": execution_time,
                "error_message": str(e),
                "run_id": None
            }
            
            logger.error(f"💥 {test_id} failed with error: {e}")
            return error_result

    async def run_persistent_workspace_tests(self):
        """Execute persistent workspace tests (PS-01 to PS-03)."""
        
        logger.info("💾 Starting Persistent Workspace Tests...")
        
        persistent_tests = [
            {
                "test_id": "PS-01",
                "workflow": "builder",
                "message": "Create utility function in persistent workspace that should be retained after completion",
                "params": {
                    "session_name": "persistent-session-1",
                    "max_turns": 6
                }
            },
            {
                "test_id": "PS-02",
                "workflow": "guardian", 
                "message": "Set up persistent test environment with configuration files",
                "params": {
                    "session_name": "test-environment",
                    "max_turns": 8
                }
            },
            {
                "test_id": "PS-03",
                "workflow": "surgeon",
                "message": "Create surgical environment persistence with diagnostic files",
                "params": {
                    "session_name": "fix-workspace",
                    "max_turns": 5
                }
            }
        ]
        
        for test_config in persistent_tests:
            result = await self.execute_persistence_test(
                test_config["test_id"],
                test_config["workflow"],
                test_config["message"],
                persistent=True,
                **test_config["params"]
            )
            self.results.append(result)
            
            # Delay between persistent tests to avoid conflicts
            await asyncio.sleep(40)

    async def run_temporary_workspace_tests(self):
        """Execute temporary workspace tests (PS-04 to PS-06)."""
        
        logger.info("🗑️ Starting Temporary Workspace Tests...")
        
        temporary_tests = [
            {
                "test_id": "PS-04",
                "workflow": "builder",
                "message": "Create temporary function that should be cleaned after completion",
                "params": {
                    "session_name": "temp-session-1",
                    "max_turns": 5
                }
            },
            {
                "test_id": "PS-05",
                "workflow": "guardian",
                "message": "Run temporary test environment that cleans up automatically",
                "params": {
                    "session_name": "temp-test",
                    "max_turns": 6
                }
            },
            {
                "test_id": "PS-06",
                "workflow": "surgeon",
                "message": "Auto-generated temporary workspace for quick fixes",
                "params": {
                    "max_turns": 4
                }
            }
        ]
        
        for test_config in temporary_tests:
            result = await self.execute_persistence_test(
                test_config["test_id"],
                test_config["workflow"],
                test_config["message"],
                persistent=False,
                **test_config["params"]
            )
            self.results.append(result)
            
            await asyncio.sleep(35)

    async def run_workspace_isolation_tests(self):
        """Execute workspace isolation tests (PS-07 to PS-09)."""
        
        logger.info("🔒 Starting Workspace Isolation Tests...")
        
        # Test parallel persistent workspaces
        logger.info("🔄 PS-07: Testing parallel persistent workspaces")
        
        # Start two persistent workflows in parallel
        builder_task = asyncio.create_task(
            self.execute_persistence_test(
                "PS-07A",
                "builder",
                "Create function A in isolated persistent workspace",
                persistent=True,
                session_name="isolated-builder-workspace",
                max_turns=5
            )
        )
        
        # Small delay to avoid exact simultaneity
        await asyncio.sleep(5)
        
        guardian_task = asyncio.create_task(
            self.execute_persistence_test(
                "PS-07B", 
                "guardian",
                "Run tests B in isolated persistent workspace",
                persistent=True,
                session_name="isolated-guardian-workspace",
                max_turns=6
            )
        )
        
        # Wait for both to complete
        builder_result, guardian_result = await asyncio.gather(builder_task, guardian_task)
        
        # Create combined result for PS-07
        ps07_result = {
            "test_id": "PS-07",
            "workflow": "parallel_persistent",
            "message": "Test parallel persistent workspace isolation",
            "persistence_mode": "persistent_parallel",
            "start_time": min(builder_result["start_time"], guardian_result["start_time"]),
            "end_time": max(builder_result["end_time"], guardian_result["end_time"]),
            "status": "passed" if builder_result["status"] == "passed" and guardian_result["status"] == "passed" else "failed",
            "execution_time": max(builder_result["execution_time"], guardian_result["execution_time"]),
            "sub_results": {
                "builder": builder_result,
                "guardian": guardian_result
            },
            "isolation_test": True
        }
        
        self.results.append(ps07_result)
        
        await asyncio.sleep(30)
        
        # Test parallel temporary workspaces
        logger.info("🔄 PS-08: Testing parallel temporary workspaces")
        
        surgeon_task = asyncio.create_task(
            self.execute_persistence_test(
                "PS-08A",
                "surgeon",
                "Fix issue A in isolated temporary workspace", 
                persistent=False,
                session_name="temp-surgeon-workspace",
                max_turns=4
            )
        )
        
        await asyncio.sleep(5)
        
        brain_task = asyncio.create_task(
            self.execute_persistence_test(
                "PS-08B",
                "brain",
                "Store knowledge B in isolated temporary workspace",
                persistent=False,
                session_name="temp-brain-workspace", 
                max_turns=5
            )
        )
        
        surgeon_result, brain_result = await asyncio.gather(surgeon_task, brain_task)
        
        ps08_result = {
            "test_id": "PS-08",
            "workflow": "parallel_temporary",
            "message": "Test parallel temporary workspace isolation",
            "persistence_mode": "temporary_parallel",
            "start_time": min(surgeon_result["start_time"], brain_result["start_time"]),
            "end_time": max(surgeon_result["end_time"], brain_result["end_time"]),
            "status": "passed" if surgeon_result["status"] == "passed" and brain_result["status"] == "passed" else "failed",
            "execution_time": max(surgeon_result["execution_time"], brain_result["execution_time"]),
            "sub_results": {
                "surgeon": surgeon_result,
                "brain": brain_result
            },
            "isolation_test": True
        }
        
        self.results.append(ps08_result)
        
        await asyncio.sleep(30)
        
        # Test mixed persistence modes
        logger.info("🔄 PS-09: Testing mixed persistence mode isolation")
        
        mixed_builder_task = asyncio.create_task(
            self.execute_persistence_test(
                "PS-09A",
                "builder",
                "Build feature in persistent mode",
                persistent=True,
                session_name="mixed-persistent-builder",
                max_turns=5
            )
        )
        
        await asyncio.sleep(5)
        
        mixed_surgeon_task = asyncio.create_task(
            self.execute_persistence_test(
                "PS-09B",
                "surgeon", 
                "Quick fix in temporary mode",
                persistent=False,
                session_name="mixed-temp-surgeon",
                max_turns=4
            )
        )
        
        mixed_builder_result, mixed_surgeon_result = await asyncio.gather(mixed_builder_task, mixed_surgeon_task)
        
        ps09_result = {
            "test_id": "PS-09",
            "workflow": "mixed_persistence",
            "message": "Test mixed persistence mode isolation",
            "persistence_mode": "mixed",
            "start_time": min(mixed_builder_result["start_time"], mixed_surgeon_result["start_time"]),
            "end_time": max(mixed_builder_result["end_time"], mixed_surgeon_result["end_time"]),
            "status": "passed" if mixed_builder_result["status"] == "passed" and mixed_surgeon_result["status"] == "passed" else "failed",
            "execution_time": max(mixed_builder_result["execution_time"], mixed_surgeon_result["execution_time"]),
            "sub_results": {
                "persistent_builder": mixed_builder_result,
                "temporary_surgeon": mixed_surgeon_result
            },
            "isolation_test": True
        }
        
        self.results.append(ps09_result)

    def generate_persistence_report(self):
        """Generate comprehensive persistence testing report."""
        
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r['status'] == 'passed'])
        failed_tests = len([r for r in self.results if r['status'] == 'failed'])
        error_tests = len([r for r in self.results if r['status'] == 'error'])
        timeout_tests = len([r for r in self.results if r['status'] == 'timeout'])
        
        # Persistence mode breakdown
        persistent_tests = [r for r in self.results if r.get('persistence_mode') in ['persistent', 'persistent_parallel']]
        temporary_tests = [r for r in self.results if r.get('persistence_mode') in ['temporary', 'temporary_parallel']]
        isolation_tests = [r for r in self.results if r.get('isolation_test', False)]
        
        # Workspace analysis
        workspaces_created = len([r for r in self.results if r.get('workspace_info')])
        
        report = {
            "test_suite": "Persistence Tests (PS-01 to PS-09)",
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
            "persistence_coverage": {
                "persistent_workspace_tests": {
                    "total": len([r for r in persistent_tests if not r.get('isolation_test')]),
                    "passed": len([r for r in persistent_tests if not r.get('isolation_test') and r['status'] == 'passed']),
                },
                "temporary_workspace_tests": {
                    "total": len([r for r in temporary_tests if not r.get('isolation_test')]), 
                    "passed": len([r for r in temporary_tests if not r.get('isolation_test') and r['status'] == 'passed']),
                },
                "isolation_tests": {
                    "total": len(isolation_tests),
                    "passed": len([r for r in isolation_tests if r['status'] == 'passed']),
                }
            },
            "workspace_analysis": {
                "workspaces_created": workspaces_created,
                "persistence_modes_tested": len(set(r.get('persistence_mode') for r in self.results if r.get('persistence_mode'))),
                "parallel_execution_tests": len([r for r in self.results if 'parallel' in r.get('persistence_mode', '')]),
            },
            "detailed_results": self.results
        }
        
        # Calculate success rates
        for category in report["persistence_coverage"]:
            category_data = report["persistence_coverage"][category]
            if category_data["total"] > 0:
                category_data["success_rate"] = (category_data["passed"] / category_data["total"]) * 100
            else:
                category_data["success_rate"] = 0
        
        return report

    async def run_all_persistence_tests(self):
        """Execute the complete persistence test suite."""
        
        logger.info("💾 Starting Persistence Test Suite (PS-01 to PS-09)")
        
        try:
            await self.run_persistent_workspace_tests()
            await self.run_temporary_workspace_tests()
            await self.run_workspace_isolation_tests()
            
            # Generate final report
            report = self.generate_persistence_report()
            
            # Save results
            with open('qa_persistence_results.json', 'w') as f:
                json.dump(report, f, indent=2)
                
            logger.info("📊 Persistence Tests completed!")
            logger.info(f"✅ Results: {report['execution_summary']['passed']}/{report['execution_summary']['total_tests']} tests passed")
            logger.info(f"💾 Persistent tests: {report['persistence_coverage']['persistent_workspace_tests']['success_rate']:.1f}% success")
            logger.info(f"🗑️ Temporary tests: {report['persistence_coverage']['temporary_workspace_tests']['success_rate']:.1f}% success")
            logger.info(f"🔒 Isolation tests: {report['persistence_coverage']['isolation_tests']['success_rate']:.1f}% success")
            
            return report
            
        except Exception as e:
            logger.error(f"💥 Persistence test suite execution failed: {e}")
            raise

async def main():
    """Main entry point for persistence tests."""
    test_executor = PersistenceTests()
    await test_executor.run_all_persistence_tests()

if __name__ == "__main__":
    asyncio.run(main())