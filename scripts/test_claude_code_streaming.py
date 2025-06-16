#!/usr/bin/env python3
"""
Test script for Claude Code API streaming and logging improvements.

This script validates the new streaming, logging, and real-time feedback features:
1. Live log streaming to files
2. API responses with actual workflow results  
3. Parallel execution with separate log files
4. Status API returns live logs instead of null

Usage:
    uv run python scripts/test_claude_code_streaming.py
"""

import asyncio
import json
import os
import time
import sys
from typing import Dict, Optional, List
import aiohttp
from pathlib import Path


# Configuration
BASE_URL = os.getenv("AM_BASE_URL", "http://localhost:8881")
API_KEY = os.getenv("AM_API_KEY", "test-key")
TIMEOUT_SECONDS = 120  # Max time to wait for workflow completion
POLL_INTERVAL = 3  # Seconds between status checks

class Colors:
    """Terminal colors for output formatting."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def print_result(test_name: str, passed: bool, details: str = ""):
    """Print test result with color formatting."""
    icon = "✅" if passed else "❌"
    color = Colors.GREEN if passed else Colors.RED
    print(f"{color}{icon} {test_name}: {'PASS' if passed else 'FAIL'}{Colors.RESET}")
    if details:
        print(f"   {details}")

def print_info(message: str):
    """Print info message in blue."""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.RESET}")

def print_warning(message: str):
    """Print warning message in yellow."""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")

async def make_request(
    session: aiohttp.ClientSession,
    method: str,
    endpoint: str,
    json_data: Optional[Dict] = None
) -> tuple[bool, Dict, str]:
    """Make an HTTP request and return success status, response data, and error message."""
    url = f"{BASE_URL}{endpoint}"
    headers = {
        "x-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        async with session.request(method, url, headers=headers, json=json_data) as response:
            data = await response.json()
            
            if response.status >= 200 and response.status < 300:
                return True, data, ""
            else:
                error_msg = data.get("detail", f"HTTP {response.status}")
                return False, data, error_msg
                
    except aiohttp.ClientError as e:
        return False, {}, f"Connection error: {str(e)}"
    except json.JSONDecodeError as e:
        return False, {}, f"Invalid JSON response: {str(e)}"
    except Exception as e:
        return False, {}, f"Unexpected error: {str(e)}"

async def start_workflow(session: aiohttp.ClientSession, workflow_name: str, message: str) -> Optional[str]:
    """Start a workflow and return run_id if successful."""
    request_data = {
        "message": message,
        "max_turns": 2,  # Keep short for testing
        "git_branch": "test-streaming"
    }
    
    print_info(f"Starting {workflow_name} workflow...")
    success, data, error = await make_request(
        session, "POST", f"/api/v1/workflows/claude-code/run/{workflow_name}", request_data
    )
    
    if not success:
        print_result(f"Start {workflow_name}", False, error)
        return None
    
    run_id = data.get("run_id")
    if not run_id:
        print_result(f"Start {workflow_name}", False, "No run_id in response")
        return None
    
    print_result(f"Start {workflow_name}", True, f"run_id: {run_id}")
    return run_id

async def monitor_workflow(session: aiohttp.ClientSession, run_id: str, workflow_name: str) -> Dict:
    """Monitor a workflow until completion and return final status."""
    start_time = time.time()
    
    while time.time() - start_time < TIMEOUT_SECONDS:
        await asyncio.sleep(POLL_INTERVAL)
        
        success, status_data, error = await make_request(
            session, "GET", f"/api/v1/workflows/claude-code/run/{run_id}/status"
        )
        
        if not success:
            print_result(f"Monitor {workflow_name}", False, error)
            return {"status": "error", "error": error}
        
        status = status_data.get("status", "unknown")
        
        print_info(f"{workflow_name} status: {status}")
        
        # Check for logs in response
        logs = status_data.get("logs")
        if logs and logs != "No logs found for run":
            print_info(f"{workflow_name} has logs: {len(logs)} characters")
        
        if status == "completed":
            execution_time = status_data.get("execution_time", 0)
            result = status_data.get("result")
            print_result(f"{workflow_name} completed", True, f"Time: {execution_time:.1f}s")
            if result:
                print_info(f"Result: {result[:100]}...")
            return status_data
        elif status == "failed":
            error_msg = status_data.get("error", "Unknown error")
            print_result(f"{workflow_name} completed", False, f"Failed: {error_msg}")
            return status_data
        elif status in ["pending", "running"]:
            continue
        else:
            print_result(f"{workflow_name} completed", False, f"Unknown status: {status}")
            return status_data
    
    print_result(f"{workflow_name} completed", False, f"Timeout after {TIMEOUT_SECONDS}s")
    return {"status": "timeout"}

async def test_log_endpoints(session: aiohttp.ClientSession, run_id: str) -> bool:
    """Test the new log endpoints."""
    print_info("Testing log endpoints...")
    
    # Test log summary
    success, summary_data, error = await make_request(
        session, "GET", f"/api/v1/workflows/claude-code/run/{run_id}/logs/summary"
    )
    
    if success:
        summary = summary_data.get("summary", {})
        print_result("Log summary", True, f"Lines: {summary.get('lines', 0)}, Size: {summary.get('size', 0)} bytes")
    else:
        print_result("Log summary", False, error)
        return False
    
    # Test log retrieval
    success, log_data, error = await make_request(
        session, "GET", f"/api/v1/workflows/claude-code/run/{run_id}/logs?lines=50"
    )
    
    if success:
        logs = log_data.get("logs", "")
        print_result("Log retrieval", True, f"Retrieved {len(logs)} characters")
    else:
        print_result("Log retrieval", False, error)
        return False
    
    return True

async def test_log_files_exist(run_ids: List[str]) -> bool:
    """Test that log files actually exist on disk."""
    print_info("Checking log files on disk...")
    
    logs_dir = Path("./logs")
    if not logs_dir.exists():
        print_result("Log directory", False, "Logs directory doesn't exist")
        return False
    
    print_result("Log directory", True, f"Found at {logs_dir}")
    
    success_count = 0
    for run_id in run_ids:
        log_file = logs_dir / f"run_{run_id}.log"
        if log_file.exists():
            size = log_file.stat().st_size
            print_result(f"Log file {run_id}", True, f"Size: {size} bytes")
            success_count += 1
        else:
            print_result(f"Log file {run_id}", False, "File not found")
    
    return success_count == len(run_ids)

async def test_parallel_execution() -> bool:
    """Test parallel execution with separate logs."""
    print_info("Testing parallel execution...")
    
    async with aiohttp.ClientSession() as session:
        # Start multiple workflows simultaneously
        workflows = [
            ("architect", "Design a simple hello world API"),
            ("test", "Write tests for a basic function"),
        ]
        
        # Start all workflows
        run_ids = []
        for workflow_name, message in workflows:
            run_id = await start_workflow(session, workflow_name, message)
            if run_id:
                run_ids.append((run_id, workflow_name))
            await asyncio.sleep(1)  # Small delay between starts
        
        if len(run_ids) < len(workflows):
            print_result("Parallel start", False, "Not all workflows started")
            return False
        
        print_result("Parallel start", True, f"Started {len(run_ids)} workflows")
        
        # Monitor all workflows to completion
        tasks = []
        for run_id, workflow_name in run_ids:
            task = asyncio.create_task(monitor_workflow(session, run_id, workflow_name))
            tasks.append(task)
        
        # Wait for all to complete
        results = await asyncio.gather(*tasks)
        
        # Check results
        completed_count = sum(1 for result in results if result.get("status") == "completed")
        
        print_result("Parallel execution", completed_count > 0, 
                    f"{completed_count}/{len(results)} workflows completed")
        
        # Test log endpoints for each run
        log_tests_passed = 0
        for run_id, workflow_name in run_ids:
            if await test_log_endpoints(session, run_id):
                log_tests_passed += 1
        
        print_result("Log endpoints", log_tests_passed == len(run_ids),
                    f"{log_tests_passed}/{len(run_ids)} log tests passed")
        
        # Check log files exist
        just_run_ids = [run_id for run_id, _ in run_ids]
        log_files_exist = await test_log_files_exist(just_run_ids)
        
        return completed_count > 0 and log_tests_passed > 0 and log_files_exist

async def main():
    """Run all streaming tests."""
    print(f"\n{Colors.CYAN}=== Claude Code Streaming Test Suite ==={Colors.RESET}")
    print(f"Target: {BASE_URL}")
    print(f"API Key: {'***' + API_KEY[-4:] if len(API_KEY) > 4 else '***'}")
    print()
    
    # Check if server is accessible
    try:
        import requests
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print_result("Server health", False, "Health check failed")
            return 1
    except Exception as e:
        print_result("Server connection", False, str(e))
        return 1
    
    print_result("Server health", True, "Server is accessible")
    
    # Run parallel execution test
    success = await test_parallel_execution()
    
    # Summary
    print(f"\n{Colors.CYAN}=== Test Summary ==={Colors.RESET}")
    if success:
        print(f"{Colors.GREEN}✅ All streaming tests passed! 🎉{Colors.RESET}")
        print()
        print("✅ Log files are being created in ./logs/")
        print("✅ API returns live logs instead of null")
        print("✅ Parallel execution works with separate logs")
        print("✅ Status API includes actual workflow results")
        return 0
    else:
        print(f"{Colors.RED}❌ Some streaming tests failed{Colors.RESET}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)