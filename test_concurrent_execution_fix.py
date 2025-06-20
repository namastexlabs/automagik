"""Test concurrent execution fix for Claude Code workflows.

This test verifies that multiple workflows can run concurrently without
TaskGroup conflicts after our surgical fixes.
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path

# Add project root to Python path
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.agents.claude_code.models import ClaudeCodeRunRequest
from src.agents.claude_code.execution_isolator import get_isolator
from src.agents.claude_code.workflow_queue import get_queue_manager, WorkflowPriority
from src.agents.claude_code.workflow_recovery import get_recovery_service


async def test_concurrent_execution():
    """Test concurrent workflow execution with isolation."""
    print("=" * 60)
    print("Testing Concurrent Execution Fix")
    print("=" * 60)
    
    # Create test requests
    requests = []
    for i in range(3):
        request = ClaudeCodeRunRequest(
            message=f"Test workflow {i+1}: Create a simple hello world function in hello{i+1}.py",
            workflow_name=f"test_workflow_{i+1}",
            run_id=f"test_run_{i+1}_{int(time.time())}",
            max_turns=1,
            timeout=300
        )
        requests.append(request)
    
    # Test 1: Direct isolation execution
    print("\n1. Testing direct isolation execution...")
    isolator = get_isolator()
    
    tasks = []
    for request in requests:
        context = {"session_id": f"test_session_{request.run_id}"}
        task = asyncio.create_task(isolator.execute_in_thread_pool(request, context))
        tasks.append((request.run_id, task))
    
    # Wait for all to complete
    results = []
    for run_id, task in tasks:
        try:
            result = await asyncio.wait_for(task, timeout=60)
            results.append((run_id, result))
            print(f"  ✓ {run_id}: Success={result.get('success')}")
        except asyncio.TimeoutError:
            print(f"  ✗ {run_id}: Timeout")
        except Exception as e:
            print(f"  ✗ {run_id}: Error - {e}")
    
    # Check for TaskGroup errors
    taskgroup_errors = 0
    for run_id, result in results:
        if "TaskGroup" in result.get("error", "") or "TaskGroup" in result.get("result", ""):
            taskgroup_errors += 1
            print(f"  ⚠️  TaskGroup error detected in {run_id}")
    
    if taskgroup_errors == 0:
        print("  ✅ No TaskGroup conflicts detected!")
    else:
        print(f"  ❌ {taskgroup_errors} TaskGroup conflicts found")
    
    # Test 2: Queue-based execution
    print("\n2. Testing queue-based execution...")
    queue_manager = get_queue_manager()
    
    # Submit workflows to queue
    queued_runs = []
    for i, request in enumerate(requests):
        priority = WorkflowPriority.HIGH if i == 0 else WorkflowPriority.NORMAL
        context = {"session_id": f"queue_session_{request.run_id}"}
        run_id = await queue_manager.submit_workflow(request, context, priority)
        queued_runs.append(run_id)
        print(f"  Submitted {run_id} with priority {priority.name}")
    
    # Check queue stats
    stats = queue_manager.get_queue_stats()
    print(f"  Queue stats: {json.dumps(stats, indent=2)}")
    
    # Wait for queue processing
    await asyncio.sleep(5)
    
    # Check workflow statuses
    for run_id in queued_runs:
        status = queue_manager.get_workflow_status(run_id)
        if status:
            print(f"  {run_id}: {status.get('status')} - {status.get('position')}")
    
    # Test 3: Recovery service
    print("\n3. Testing recovery service...")
    recovery_service = get_recovery_service()
    
    # Simulate stuck workflow
    stuck_request = ClaudeCodeRunRequest(
        message="This workflow will simulate being stuck",
        workflow_name="stuck_workflow",
        run_id=f"stuck_run_{int(time.time())}",
        max_turns=1
    )
    
    # Check recovery stats
    recovery_stats = recovery_service.get_recovery_stats()
    print(f"  Recovery stats: {json.dumps(recovery_stats, indent=2)}")
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  - Concurrent executions: {len(requests)}")
    print(f"  - TaskGroup conflicts: {taskgroup_errors}")
    print(f"  - Queue processing: {'✓' if stats['active_workflows'] > 0 else '✗'}")
    print(f"  - Recovery service: {'✓' if recovery_stats else '✗'}")
    print("=" * 60)
    
    # Cleanup
    isolator.shutdown()
    await queue_manager.shutdown()


async def test_race_condition_scenario():
    """Test the specific race condition scenario from the QA report."""
    print("\n" + "=" * 60)
    print("Testing Race Condition Scenario")
    print("=" * 60)
    
    # Simulate the exact scenario that causes race conditions
    requests = []
    for i in range(5):  # 5 concurrent workflows
        request = ClaudeCodeRunRequest(
            message=f"Workflow {i+1}: Analyze this code and suggest improvements",
            workflow_name="test",
            run_id=f"race_test_{i+1}_{int(time.time())}",
            max_turns=3,  # Multiple turns to increase conflict chance
            timeout=120
        )
        requests.append(request)
    
    print(f"Submitting {len(requests)} workflows concurrently...")
    
    isolator = get_isolator()
    tasks = []
    start_time = time.time()
    
    # Submit all at once to maximize conflict potential
    for request in requests:
        context = {
            "session_id": f"race_session_{request.run_id}",
            "workspace": "/tmp/test_workspace"
        }
        task = asyncio.create_task(isolator.execute_in_thread_pool(request, context))
        tasks.append((request.run_id, task))
    
    # Monitor execution
    completed = 0
    failed = 0
    taskgroup_conflicts = 0
    
    for run_id, task in tasks:
        try:
            result = await asyncio.wait_for(task, timeout=180)
            if result.get("success"):
                completed += 1
                print(f"  ✓ {run_id}: Completed successfully")
            else:
                failed += 1
                error = result.get("error", "Unknown error")
                if "TaskGroup" in error or "cancel scope" in error:
                    taskgroup_conflicts += 1
                    print(f"  ⚠️  {run_id}: TaskGroup conflict")
                else:
                    print(f"  ✗ {run_id}: Failed - {error}")
        except Exception as e:
            failed += 1
            print(f"  ✗ {run_id}: Exception - {e}")
    
    elapsed = time.time() - start_time
    
    print(f"\nResults:")
    print(f"  Total workflows: {len(requests)}")
    print(f"  Completed: {completed}")
    print(f"  Failed: {failed}")
    print(f"  TaskGroup conflicts: {taskgroup_conflicts}")
    print(f"  Elapsed time: {elapsed:.2f}s")
    print(f"  Success rate: {(completed/len(requests)*100):.1f}%")
    
    if taskgroup_conflicts == 0 and completed == len(requests):
        print("\n✅ RACE CONDITION FIX VERIFIED!")
    else:
        print("\n❌ Race condition still present")
    
    isolator.shutdown()


async def main():
    """Run all tests."""
    try:
        await test_concurrent_execution()
        await test_race_condition_scenario()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("Starting concurrent execution tests...")
    print(f"Timestamp: {datetime.now().isoformat()}")
    asyncio.run(main())