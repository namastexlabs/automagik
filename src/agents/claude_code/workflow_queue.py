"""Workflow queue management for concurrent execution control.

This module provides a queue-based system to manage concurrent workflow
executions and prevent resource contention.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from uuid import uuid4

from .models import ClaudeCodeRunRequest
from ...db.repository.workflow_run import update_workflow_run_by_run_id
from ...db.models import WorkflowRunUpdate

logger = logging.getLogger(__name__)


class WorkflowPriority(Enum):
    """Workflow execution priority levels."""
    CRITICAL = 0  # Highest priority
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BATCH = 4  # Lowest priority


@dataclass
class QueuedWorkflow:
    """Represents a queued workflow execution."""
    run_id: str
    request: ClaudeCodeRunRequest
    agent_context: Dict[str, Any]
    priority: WorkflowPriority = WorkflowPriority.NORMAL
    queued_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "queued"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3


class WorkflowQueueManager:
    """Manages concurrent workflow executions with queuing and prioritization."""
    
    def __init__(self, max_concurrent: int = 5):
        """Initialize the workflow queue manager.
        
        Args:
            max_concurrent: Maximum number of concurrent workflow executions
        """
        self.max_concurrent = max_concurrent
        self.queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self.active_workflows: Dict[str, QueuedWorkflow] = {}
        self.completed_workflows: Dict[str, QueuedWorkflow] = {}
        self.workers: List[asyncio.Task] = []
        self._shutdown = False
        
        # Start worker tasks
        self._start_workers()
        
    def _start_workers(self):
        """Start worker tasks to process the queue."""
        for i in range(self.max_concurrent):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)
            
    async def _worker(self, worker_id: str):
        """Worker coroutine that processes queued workflows."""
        logger.info(f"Queue worker {worker_id} started")
        
        while not self._shutdown:
            try:
                # Get next workflow from queue (blocks until available)
                queue_item = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0  # Check shutdown flag periodically
                )
                
                # Unpack the tuple (priority, timestamp, workflow)
                priority_value, timestamp, workflow = queue_item
                
                # Process the workflow
                await self._process_workflow(workflow, worker_id)
                
            except asyncio.TimeoutError:
                # Normal timeout to check shutdown flag
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                
        logger.info(f"Queue worker {worker_id} stopped")
        
    async def _process_workflow(self, workflow: QueuedWorkflow, worker_id: str):
        """Process a single workflow execution."""
        run_id = workflow.run_id
        logger.info(f"Worker {worker_id} processing workflow {run_id}")
        
        # Check if workflow was cancelled while queued
        if workflow.status == "killed":
            logger.info(f"Worker {worker_id} skipping cancelled workflow {run_id}")
            self.completed_workflows[run_id] = workflow
            return
        
        # Move to active workflows
        workflow.status = "running"
        workflow.started_at = datetime.utcnow()
        self.active_workflows[run_id] = workflow
        
        # Update database status
        await self._update_workflow_status(run_id, "running")
        
        try:
            # Execute workflow directly
            # Import executor factory to create an executor
            from .executor_factory import ExecutorFactory
            executor = ExecutorFactory.create_executor(mode="local")
            
            result = await executor.execute_claude_task(
                request=workflow.request,
                agent_context=workflow.agent_context
            )
            
            # Update workflow record
            workflow.status = "completed" if result.get("success") else "failed"
            workflow.completed_at = datetime.utcnow()
            workflow.result = result
            
            # Update database with final status
            await self._update_workflow_completion(run_id, result)
            
            logger.info(f"Worker {worker_id} completed workflow {run_id} - Success: {result.get('success')}")
            
        except Exception as e:
            logger.error(f"Worker {worker_id} failed to process workflow {run_id}: {e}")
            
            workflow.status = "failed"
            workflow.error = str(e)
            workflow.completed_at = datetime.utcnow()
            
            # Check if retry is needed
            if workflow.retry_count < workflow.max_retries:
                workflow.retry_count += 1
                workflow.status = "retry_queued"
                logger.info(f"Requeueing workflow {run_id} for retry {workflow.retry_count}/{workflow.max_retries}")
                
                # Requeue with lower priority
                await self.queue.put((
                    workflow.priority.value + 1,  # Lower priority for retries
                    -workflow.queued_at.timestamp(),
                    workflow
                ))
            else:
                # Update database with final failure
                await self._update_workflow_failure(run_id, str(e))
                
        finally:
            # Move to completed workflows
            if run_id in self.active_workflows:
                del self.active_workflows[run_id]
            self.completed_workflows[run_id] = workflow
            
            # Cleanup old completed workflows (keep last 100)
            if len(self.completed_workflows) > 100:
                oldest_ids = sorted(
                    self.completed_workflows.keys(),
                    key=lambda k: self.completed_workflows[k].completed_at or datetime.min
                )[:len(self.completed_workflows) - 100]
                
                for old_id in oldest_ids:
                    del self.completed_workflows[old_id]
    
    async def submit_workflow(
        self,
        request: ClaudeCodeRunRequest,
        agent_context: Dict[str, Any],
        priority: WorkflowPriority = WorkflowPriority.NORMAL
    ) -> str:
        """Submit a workflow for execution.
        
        Args:
            request: Workflow execution request
            agent_context: Agent context for execution
            priority: Execution priority
            
        Returns:
            run_id of the submitted workflow
        """
        run_id = request.run_id or str(uuid4())
        
        # Create queued workflow
        workflow = QueuedWorkflow(
            run_id=run_id,
            request=request,
            agent_context=agent_context,
            priority=priority
        )
        
        # Add to queue with priority and timestamp for ordering
        # Use negative timestamp to ensure FIFO within same priority
        await self.queue.put((priority.value, -workflow.queued_at.timestamp(), workflow))
        
        logger.info(f"Submitted workflow {run_id} to queue with priority {priority.name}")
        logger.info(f"Queue size: {self.queue.qsize()}, Active: {len(self.active_workflows)}")
        
        return run_id
    
    def get_workflow_status(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a workflow.
        
        Args:
            run_id: Workflow run ID
            
        Returns:
            Status dictionary or None if not found
        """
        # Check active workflows
        if run_id in self.active_workflows:
            workflow = self.active_workflows[run_id]
            return {
                "status": workflow.status,
                "queued_at": workflow.queued_at,
                "started_at": workflow.started_at,
                "priority": workflow.priority.name,
                "position": "active"
            }
        
        # Check completed workflows
        if run_id in self.completed_workflows:
            workflow = self.completed_workflows[run_id]
            return {
                "status": workflow.status,
                "queued_at": workflow.queued_at,
                "started_at": workflow.started_at,
                "completed_at": workflow.completed_at,
                "priority": workflow.priority.name,
                "position": "completed",
                "success": workflow.result.get("success") if workflow.result else False
            }
        
        # Check if still in queue
        queue_position = self._get_queue_position(run_id)
        if queue_position is not None:
            return {
                "status": "queued",
                "position": f"queue position {queue_position}",
                "queue_size": self.queue.qsize()
            }
        
        return None
    
    def _get_queue_position(self, run_id: str) -> Optional[int]:
        """Get position of workflow in queue."""
        # Note: This is a simplified implementation
        # Real implementation would need to safely iterate the queue
        return None
    
    async def _update_workflow_status(self, run_id: str, status: str):
        """Update workflow status in database."""
        try:
            update_data = WorkflowRunUpdate(
                status=status,
                updated_at=datetime.utcnow()
            )
            update_workflow_run_by_run_id(run_id, update_data)
        except Exception as e:
            logger.error(f"Failed to update workflow status: {e}")
    
    async def _update_workflow_completion(self, run_id: str, result: Dict[str, Any]):
        """Update workflow completion in database."""
        try:
            update_data = WorkflowRunUpdate(
                status="completed" if result.get("success") else "failed",
                result=result.get("result", "")[:1000],  # Truncate for database
                cost_estimate=result.get("cost_usd", 0.0),
                input_tokens=result.get("token_details", {}).get("input_tokens", 0),
                output_tokens=result.get("token_details", {}).get("output_tokens", 0),
                total_tokens=result.get("token_details", {}).get("total_tokens", 0),
                completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                duration_seconds=int(result.get("execution_time", 0))
            )
            update_workflow_run_by_run_id(run_id, update_data)
        except Exception as e:
            logger.error(f"Failed to update workflow completion: {e}")
    
    async def _update_workflow_failure(self, run_id: str, error: str):
        """Update workflow failure in database."""
        try:
            update_data = WorkflowRunUpdate(
                status="failed",
                error_message=error,
                completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            update_workflow_run_by_run_id(run_id, update_data)
        except Exception as e:
            logger.error(f"Failed to update workflow failure: {e}")
    
    async def cancel_workflow(self, run_id: str) -> bool:
        """Cancel a workflow execution.
        
        Args:
            run_id: Workflow run ID to cancel
            
        Returns:
            True if cancelled successfully
        """
        # Check if workflow is active
        if run_id in self.active_workflows:
            workflow = self.active_workflows[run_id]
            workflow.status = "killed"
            workflow.completed_at = datetime.utcnow()
            workflow.error = "Workflow cancelled by user"
            
            # Update database
            await self._update_workflow_status(run_id, "killed")
            
            # Move to completed
            del self.active_workflows[run_id]
            self.completed_workflows[run_id] = workflow
            
            logger.info(f"Cancelled active workflow {run_id}")
            return True
        
        # Check if workflow is queued
        # Note: Removing from asyncio.PriorityQueue is complex, 
        # so we'll mark it for cancellation when processed
        for i in range(self.queue.qsize()):
            try:
                priority_value, timestamp, workflow = self.queue.get_nowait()
                if workflow.run_id == run_id:
                    workflow.status = "killed"
                    workflow.error = "Workflow cancelled while queued"
                    self.completed_workflows[run_id] = workflow
                    
                    # Update database
                    await self._update_workflow_status(run_id, "killed")
                    
                    logger.info(f"Cancelled queued workflow {run_id}")
                    return True
                else:
                    # Put it back
                    self.queue.put_nowait((priority_value, timestamp, workflow))
            except asyncio.QueueEmpty:
                break
        
        # Check if already completed
        if run_id in self.completed_workflows:
            logger.info(f"Workflow {run_id} already completed, cannot cancel")
            return False
        
        logger.warning(f"Workflow {run_id} not found in queue")
        return False
    
    def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "queue_size": self.queue.qsize(),
            "active_workflows": len(self.active_workflows),
            "completed_workflows": len(self.completed_workflows),
            "max_concurrent": self.max_concurrent,
            "workers": len(self.workers)
        }
    
    async def shutdown(self):
        """Shutdown the queue manager."""
        logger.info("Shutting down workflow queue manager")
        self._shutdown = True
        
        # Wait for workers to finish
        await asyncio.gather(*self.workers, return_exceptions=True)
        
        logger.info("Workflow queue manager shutdown complete")


# Global queue manager instance
_queue_manager: Optional[WorkflowQueueManager] = None


def get_queue_manager() -> WorkflowQueueManager:
    """Get or create the global workflow queue manager."""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = WorkflowQueueManager()
    return _queue_manager


async def shutdown_queue_manager():
    """Shutdown the global queue manager."""
    global _queue_manager
    if _queue_manager:
        await _queue_manager.shutdown()
        _queue_manager = None