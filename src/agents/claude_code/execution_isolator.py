"""Execution isolation for Claude SDK to prevent TaskGroup conflicts.

This module provides isolation mechanisms to run the Claude SDK in separate
contexts to avoid conflicts with FastAPI's event loop and TaskGroup management.
"""

import asyncio
import concurrent.futures
import json
import logging
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from uuid import uuid4

from .models import ClaudeCodeRunRequest
from ...db.repository.workflow_run import update_workflow_run_by_run_id
from ...db.models import WorkflowRunUpdate

logger = logging.getLogger(__name__)


class ExecutionIsolator:
    """Provides isolated execution contexts for Claude SDK to avoid TaskGroup conflicts."""
    
    def __init__(self):
        """Initialize the execution isolator."""
        self.thread_pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=10,  # Allow up to 10 concurrent isolated executions
            thread_name_prefix="claude-sdk-"
        )
        self.active_executions: Dict[str, Dict[str, Any]] = {}
        self._shutdown = False
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.shutdown()
        
    def shutdown(self):
        """Shutdown the thread pool and cleanup resources."""
        logger.info("Shutting down execution isolator...")
        self._shutdown = True
        
        # Cancel all pending futures
        for run_id, execution in self.active_executions.items():
            if execution.get("future") and not execution["future"].done():
                logger.info(f"Cancelling pending execution: {run_id}")
                execution["future"].cancel()
        
        # Shutdown thread pool with timeout handling
        try:
            # Use a timeout thread to prevent hanging
            import threading
            shutdown_complete = threading.Event()
            
            def shutdown_thread():
                try:
                    self.thread_pool.shutdown(wait=True)
                    shutdown_complete.set()
                except Exception as e:
                    logger.error(f"Thread pool shutdown error: {e}")
                    shutdown_complete.set()
            
            # Start shutdown in background thread
            shutdown_thread_obj = threading.Thread(target=shutdown_thread, daemon=True)
            shutdown_thread_obj.start()
            
            # Wait for shutdown with timeout
            if shutdown_complete.wait(timeout=2.0):
                logger.info("Thread pool shutdown completed")
            else:
                logger.warning("Thread pool shutdown timed out, forcing shutdown")
                self.thread_pool.shutdown(wait=False)
                
        except Exception as e:
            logger.error(f"Thread pool shutdown failed: {e}")
            # Force shutdown as last resort
            try:
                self.thread_pool.shutdown(wait=False)
                logger.info("Thread pool force shutdown completed")
            except Exception as force_e:
                logger.error(f"Force shutdown failed: {force_e}")
        
        # Clear active executions
        self.active_executions.clear()
        logger.info("Execution isolator shutdown completed")
        
    async def execute_in_thread_pool(
        self, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Claude SDK in a dedicated thread with isolated event loop.
        
        This method completely isolates the SDK execution from FastAPI's event loop,
        preventing TaskGroup conflicts that occur when the SDK is run in background tasks.
        
        Args:
            request: Execution request with task details
            agent_context: Agent context including session info
            
        Returns:
            Execution result dictionary
        """
        run_id = request.run_id or str(uuid4())
        logger.info(f"Isolator: Starting thread pool execution for {run_id}")
        
        # Register active execution
        self.active_executions[run_id] = {
            "status": "starting",
            "started_at": datetime.utcnow(),
            "request": request,
            "context": agent_context,
            "pid": None  # Will be set to thread/subprocess PID, not main process
        }
        
        try:
            # Execute in thread pool with new event loop
            loop = asyncio.get_running_loop()
            future = loop.run_in_executor(
                self.thread_pool,
                self._run_in_isolated_thread,
                request,
                agent_context
            )
            
            # Update status and store future for cancellation
            self.active_executions[run_id]["status"] = "running"
            self.active_executions[run_id]["future"] = future
            
            # Wait for completion with timeout
            timeout = request.timeout or 7200  # Default 2 hours
            result = await asyncio.wait_for(future, timeout=timeout)
            
            # Store subprocess PID if available
            if isinstance(result, dict) and "subprocess_pid" in result:
                self.active_executions[run_id]["pid"] = result["subprocess_pid"]
                logger.info(f"Stored subprocess PID {result['subprocess_pid']} for execution {run_id}")
                # Remove from result to avoid confusing downstream consumers
                del result["subprocess_pid"]
            
            # Update status
            self.active_executions[run_id]["status"] = "completed"
            self.active_executions[run_id]["completed_at"] = datetime.utcnow()
            
            # Update workflow process status in database
            try:
                self._update_workflow_status(run_id, "completed")
            except Exception as e:
                logger.warning(f"Could not update database status for {run_id}: {e}")
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Isolator: Execution timeout for {run_id} after {timeout}s")
            self.active_executions[run_id]["status"] = "timeout"
            
            # SURGICAL FIX: Update database immediately with timeout status
            self._update_workflow_timeout(run_id)
            
            return {
                "success": False,
                "session_id": agent_context.get("session_id"),
                "result": f"Execution timed out after {timeout} seconds",
                "exit_code": 124,  # Standard timeout exit code
                "execution_time": timeout,
                "error": "TIMEOUT",
                "run_id": run_id
            }
            
        except Exception as e:
            logger.error(f"Isolator: Thread pool execution failed for {run_id}: {e}")
            self.active_executions[run_id]["status"] = "failed"
            self.active_executions[run_id]["error"] = str(e)
            self.active_executions[run_id]["completed_at"] = datetime.utcnow()
            
            # SURGICAL FIX: Update database immediately with failure status
            self._update_workflow_failure(run_id, str(e))
            
            return {
                "success": False,
                "session_id": agent_context.get("session_id"),
                "result": f"Execution failed: {str(e)}",
                "exit_code": 1,
                "execution_time": 0,
                "error": str(e),
                "run_id": run_id
            }
            
        finally:
            # Cleanup execution record after delay
            if run_id in self.active_executions:
                # Keep record for 5 minutes for status queries
                asyncio.create_task(self._cleanup_execution_record(run_id, delay=300))
    
    def _run_in_isolated_thread(
        self,
        request: ClaudeCodeRunRequest,
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Run SDK in isolated thread with new event loop.
        
        This runs in a separate thread and creates its own event loop,
        completely isolating it from FastAPI's main event loop.
        """
        # Create new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Register current subprocess PID for cancellation
            current_pid = os.getpid()
            
            # SURGICAL FIX: Set isolation flags to prevent recursive isolation attempts
            os.environ['CLAUDE_SDK_ISOLATED'] = 'true'
            os.environ['BYPASS_TASKGROUP_DETECTION'] = 'true'  # Legacy compatibility
            os.environ['CLAUDE_SDK_NO_TASKGROUP'] = 'true'  # Force simple task in SDK
            
            # Import SDK executor here to ensure it's loaded in the thread context
            from .sdk_executor import ClaudeSDKExecutor
            
            # Create executor instance in thread context
            executor = ClaudeSDKExecutor()
            
            # SURGICAL FIX: Use a completely isolated approach to avoid any TaskGroup conflicts
            # Since even the simple execution has TaskGroup issues, try minimal execution
            logger.info("SURGICAL FIX: Using minimal isolated execution to avoid TaskGroup conflicts")
            
            try:
                result = loop.run_until_complete(
                    executor._execute_claude_task_simple(request, agent_context)
                )
                
                # Add PID to result so main thread can store it
                result["subprocess_pid"] = current_pid
            except Exception as e:
                if "TaskGroup" in str(e):
                    logger.error(f"SURGICAL ESCALATION: Even isolated execution failed with TaskGroup: {e}")
                    # Return a failure result with clear indication
                    result = {
                        'success': False,
                        'session_id': agent_context.get('session_id', 'unknown'),
                        'result': f"SURGICAL FAILURE: TaskGroup conflict in isolation: {str(e)}",
                        'exit_code': 1,
                        'execution_time': 0,
                        'error': f"TASKGROUP_ISOLATION_FAILURE: {str(e)}",
                        'run_id': request.run_id or 'unknown',
                        'cost_usd': 0.0,
                        'total_turns': 0,
                        'tools_used': [],
                        'subprocess_pid': current_pid
                    }
                else:
                    raise e
            
            return result
            
        finally:
            # Cleanup environment flags
            os.environ.pop('CLAUDE_SDK_ISOLATED', None)
            os.environ.pop('BYPASS_TASKGROUP_DETECTION', None)
            os.environ.pop('CLAUDE_SDK_NO_TASKGROUP', None)
            loop.close()
    
    async def execute_in_subprocess(
        self,
        request: ClaudeCodeRunRequest,
        agent_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Claude SDK in a completely separate subprocess.
        
        This provides the highest level of isolation by running the SDK
        in a separate Python process with its own memory space.
        
        Args:
            request: Execution request with task details
            agent_context: Agent context including session info
            
        Returns:
            Execution result dictionary
        """
        run_id = request.run_id or str(uuid4())
        logger.info(f"Isolator: Starting subprocess execution for {run_id}")
        
        # Create temporary script for subprocess execution
        script_content = self._generate_subprocess_script(request, agent_context)
        
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            delete=False,
            dir=Path.cwd()
        ) as temp_script:
            temp_script.write(script_content)
            temp_script_path = temp_script.name
        
        try:
            # Use virtual environment Python explicitly
            venv_python = Path(__file__).parent.parent.parent.parent / ".venv" / "bin" / "python"
            if not venv_python.exists():
                venv_python = sys.executable
            
            # Execute subprocess
            process = await asyncio.create_subprocess_exec(
                str(venv_python),
                temp_script_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(Path.cwd())
            )
            
            # Wait for completion with timeout
            timeout = request.timeout or 7200
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                raise
            
            # Parse result from stdout
            stdout_text = stdout.decode('utf-8')
            stderr_text = stderr.decode('utf-8')
            
            if stderr_text:
                logger.warning(f"Subprocess stderr: {stderr_text}")
            
            # Extract JSON result
            result = self._parse_subprocess_result(stdout_text)
            
            if result:
                logger.info(f"Isolator: Subprocess completed successfully for {run_id}")
                return result
            else:
                logger.error(f"Isolator: Failed to parse subprocess result for {run_id}")
                return {
                    "success": False,
                    "session_id": agent_context.get("session_id"),
                    "result": "Failed to parse subprocess result",
                    "exit_code": 1,
                    "execution_time": 0,
                    "error": "PARSE_ERROR",
                    "run_id": run_id
                }
                
        except Exception as e:
            logger.error(f"Isolator: Subprocess execution failed for {run_id}: {e}")
            return {
                "success": False,
                "session_id": agent_context.get("session_id"),
                "result": f"Subprocess execution failed: {str(e)}",
                "exit_code": 1,
                "execution_time": 0,
                "error": str(e),
                "run_id": run_id
            }
            
        finally:
            # Cleanup temp file
            try:
                os.unlink(temp_script_path)
            except (OSError, FileNotFoundError):
                pass
    
    def _generate_subprocess_script(
        self,
        request: ClaudeCodeRunRequest,
        agent_context: Dict[str, Any]
    ) -> str:
        """Generate Python script for subprocess execution."""
        request_json = json.dumps(request.model_dump())
        context_json = json.dumps(agent_context)
        project_root = str(Path.cwd())
        
        return f'''
import asyncio
import json
import sys
import os
from pathlib import Path

# Add project to path
sys.path.insert(0, r"{project_root}")

# Set environment for subprocess
os.environ["CLAUDE_SDK_SUBPROCESS"] = "true"

from src.agents.claude_code.sdk_executor import ClaudeSDKExecutor
from src.agents.claude_code.models import ClaudeCodeRunRequest

async def run_isolated():
    """Run SDK in isolated subprocess."""
    try:
        # Parse request and context
        request_data = json.loads(r"""{request_json}""")
        request = ClaudeCodeRunRequest.model_validate(request_data)
        
        context_data = json.loads(r"""{context_json}""")
        
        # Create executor and run
        executor = ClaudeSDKExecutor()
        result = await executor._execute_claude_task_simple(request, context_data)
        
        # Output result as JSON
        print("===RESULT_START===")
        print(json.dumps(result))
        print("===RESULT_END===")
        
    except Exception as e:
        import traceback
        error_result = {{
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "session_id": context_data.get("session_id"),
            "result": f"Subprocess failed: {{str(e)}}",
            "exit_code": 1,
            "execution_time": 0
        }}
        print("===RESULT_START===")
        print(json.dumps(error_result))
        print("===RESULT_END===")

if __name__ == "__main__":
    asyncio.run(run_isolated())
'''
    
    def _parse_subprocess_result(self, output: str) -> Optional[Dict[str, Any]]:
        """Parse JSON result from subprocess output."""
        try:
            # Find result markers
            start_marker = "===RESULT_START==="
            end_marker = "===RESULT_END==="
            
            start_idx = output.find(start_marker)
            end_idx = output.find(end_marker)
            
            if start_idx >= 0 and end_idx > start_idx:
                result_json = output[start_idx + len(start_marker):end_idx].strip()
                return json.loads(result_json)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to parse subprocess result: {e}")
            return None
    
    def _update_workflow_timeout(self, run_id: str):
        """Update workflow run with timeout status."""
        try:
            update_data = WorkflowRunUpdate(
                status="failed",
                error_message="Execution timed out",
                completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            update_workflow_run_by_run_id(run_id, update_data)
            logger.info(f"SURGICAL SUCCESS: Updated database with timeout status for {run_id}")
        except Exception as e:
            logger.error(f"Failed to update workflow timeout status: {e}")
    
    def _update_workflow_failure(self, run_id: str, error_message: str):
        """SURGICAL FIX: Update workflow run with immediate failure status."""
        try:
            update_data = WorkflowRunUpdate(
                status="failed",
                error_message=error_message[:500],  # Truncate long error messages
                completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            update_workflow_run_by_run_id(run_id, update_data)
            logger.info(f"SURGICAL SUCCESS: Updated database with failure status for {run_id}")
        except Exception as e:
            logger.error(f"SURGICAL ERROR: Failed to update workflow failure status: {e}")
    
    async def _cleanup_execution_record(self, run_id: str, delay: int = 300):
        """Cleanup execution record after delay."""
        await asyncio.sleep(delay)
        if run_id in self.active_executions:
            del self.active_executions[run_id]
    
    def get_execution_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get status of an active execution."""
        return self.active_executions.get(run_id)
    
    def cancel_execution(self, run_id: str) -> bool:
        """Attempt to cancel an active execution."""
        if run_id not in self.active_executions:
            return False
        
        execution = self.active_executions[run_id]
        execution["status"] = "cancelled"
        execution["cancelled_at"] = datetime.utcnow()
        
        # Actually attempt to terminate the execution
        success = False
        
        # If we have a future, try to cancel it
        if "future" in execution and execution["future"] is not None:
            future = execution["future"]
            if not future.done():
                cancelled = future.cancel()
                if cancelled:
                    logger.info(f"Successfully cancelled future for execution {run_id}")
                    success = True
                else:
                    logger.warning(f"Could not cancel future for execution {run_id} (already running)")
        
        # If we have a process ID, try to terminate the process
        if "pid" in execution and execution["pid"] is not None:
            try:
                import psutil
                import os
                import signal
                
                target_pid = execution["pid"]
                current_pid = os.getpid()
                
                # Safety check: don't kill the main server process
                if target_pid == current_pid:
                    logger.error(f"SAFETY: Refusing to kill main server process (PID: {current_pid})")
                    return success
                
                # Try to terminate the process
                try:
                    process = psutil.Process(target_pid)
                    
                    # Send SIGTERM first (graceful)
                    process.terminate()
                    logger.info(f"Sent SIGTERM to process {target_pid}")
                    
                    # Wait up to 3 seconds for graceful shutdown
                    try:
                        process.wait(timeout=3)
                        logger.info(f"Process {target_pid} terminated gracefully")
                        success = True
                    except psutil.TimeoutExpired:
                        # Force kill if graceful termination failed
                        process.kill()
                        logger.warning(f"Force killed process {target_pid}")
                        success = True
                        
                except psutil.NoSuchProcess:
                    logger.info(f"Process {target_pid} not found (already terminated)")
                    success = True
                except psutil.AccessDenied:
                    logger.error(f"Access denied when trying to terminate process {target_pid}")
                except Exception as e:
                    logger.error(f"Error terminating process {target_pid}: {e}")
                    
            except ImportError:
                logger.warning("psutil not available for process termination")
        
        logger.info(f"Marked execution {run_id} as cancelled (termination success: {success})")
        
        # Update database status
        try:
            self._update_workflow_status(run_id, "killed")
        except Exception as e:
            logger.warning(f"Could not update database status for {run_id}: {e}")
        
        return success
    
    def _update_workflow_status(self, run_id: str, status: str) -> None:
        """Update workflow status in database."""
        try:
            from src.db.repository.workflow_process import WorkflowProcessRepository
            repo = WorkflowProcessRepository()
            # Use asyncio.create_task for async database operations
            asyncio.create_task(repo.mark_process_terminated(run_id, status=status))
        except Exception as e:
            logger.error(f"Failed to update workflow status in database: {e}")
    
    def _update_workflow_timeout(self, run_id: str) -> None:
        """Update workflow with timeout status in database."""
        self._update_workflow_status(run_id, "timeout")
    
    def _update_workflow_failure(self, run_id: str, error: str) -> None:
        """Update workflow with failure status in database."""
        self._update_workflow_status(run_id, "failed")


# Global isolator instance
_isolator: Optional[ExecutionIsolator] = None


def get_isolator() -> ExecutionIsolator:
    """Get or create the global execution isolator."""
    global _isolator
    if _isolator is None:
        _isolator = ExecutionIsolator()
    return _isolator


def shutdown_isolator():
    """Shutdown the global isolator."""
    global _isolator
    if _isolator:
        _isolator.shutdown()
        _isolator = None