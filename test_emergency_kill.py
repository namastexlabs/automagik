#!/usr/bin/env python3
"""
Emergency Kill Test Script for Stuck Workflow run_5fbae44ab6f0

This script tests the emergency kill functionality by:
1. Checking for the stuck workflow run_5fbae44ab6f0
2. Testing the kill functionality directly
3. Verifying process termination
"""

import asyncio
import sys
import os
import subprocess
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_emergency_kill():
    """Test the emergency kill functionality."""
    target_run_id = "run_5fbae44ab6f0"
    
    try:
        logger.info(f"🚨 EMERGENCY KILL TEST for {target_run_id}")
        
        # Check for Claude processes before kill
        logger.info("Checking for running Claude processes...")
        result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        claude_processes = [line for line in result.stdout.split('\n') if 'claude' in line.lower() and 'grep' not in line]
        
        logger.info(f"Found {len(claude_processes)} Claude processes before kill:")
        for i, proc in enumerate(claude_processes):
            logger.info(f"  {i+1}. {proc.strip()}")
        
        # Test 1: Import and test CLI executor kill functionality
        logger.info("\n📋 TEST 1: Testing ClaudeCLIExecutor.cancel_execution()")
        try:
            from src.agents.claude_code.cli_executor import ClaudeCLIExecutor
            
            cli_executor = ClaudeCLIExecutor()
            kill_result = await cli_executor.cancel_execution(target_run_id)
            
            logger.info(f"✅ CLI Executor kill result: {kill_result}")
            
        except Exception as e:
            logger.error(f"❌ CLI Executor kill failed: {e}")
        
        # Test 2: Test LocalExecutor kill functionality 
        logger.info("\n📋 TEST 2: Testing LocalExecutor.cancel_execution()")
        try:
            from src.agents.claude_code.local_executor import LocalExecutor
            
            local_executor = LocalExecutor()
            kill_result = await local_executor.cancel_execution(target_run_id)
            
            logger.info(f"✅ Local Executor kill result: {kill_result}")
            
        except Exception as e:
            logger.error(f"❌ Local Executor kill failed: {e}")
        
        # Test 3: Test workflow process database functionality
        logger.info("\n📋 TEST 3: Testing workflow process database operations")
        try:
            from src.db.repository import get_workflow_process, list_workflow_processes, mark_process_terminated
            
            # Check if the target run_id exists in database
            workflow_process = get_workflow_process(target_run_id)
            if workflow_process:
                logger.info(f"✅ Found workflow process in database: {workflow_process.run_id}")
                logger.info(f"   - PID: {workflow_process.pid}")
                logger.info(f"   - Status: {workflow_process.status}")
                logger.info(f"   - Workflow: {workflow_process.workflow_name}")
                
                # Mark as terminated
                terminate_result = mark_process_terminated(target_run_id, "killed")
                logger.info(f"✅ Database termination result: {terminate_result}")
            else:
                logger.warning(f"⚠️  Workflow process {target_run_id} not found in database")
            
            # List all running processes
            running_processes = list_workflow_processes(status="running")
            logger.info(f"📊 Found {len(running_processes)} running workflow processes in database")
            
        except Exception as e:
            logger.error(f"❌ Database operations failed: {e}")
        
        # Test 4: Direct process termination by PID
        logger.info("\n📋 TEST 4: Direct process termination")
        
        # Check for long-running Claude processes (likely stuck)
        for proc_line in claude_processes:
            if 'claude' in proc_line and len(proc_line.split()) >= 2:
                try:
                    parts = proc_line.split()
                    pid = int(parts[1])
                    
                    # Check process runtime with ps
                    ps_result = subprocess.run(
                        ["ps", "-p", str(pid), "-o", "etime,pid,cmd"],
                        capture_output=True, text=True
                    )
                    
                    if ps_result.returncode == 0:
                        lines = ps_result.stdout.strip().split('\n')
                        if len(lines) > 1:
                            etime_info = lines[1].strip().split()[0]
                            logger.info(f"📊 Process {pid} runtime: {etime_info}")
                            
                            # If runtime indicates it might be stuck (more than 30 minutes)
                            if ':' in etime_info:
                                time_parts = etime_info.split(':')
                                if len(time_parts) >= 2:
                                    try:
                                        minutes = int(time_parts[-2])
                                        if minutes > 30:  # More than 30 minutes
                                            logger.warning(f"🚨 Potentially stuck process {pid} (runtime: {etime_info})")
                                            
                                            # Attempt graceful termination
                                            logger.info(f"🔄 Attempting graceful termination of PID {pid}")
                                            subprocess.run(["kill", "-TERM", str(pid)], check=False)
                                            
                                            # Wait a moment
                                            await asyncio.sleep(2)
                                            
                                            # Check if still running
                                            check_result = subprocess.run(
                                                ["ps", "-p", str(pid)], 
                                                capture_output=True, text=True
                                            )
                                            
                                            if check_result.returncode == 0:
                                                logger.warning(f"🚨 Process {pid} still running, attempting force kill")
                                                subprocess.run(["kill", "-KILL", str(pid)], check=False)
                                                
                                                await asyncio.sleep(1)
                                                
                                                # Final check
                                                final_check = subprocess.run(
                                                    ["ps", "-p", str(pid)], 
                                                    capture_output=True, text=True
                                                )
                                                
                                                if final_check.returncode != 0:
                                                    logger.info(f"✅ Successfully killed stuck process {pid}")
                                                else:
                                                    logger.error(f"❌ Failed to kill process {pid}")
                                            else:
                                                logger.info(f"✅ Process {pid} terminated gracefully")
                                    except ValueError:
                                        pass
                        
                except (ValueError, IndexError):
                    continue
        
        # Final verification
        logger.info("\n🔍 FINAL VERIFICATION")
        final_result = subprocess.run(["ps", "aux"], capture_output=True, text=True)
        final_claude_processes = [line for line in final_result.stdout.split('\n') if 'claude' in line.lower() and 'grep' not in line]
        
        logger.info(f"Found {len(final_claude_processes)} Claude processes after kill operations:")
        for i, proc in enumerate(final_claude_processes):
            logger.info(f"  {i+1}. {proc.strip()}")
        
        if len(final_claude_processes) < len(claude_processes):
            logger.info(f"✅ SUCCESS: Reduced Claude processes from {len(claude_processes)} to {len(final_claude_processes)}")
        else:
            logger.warning(f"⚠️  No reduction in Claude processes")
        
        logger.info(f"\n🎯 EMERGENCY KILL TEST COMPLETED for {target_run_id}")
        
    except Exception as e:
        logger.error(f"❌ Emergency kill test failed: {e}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(test_emergency_kill())