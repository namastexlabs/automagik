"""Process management for Claude SDK Executor.

This module handles workflow process registration, heartbeat updates, and termination.
"""

import asyncio
import logging
import os
from typing import Dict, Any

try:
    from ...db.repository.workflow_process import (
        create_workflow_process, 
        update_heartbeat, 
        mark_process_terminated,
        get_workflow_process
    )
    from ...db.models import WorkflowProcessCreate
except ImportError:
    # Testing environment stubs
    def create_workflow_process(data):
        return True
    def update_heartbeat(run_id):
        pass
    def mark_process_terminated(run_id, status):
        pass
    def get_workflow_process(run_id):
        return None
    class WorkflowProcessCreate:
        def __init__(self, **kwargs):
            pass
from .models import ClaudeCodeRunRequest

logger = logging.getLogger(__name__)


class ProcessManager:
    """Manages workflow processes and their lifecycle."""
    
    async def register_workflow_process(
        self, 
        run_id: str, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> bool:
        """Register a new workflow process in the database.
        
        Args:
            run_id: Unique run identifier
            request: Execution request
            agent_context: Agent context
            
        Returns:
            True if registered successfully
        """
        try:
            process_data = WorkflowProcessCreate(
                run_id=run_id,
                pid=os.getpid(),
                status="running",
                workflow_name=request.workflow_name,
                session_id=agent_context.get('session_id'),
                user_id=agent_context.get('user_id'),
                workspace_path=agent_context.get('workspace', '.')
            )
            
            success = create_workflow_process(process_data)
            if success:
                logger.info(f"Registered workflow process for run_id: {run_id}, PID: {os.getpid()}")
            else:
                logger.warning(f"Failed to register workflow process for run_id: {run_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error registering workflow process: {e}")
            return False
    
    async def update_process_heartbeat(self, run_id: str) -> None:
        """Update workflow process heartbeat."""
        try:
            update_heartbeat(run_id)
        except Exception as e:
            logger.debug(f"Failed to update heartbeat for {run_id}: {e}")
    
    def create_heartbeat_task(self, run_id: str) -> asyncio.Task:
        """Create a heartbeat task for continuous health monitoring."""
        async def heartbeat_loop():
            while True:
                await asyncio.sleep(30)  # Update every 30 seconds
                
                # Check if process was killed before updating heartbeat
                try:
                    process_info = self.get_process_info(run_id)
                    if process_info and process_info.status == "killed":
                        logger.info(f"🛑 Heartbeat detected kill signal for {run_id}, stopping heartbeat")
                        break
                except Exception as kill_check_error:
                    logger.error(f"Heartbeat kill signal check failed: {kill_check_error}")
                
                await self.update_process_heartbeat(run_id)
        
        return asyncio.create_task(heartbeat_loop())
    
    async def terminate_process(self, run_id: str, status: str = "completed") -> None:
        """Mark process as terminated in the database."""
        try:
            # Update workflow_processes table
            mark_process_terminated(run_id, status=status)
            logger.info(f"Marked process {run_id} as {status}")
            
            # Clean up worktree if workflow was killed and not persistent
            if status == "killed":
                try:
                    from ...db.repository.workflow_run import get_workflow_run_by_run_id
                    workflow_run = get_workflow_run_by_run_id(run_id)
                    
                    if workflow_run and not workflow_run.workspace_persistent:
                        from .utils.worktree_cleanup import cleanup_workflow_worktree
                        cleanup_success = await cleanup_workflow_worktree(run_id)
                        if cleanup_success:
                            logger.info(f"Successfully cleaned up worktree for killed workflow {run_id}")
                        else:
                            logger.warning(f"Failed to clean up worktree for killed workflow {run_id}")
                except Exception as cleanup_error:
                    logger.error(f"Error during kill cleanup: {cleanup_error}")
            
            # CRITICAL FIX: Also update workflow_runs table for status API consistency
            try:
                from datetime import datetime
                from ...db.models import WorkflowRunUpdate
                from ...db.repository.workflow_run import update_workflow_run_by_run_id
                
                update_data = WorkflowRunUpdate(
                    status=status,
                    completed_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                update_success = update_workflow_run_by_run_id(run_id, update_data)
                if update_success:
                    logger.info(f"Updated workflow_runs table for {run_id} to {status}")
                else:
                    logger.warning(f"Failed to update workflow_runs table for {run_id}")
                    
            except Exception as workflow_update_error:
                logger.error(f"Failed to update workflow_runs table for {run_id}: {workflow_update_error}")
                
        except Exception as e:
            logger.error(f"Failed to mark process {run_id} as terminated: {e}")
    
    def get_process_info(self, run_id: str) -> Dict[str, Any]:
        """Get process information from database."""
        try:
            return get_workflow_process(run_id)
        except Exception as e:
            logger.error(f"Failed to get process info for {run_id}: {e}")
            return None
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution by marking it as terminated.
        
        Args:
            execution_id: Run ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        try:
            # Mark process as killed in database
            await self.terminate_process(execution_id, status="killed")
            logger.info(f"Cancelled execution {execution_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel execution {execution_id}: {e}")
            return False


class SDKProcessManager(ProcessManager):
    """Enhanced process manager for SDK execution with additional capabilities."""
    
    def __init__(self):
        super().__init__()
        self.active_processes = {}
    
    async def register_sdk_process(
        self, 
        run_id: str, 
        request: ClaudeCodeRunRequest, 
        agent_context: Dict[str, Any]
    ) -> bool:
        """Register SDK process with additional tracking."""
        success = await self.register_workflow_process(run_id, request, agent_context)
        if success:
            self.active_processes[run_id] = {
                "status": "running",
                "request": request,
                "context": agent_context
            }
        return success
    
    async def cancel_execution(self, execution_id: str) -> bool:
        """Enhanced cancellation with active process tracking."""
        # First try base cancellation
        success = await super().cancel_execution(execution_id)
        
        # Remove from active processes
        if execution_id in self.active_processes:
            del self.active_processes[execution_id]
            logger.info(f"Removed {execution_id} from active processes")
            success = True
        
        return success