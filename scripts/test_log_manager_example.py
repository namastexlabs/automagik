#!/usr/bin/env python3
"""Example script demonstrating LogManager usage for Claude Code workflows.

This script shows how to integrate the LogManager into workflow executions
for proper logging and monitoring.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.claude_code.log_manager import (
    get_log_manager,
    log_workflow_init,
    log_workflow_progress, 
    log_workflow_completion,
    log_workflow_error
)


async def example_workflow_execution():
    """Example of how to use LogManager in a Claude Code workflow."""
    
    print("🚀 Starting example workflow execution with logging...")
    
    # Get the global log manager instance
    log_manager = get_log_manager("./example_logs")
    
    # Simulate a workflow run
    run_id = "example_run_20250610_224838"
    workflow_name = "bug-fixer"
    
    try:
        # 1. Initialize workflow
        await log_workflow_init(run_id, workflow_name, {
            "max_turns": 30,
            "git_branch": "feature/example-fix",
            "timeout": 3600
        })
        print("✓ Logged workflow initialization")
        
        # 2. Log various progress steps
        await log_workflow_progress(run_id, "container_setup", {
            "container_id": "claude-code-example-123",
            "image": "claude-code-agent:latest", 
            "status": "starting"
        })
        
        await log_workflow_progress(run_id, "claude_session_start", {
            "session_id": "claude_session_abc123",
            "message": "Fix the authentication bug in user login"
        })
        
        await log_workflow_progress(run_id, "code_analysis", {
            "files_analyzed": ["src/auth.py", "src/login.py"],
            "issues_found": 2
        })
        
        await log_workflow_progress(run_id, "fix_implementation", {
            "files_modified": ["src/auth.py"],
            "commits": ["abc123def456"]
        })
        
        print("✓ Logged progress steps")
        
        # 3. Complete the workflow
        await log_workflow_completion(run_id, {
            "success": True,
            "files_changed": ["src/auth.py"],
            "git_commits": ["abc123def456"],
            "tests_passed": True
        }, execution_time=1234.5)
        
        print("✓ Logged workflow completion")
        
    except Exception as e:
        # Log any errors
        await log_workflow_error(run_id, str(e), "workflow_error")
        print(f"✗ Logged workflow error: {e}")
        raise
    
    # 4. Demonstrate log reading
    print("\n📖 Reading back logged data...")
    
    # Get all logs for this run
    logs = await log_manager.get_logs(run_id)
    print(f"Total log entries: {len(logs)}")
    
    for i, entry in enumerate(logs, 1):
        print(f"  {i}. [{entry['event_type']}] {entry['timestamp']}")
        if entry['event_type'] == 'progress':
            step = entry['data'].get('step', 'unknown')
            print(f"      Step: {step}")
    
    # 5. Get execution summary
    summary = await log_manager.get_log_summary(run_id)
    print("\n📊 Execution Summary:")
    print(f"  Duration: {summary.get('duration_seconds', 0):.1f} seconds")
    print(f"  Total entries: {summary['total_entries']}")
    print(f"  Event types: {summary['event_types']}")
    print(f"  Errors: {summary['error_count']}")
    print(f"  File size: {summary['file_size_bytes']} bytes")
    
    # 6. List all available logs
    all_logs = log_manager.list_all_logs()
    print(f"\n📁 Available log files: {len(all_logs)}")
    for log_info in all_logs:
        print(f"  - {log_info['run_id']}: {log_info['file_size_bytes']} bytes")


async def example_log_streaming():
    """Example of streaming logs in real-time."""
    
    print("\n🔄 Testing log streaming functionality...")
    
    log_manager = get_log_manager()
    stream_run_id = "stream_test_run"
    
    # Start a background task to write logs
    async def write_logs():
        await asyncio.sleep(0.5)
        for i in range(5):
            await log_manager.log_event(stream_run_id, "progress", {
                "step": f"step_{i+1}",
                "message": f"Processing item {i+1}/5"
            })
            await asyncio.sleep(0.2)
        
        await log_manager.log_event(stream_run_id, "completion", {
            "status": "finished",
            "total_items": 5
        })
    
    # Stream logs in real-time
    async def stream_logs():
        count = 0
        async for entry in log_manager._stream_logs(stream_run_id):
            print(f"  Stream: [{entry['event_type']}] {entry.get('data', {})}")
            count += 1
            if count >= 6:  # Stop after receiving all expected entries
                break
    
    # Run both tasks concurrently
    await asyncio.gather(write_logs(), stream_logs())
    print("✓ Log streaming test completed")


async def main():
    """Main example function."""
    
    try:
        await example_workflow_execution()
        await example_log_streaming()
        
        # Cleanup example
        log_manager = get_log_manager()
        cleanup_result = await log_manager.cleanup_old_logs(max_age_days=0)  # Clean all for demo
        print(f"\n🧹 Cleanup: Deleted {cleanup_result['deleted_count']} files, freed {cleanup_result['freed_bytes']} bytes")
        
        await log_manager.close()
        print("\n✅ Example completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())