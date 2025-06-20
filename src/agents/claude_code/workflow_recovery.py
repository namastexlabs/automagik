"""Workflow state recovery system for handling stuck or failed workflows.

This module provides mechanisms to detect, diagnose, and recover workflows
that get stuck due to TaskGroup conflicts or other issues.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum

from ...db.repository.workflow_run import (
    list_workflow_runs, 
    get_workflow_run_by_run_id,
    update_workflow_run_by_run_id
)
from ...db.models import WorkflowRunUpdate
from .workflow_queue import get_queue_manager, WorkflowPriority
from .models import ClaudeCodeRunRequest

logger = logging.getLogger(__name__)


class RecoveryAction(Enum):
    """Recovery actions for stuck workflows."""
    RETRY = "retry"  # Retry the workflow
    MARK_FAILED = "mark_failed"  # Mark as failed
    CLEANUP = "cleanup"  # Cleanup resources
    INVESTIGATE = "investigate"  # Needs manual investigation
    IGNORE = "ignore"  # No action needed


class WorkflowRecoveryService:
    """Service for detecting and recovering stuck workflows."""
    
    def __init__(self):
        """Initialize the recovery service."""
        self.recovery_stats = {
            "workflows_checked": 0,
            "workflows_recovered": 0,
            "workflows_failed": 0,
            "last_check": None
        }
        self._running = False
        self._check_interval = 300  # 5 minutes
        self._task = None
        
    async def start(self):
        """Start the recovery service."""
        if self._running:
            logger.warning("Recovery service already running")
            return
            
        self._running = True
        self._task = asyncio.create_task(self._recovery_loop())
        logger.info("Workflow recovery service started")
        
    async def stop(self):
        """Stop the recovery service."""
        self._running = False
        if self._task:
            await self._task
        logger.info("Workflow recovery service stopped")
        
    async def _recovery_loop(self):
        """Main recovery loop that runs periodically."""
        while self._running:
            try:
                await self.check_and_recover_workflows()
                await asyncio.sleep(self._check_interval)
            except Exception as e:
                logger.error(f"Recovery loop error: {e}")
                await asyncio.sleep(60)  # Wait before retry
                
    async def check_and_recover_workflows(self):
        """Check for stuck workflows and attempt recovery."""
        logger.info("Starting workflow recovery check")
        self.recovery_stats["last_check"] = datetime.utcnow()
        
        # Find potentially stuck workflows
        stuck_workflows = await self._find_stuck_workflows()
        
        logger.info(f"Found {len(stuck_workflows)} potentially stuck workflows")
        self.recovery_stats["workflows_checked"] += len(stuck_workflows)
        
        # Process each stuck workflow
        for workflow in stuck_workflows:
            try:
                action = await self._diagnose_workflow(workflow)
                await self._apply_recovery_action(workflow, action)
            except Exception as e:
                logger.error(f"Failed to recover workflow {workflow.run_id}: {e}")
                
    async def _find_stuck_workflows(self) -> List[Any]:
        """Find workflows that might be stuck."""
        stuck_workflows = []
        
        # Check running workflows that haven't updated in a while
        running_workflows, _ = list_workflow_runs(
            filters={"status": "running"},
            page_size=100
        )
        
        current_time = datetime.utcnow()
        for workflow in running_workflows:
            # Check if workflow has been running for too long without updates
            last_update = getattr(workflow, 'updated_at', None) or workflow.created_at
            if last_update and (current_time - last_update) > timedelta(minutes=30):
                stuck_workflows.append(workflow)
                logger.warning(f"Workflow {workflow.run_id} stuck - no updates for 30+ minutes")
                
        # Check pending workflows that never started
        pending_workflows, _ = list_workflow_runs(
            filters={"status": "pending"},
            page_size=100
        )
        
        for workflow in pending_workflows:
            created_at = workflow.created_at
            if created_at and (current_time - created_at) > timedelta(minutes=15):
                stuck_workflows.append(workflow)
                logger.warning(f"Workflow {workflow.run_id} stuck - pending for 15+ minutes")
                
        return stuck_workflows
        
    async def _diagnose_workflow(self, workflow) -> RecoveryAction:
        """Diagnose a stuck workflow and determine recovery action."""
        run_id = workflow.run_id
        status = workflow.status
        
        # Check metadata for specific error patterns
        metadata = workflow.metadata or {}
        
        # Pattern 1: TaskGroup conflict
        if "TaskGroup" in metadata.get("error", "") or "cancel scope" in metadata.get("error", ""):
            logger.info(f"Workflow {run_id} diagnosed with TaskGroup conflict")
            return RecoveryAction.RETRY
            
        # Pattern 2: Pending too long
        if status == "pending":
            created_at = workflow.created_at
            if created_at and (datetime.utcnow() - created_at) > timedelta(hours=1):
                logger.info(f"Workflow {run_id} pending for too long")
                return RecoveryAction.MARK_FAILED
            else:
                return RecoveryAction.RETRY
                
        # Pattern 3: Running too long without progress
        if status == "running":
            # Check if workflow has any recent activity
            last_activity = metadata.get("last_activity")
            if last_activity:
                last_activity_time = datetime.fromisoformat(last_activity)
                if (datetime.utcnow() - last_activity_time) > timedelta(hours=2):
                    logger.info(f"Workflow {run_id} running without progress for 2+ hours")
                    return RecoveryAction.MARK_FAILED
                    
            # Check execution time
            duration = workflow.duration_seconds
            max_duration = metadata.get("timeout", 7200)
            if duration and duration > max_duration:
                logger.info(f"Workflow {run_id} exceeded timeout")
                return RecoveryAction.MARK_FAILED
                
        # Pattern 4: Failed phase with running status (the critical bug)
        if status == "running" and metadata.get("current_phase") == "failed":
            logger.info(f"Workflow {run_id} in failed phase but running status")
            return RecoveryAction.MARK_FAILED
            
        # Default action
        return RecoveryAction.INVESTIGATE
        
    async def _apply_recovery_action(self, workflow, action: RecoveryAction):
        """Apply the recovery action to the workflow."""
        run_id = workflow.run_id
        
        if action == RecoveryAction.RETRY:
            logger.info(f"Retrying workflow {run_id}")
            await self._retry_workflow(workflow)
            self.recovery_stats["workflows_recovered"] += 1
            
        elif action == RecoveryAction.MARK_FAILED:
            logger.info(f"Marking workflow {run_id} as failed")
            await self._mark_workflow_failed(workflow)
            self.recovery_stats["workflows_failed"] += 1
            
        elif action == RecoveryAction.CLEANUP:
            logger.info(f"Cleaning up workflow {run_id}")
            await self._cleanup_workflow(workflow)
            
        elif action == RecoveryAction.INVESTIGATE:
            logger.warning(f"Workflow {run_id} needs manual investigation")
            
    async def _retry_workflow(self, workflow):
        """Retry a stuck workflow."""
        try:
            # Update status to retry
            update_data = WorkflowRunUpdate(
                status="pending",
                error_message="Automatically retrying after recovery",
                updated_at=datetime.utcnow()
            )
            update_workflow_run_by_run_id(workflow.run_id, update_data)
            
            # Recreate request from workflow data
            metadata = workflow.metadata or {}
            request_data = metadata.get("request", {})
            
            request = ClaudeCodeRunRequest(
                message=workflow.task_input,
                workflow_name=workflow.workflow_name,
                session_id=workflow.session_id,
                run_id=workflow.run_id,
                max_turns=request_data.get("max_turns"),
                timeout=request_data.get("timeout", 7200),
                repository_url=workflow.git_repo,
                git_branch=workflow.git_branch
            )
            
            # Submit to queue with high priority
            queue_manager = get_queue_manager()
            await queue_manager.submit_workflow(
                request,
                {"session_id": workflow.session_id, "workspace": workflow.workspace_path},
                priority=WorkflowPriority.HIGH
            )
            
            logger.info(f"Successfully resubmitted workflow {workflow.run_id}")
            
        except Exception as e:
            logger.error(f"Failed to retry workflow {workflow.run_id}: {e}")
            await self._mark_workflow_failed(workflow, f"Recovery retry failed: {e}")
            
    async def _mark_workflow_failed(self, workflow, error_message: str = None):
        """Mark a workflow as failed."""
        try:
            update_data = WorkflowRunUpdate(
                status="failed",
                error_message=error_message or "Workflow stuck - marked as failed by recovery service",
                completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            update_workflow_run_by_run_id(workflow.run_id, update_data)
            logger.info(f"Marked workflow {workflow.run_id} as failed")
        except Exception as e:
            logger.error(f"Failed to mark workflow {workflow.run_id} as failed: {e}")
            
    async def _cleanup_workflow(self, workflow):
        """Cleanup resources for a workflow."""
        # TODO: Implement workspace cleanup, cancel active tasks, etc.
        pass
        
    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery service statistics."""
        return self.recovery_stats.copy()
        
    async def recover_specific_workflow(self, run_id: str) -> bool:
        """Manually trigger recovery for a specific workflow."""
        try:
            workflow = get_workflow_run_by_run_id(run_id)
            if not workflow:
                logger.error(f"Workflow {run_id} not found")
                return False
                
            action = await self._diagnose_workflow(workflow)
            await self._apply_recovery_action(workflow, action)
            return True
            
        except Exception as e:
            logger.error(f"Failed to recover workflow {run_id}: {e}")
            return False


# Global recovery service instance
_recovery_service: Optional[WorkflowRecoveryService] = None


def get_recovery_service() -> WorkflowRecoveryService:
    """Get or create the global recovery service."""
    global _recovery_service
    if _recovery_service is None:
        _recovery_service = WorkflowRecoveryService()
    return _recovery_service


async def start_recovery_service():
    """Start the global recovery service."""
    service = get_recovery_service()
    await service.start()


async def stop_recovery_service():
    """Stop the global recovery service."""
    global _recovery_service
    if _recovery_service:
        await _recovery_service.stop()
        _recovery_service = None