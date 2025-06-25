"""Workflow monitoring for Flashinho Pro agent."""

import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict

from .models import WorkflowStatus

logger = logging.getLogger(__name__)


class WorkflowMonitor:
    """Monitor and track workflow executions."""
    
    def __init__(self):
        self._active_workflows: Dict[str, WorkflowStatus] = {}
        self._completed_workflows: List[WorkflowStatus] = []
        self._workflow_stats = defaultdict(lambda: {"total": 0, "successful": 0, "failed": 0, "total_duration": 0.0})
        self._lock = asyncio.Lock()
        
    async def start_workflow(self, workflow_id: str, user_id: str, subject: Optional[str] = None) -> WorkflowStatus:
        """Start tracking a new workflow."""
        async with self._lock:
            workflow = WorkflowStatus(
                workflow_id=workflow_id,
                status="started",
                started_at=datetime.utcnow().isoformat()
            )
            self._active_workflows[workflow_id] = workflow
            
            logger.info(f"Started tracking workflow {workflow_id} for user {user_id} (subject: {subject})")
            
            # Start timeout monitor
            asyncio.create_task(self._monitor_workflow_timeout(workflow_id))
            
            return workflow
    
    async def update_workflow(self, workflow_id: str, status: str, **kwargs) -> Optional[WorkflowStatus]:
        """Update workflow status."""
        async with self._lock:
            if workflow_id not in self._active_workflows:
                logger.warning(f"Workflow {workflow_id} not found in active workflows")
                return None
                
            workflow = self._active_workflows[workflow_id]
            workflow.status = status
            
            # Update additional fields
            for key, value in kwargs.items():
                if hasattr(workflow, key):
                    setattr(workflow, key, value)
                    
            if status in ["completed", "failed"]:
                workflow.completed_at = datetime.utcnow().isoformat()
                
                # Calculate duration if not provided
                if not workflow.duration_seconds:
                    start_time = datetime.fromisoformat(workflow.started_at)
                    end_time = datetime.fromisoformat(workflow.completed_at)
                    workflow.duration_seconds = (end_time - start_time).total_seconds()
                
                # Move to completed list
                self._completed_workflows.append(workflow)
                del self._active_workflows[workflow_id]
                
                # Update stats
                self._update_stats(workflow)
                
                logger.info(f"Workflow {workflow_id} {status} in {workflow.duration_seconds:.2f}s")
            
            return workflow
    
    async def _monitor_workflow_timeout(self, workflow_id: str, timeout_seconds: float = 300):
        """Monitor workflow for timeout."""
        await asyncio.sleep(timeout_seconds)
        
        async with self._lock:
            if workflow_id in self._active_workflows:
                workflow = self._active_workflows[workflow_id]
                if workflow.status not in ["completed", "failed"]:
                    logger.warning(f"Workflow {workflow_id} timed out after {timeout_seconds}s")
                    workflow.status = "failed"
                    workflow.error = f"Workflow timed out after {timeout_seconds} seconds"
                    workflow.completed_at = datetime.utcnow().isoformat()
                    workflow.duration_seconds = timeout_seconds
                    
                    # Move to completed list
                    self._completed_workflows.append(workflow)
                    del self._active_workflows[workflow_id]
                    
                    # Update stats
                    self._update_stats(workflow)
    
    def _update_stats(self, workflow: WorkflowStatus):
        """Update workflow statistics."""
        stats = self._workflow_stats["all"]
        stats["total"] += 1
        
        if workflow.status == "completed":
            stats["successful"] += 1
        else:
            stats["failed"] += 1
            
        if workflow.duration_seconds:
            stats["total_duration"] += workflow.duration_seconds
            
    async def get_active_workflows(self) -> List[WorkflowStatus]:
        """Get all active workflows."""
        async with self._lock:
            return list(self._active_workflows.values())
    
    async def get_workflow_stats(self) -> Dict[str, any]:
        """Get workflow statistics."""
        async with self._lock:
            stats = dict(self._workflow_stats["all"])
            
            if stats["total"] > 0:
                stats["average_duration"] = stats["total_duration"] / stats["total"]
                stats["success_rate"] = stats["successful"] / stats["total"]
            else:
                stats["average_duration"] = 0.0
                stats["success_rate"] = 0.0
                
            stats["active_count"] = len(self._active_workflows)
            stats["completed_count"] = len(self._completed_workflows)
            
            return stats
    
    async def get_recent_workflows(self, limit: int = 10) -> List[WorkflowStatus]:
        """Get recent completed workflows."""
        async with self._lock:
            return self._completed_workflows[-limit:]
    
    async def cleanup_old_workflows(self, days: int = 7):
        """Clean up old completed workflows."""
        async with self._lock:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            self._completed_workflows = [
                w for w in self._completed_workflows
                if datetime.fromisoformat(w.completed_at or w.started_at) > cutoff_date
            ]
            
            logger.info(f"Cleaned up workflows older than {days} days, {len(self._completed_workflows)} remaining")


# Global workflow monitor instance
workflow_monitor = WorkflowMonitor()


# Convenience functions
async def track_workflow(workflow_id: str, user_id: str, subject: Optional[str] = None):
    """Start tracking a workflow execution."""
    return await workflow_monitor.start_workflow(workflow_id, user_id, subject)


async def update_workflow_status(workflow_id: str, status: str, **kwargs):
    """Update workflow status."""
    return await workflow_monitor.update_workflow(workflow_id, status, **kwargs)


async def get_workflow_stats():
    """Get workflow statistics."""
    return await workflow_monitor.get_workflow_stats()


async def log_workflow_summary():
    """Log a summary of workflow statistics."""
    stats = await get_workflow_stats()
    
    logger.info(f"Workflow Summary: "
               f"Total={stats['total']}, "
               f"Success={stats['successful']}, "
               f"Failed={stats['failed']}, "
               f"Active={stats['active_count']}, "
               f"Avg Duration={stats['average_duration']:.2f}s, "
               f"Success Rate={stats['success_rate']:.1%}")