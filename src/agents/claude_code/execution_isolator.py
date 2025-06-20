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
        self._shutdown = True
        self.thread_pool.shutdown(wait=True)
        
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
            "context": agent_context
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
            
            # Update status
            self.active_executions[run_id]["status"] = "running"
            
            # Wait for completion with timeout
            timeout = request.timeout or 7200  # Default 2 hours
            result = await asyncio.wait_for(future, timeout=timeout)
            
            # Update status
            self.active_executions[run_id]["status"] = "completed"
            self.active_executions[run_id]["completed_at"] = datetime.utcnow()
            
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"Isolator: Execution timeout for {run_id} after {timeout}s")
            self.active_executions[run_id]["status"] = "timeout"
            
            # Update database with timeout status
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
            # Set isolation flag
            os.environ['CLAUDE_SDK_ISOLATED'] = 'true'
            
            # Import SDK executor here to ensure it's loaded in the thread context
            from .sdk_executor import ClaudeSDKExecutor
            
            # Create executor instance in thread context
            executor = ClaudeSDKExecutor()
            
            # Run the async execution in the new loop
            result = loop.run_until_complete(
                executor._execute_claude_task_simple(request, agent_context)
            )
            
            return result
            
        finally:
            # Cleanup
            os.environ.pop('CLAUDE_SDK_ISOLATED', None)
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
            # Execute subprocess
            process = await asyncio.create_subprocess_exec(
                sys.executable,
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
        except Exception as e:
            logger.error(f"Failed to update workflow timeout status: {e}")
    
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
        
        # Note: Actual thread/process cancellation is complex
        # This just marks it as cancelled in our tracking
        logger.info(f"Marked execution {run_id} as cancelled")
        
        return True


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