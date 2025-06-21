"""Startup and shutdown hooks for Claude Code workflow services.

This module manages the lifecycle of background services like the
workflow queue manager and recovery service.
"""

import asyncio
import logging
import os
from typing import Optional

from .workflow_queue import get_queue_manager, shutdown_queue_manager
from .workflow_recovery import get_recovery_service, start_recovery_service, stop_recovery_service
from .execution_isolator import get_isolator, shutdown_isolator

logger = logging.getLogger(__name__)


class WorkflowServicesManager:
    """Manages lifecycle of workflow background services."""
    
    def __init__(self):
        """Initialize the services manager."""
        self.queue_manager = None
        self.recovery_service = None
        self.isolator = None
        self._started = False
        
    async def start(self):
        """Start all workflow services."""
        if self._started:
            logger.warning("Workflow services already started")
            return
            
        logger.info("Starting workflow services...")
        
        # Start execution isolator
        self.isolator = get_isolator()
        logger.info("✓ Execution isolator started")
        
        # Start queue manager if enabled
        if os.environ.get('USE_WORKFLOW_QUEUE', 'false').lower() == 'true':
            self.queue_manager = get_queue_manager()
            logger.info("✓ Workflow queue manager started")
        else:
            logger.info("- Workflow queue manager disabled (USE_WORKFLOW_QUEUE=false)")
        
        # Start recovery service if enabled
        if os.environ.get('ENABLE_WORKFLOW_RECOVERY', 'true').lower() == 'true':
            self.recovery_service = get_recovery_service()
            await start_recovery_service()
            logger.info("✓ Workflow recovery service started")
        else:
            logger.info("- Workflow recovery service disabled (ENABLE_WORKFLOW_RECOVERY=false)")
        
        self._started = True
        logger.info("All workflow services started successfully")
        
    async def stop(self):
        """Stop all workflow services."""
        if not self._started:
            return
            
        logger.info("Stopping workflow services...")
        
        # Stop recovery service
        if self.recovery_service:
            await stop_recovery_service()
            logger.info("✓ Workflow recovery service stopped")
        
        # Stop queue manager
        if self.queue_manager:
            await shutdown_queue_manager()
            logger.info("✓ Workflow queue manager stopped")
        
        # Stop isolator
        if self.isolator:
            shutdown_isolator()
            logger.info("✓ Execution isolator stopped")
        
        self._started = False
        logger.info("All workflow services stopped successfully")
        
    def get_status(self):
        """Get status of all services."""
        status = {
            "started": self._started,
            "isolator": "running" if self.isolator else "stopped",
            "queue_manager": None,
            "recovery_service": None
        }
        
        if self.queue_manager:
            status["queue_manager"] = self.queue_manager.get_queue_stats()
        else:
            status["queue_manager"] = "disabled"
        
        if self.recovery_service:
            status["recovery_service"] = self.recovery_service.get_recovery_stats()
        else:
            status["recovery_service"] = "disabled"
        
        return status


# Global services manager
_services_manager: Optional[WorkflowServicesManager] = None


def get_services_manager() -> WorkflowServicesManager:
    """Get or create the global services manager."""
    global _services_manager
    if _services_manager is None:
        _services_manager = WorkflowServicesManager()
    return _services_manager


async def start_workflow_services():
    """Start all workflow services."""
    manager = get_services_manager()
    await manager.start()


async def stop_workflow_services():
    """Stop all workflow services."""
    global _services_manager
    if _services_manager:
        await _services_manager.stop()
        _services_manager = None


def get_workflow_services_status():
    """Get status of workflow services."""
    manager = get_services_manager()
    return manager.get_status()


# FastAPI lifecycle hooks
async def on_startup():
    """FastAPI startup hook."""
    await start_workflow_services()


async def on_shutdown():
    """FastAPI shutdown hook."""
    await stop_workflow_services()