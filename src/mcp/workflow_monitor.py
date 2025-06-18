"""
Workflow Timeout Monitor Integration - GUARDIAN Safety Validation
 
Integrates timeout detection and monitoring with existing MCP safety triggers
to provide comprehensive workflow health monitoring and automatic kill functionality.

This module extends the existing safety infrastructure to include:
- Workflow-specific timeout detection
- Background monitoring with heartbeat tracking  
- Auto-kill functionality for stuck processes
- Integration with existing kill API and safety triggers
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .safety_triggers import SafetyTriggerSystem, TriggerType, TriggerSeverity
from ..utils.timezone import get_timezone_aware_now, format_timestamp_for_api
from ..db.repository.workflow_process import (
    get_running_processes, get_stale_processes,
    update_heartbeat, mark_process_terminated
)

logger = logging.getLogger(__name__)


class WorkflowType(Enum):
    """Workflow types with specific timeout configurations."""
    DEFAULT = "default"
    BUILDER = "builder" 
    LINA = "lina"
    BRAIN = "brain"
    # Dynamic workflow system - workflows are discovered at runtime


@dataclass
class TimeoutConfig:
    """Timeout configuration for a workflow type."""
    workflow_type: WorkflowType
    timeout_minutes: int
    warning_threshold_minutes: int
    heartbeat_interval_seconds: int
    stale_threshold_minutes: int
    auto_kill_enabled: bool


@dataclass
class WorkflowHealthStatus:
    """Health status for a running workflow."""
    run_id: str
    workflow_name: str
    status: str
    elapsed_minutes: float
    timeout_limit_minutes: int
    warning_threshold_minutes: int
    is_warning: bool
    is_timeout: bool
    is_stale: bool
    last_heartbeat: Optional[datetime]


class WorkflowMonitor:
    """
    GUARDIAN workflow timeout monitor integrating with existing safety triggers.
    
    Features:
    - Workflow-specific timeouts (default 30min, builder 60min, lina 40min, brain 40min)
    - Background monitoring task (check every 60 seconds)
    - Auto-kill functionality using existing kill API
    - Integration with existing safety trigger system
    - Heartbeat monitoring integration
    - Stale process detection (5min threshold)
    """
    
    def __init__(self, safety_trigger_system: Optional[SafetyTriggerSystem] = None):
        """Initialize the workflow monitor."""
        self.safety_triggers = safety_trigger_system or SafetyTriggerSystem()
        self.monitoring_active = False
        self.monitor_task: Optional[asyncio.Task] = None
        self.monitor_interval = 60  # Check every 60 seconds
        
        # Workflow-specific timeout configurations
        self.timeout_configs = {
            WorkflowType.DEFAULT: TimeoutConfig(
                workflow_type=WorkflowType.DEFAULT,
                timeout_minutes=30,
                warning_threshold_minutes=25,
                heartbeat_interval_seconds=60,
                stale_threshold_minutes=5,
                auto_kill_enabled=True
            ),
            WorkflowType.BUILDER: TimeoutConfig(
                workflow_type=WorkflowType.BUILDER,
                timeout_minutes=60,
                warning_threshold_minutes=50,
                heartbeat_interval_seconds=60,
                stale_threshold_minutes=5,
                auto_kill_enabled=True
            ),
            WorkflowType.LINA: TimeoutConfig(
                workflow_type=WorkflowType.LINA,
                timeout_minutes=40,
                warning_threshold_minutes=35,
                heartbeat_interval_seconds=60,
                stale_threshold_minutes=5,
                auto_kill_enabled=True
            ),
            WorkflowType.BRAIN: TimeoutConfig(
                workflow_type=WorkflowType.BRAIN,
                timeout_minutes=40,
                warning_threshold_minutes=35,
                heartbeat_interval_seconds=60,
                stale_threshold_minutes=5,
                auto_kill_enabled=True
            ),
            # Dynamic workflows use default timeout config
        }
        
        logger.info("🛡️ GUARDIAN WorkflowMonitor initialized with safety trigger integration")
    
    def get_workflow_type(self, workflow_name: str) -> WorkflowType:
        """Dynamic workflow system - all workflows use default config."""
        return WorkflowType.DEFAULT
    
    def get_timeout_config(self, workflow_name: str) -> TimeoutConfig:
        """Get timeout configuration for a specific workflow."""
        workflow_type = self.get_workflow_type(workflow_name)
        return self.timeout_configs.get(workflow_type, self.timeout_configs[WorkflowType.DEFAULT])
    
    async def start_monitoring(self):
        """Start the background monitoring task."""
        if self.monitoring_active:
            logger.warning("🛡️ Workflow monitoring is already active")
            return
        
        # Activate safety trigger system
        self.safety_triggers.activate()
        
        self.monitoring_active = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop())
        logger.info("🛡️ GUARDIAN workflow monitoring started")
    
    async def stop_monitoring(self):
        """Stop the background monitoring task."""
        self.monitoring_active = False
        
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛡️ GUARDIAN workflow monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop that runs every 60 seconds."""
        logger.info(f"🔄 Starting GUARDIAN timeout monitoring loop (interval: {self.monitor_interval}s)")
        
        while self.monitoring_active:
            try:
                await self._check_workflow_timeouts()
                await self._check_stale_processes()
                await self._update_heartbeats()
                
            except Exception as e:
                logger.error(f"❌ Error in GUARDIAN monitoring loop: {e}")
                # Continue monitoring despite errors
            
            # Wait for next check interval
            await asyncio.sleep(self.monitor_interval)
    
    async def _check_workflow_timeouts(self):
        """Check for workflows that have exceeded their timeout limits."""
        running_processes = get_running_processes()
        
        for process in running_processes:
            try:
                await self._check_process_timeout(process)
            except Exception as e:
                logger.error(f"❌ Error checking timeout for process {process.run_id}: {e}")
    
    async def _check_process_timeout(self, process):
        """Check if a specific process has timed out."""
        config = self.get_timeout_config(process.workflow_name)
        now = get_timezone_aware_now()
        
        # Calculate elapsed time
        started_at = process.started_at
        if not started_at:
            started_at = process.created_at
        
        elapsed_time = now - started_at
        elapsed_minutes = elapsed_time.total_seconds() / 60
        
        # Check for timeout
        if elapsed_minutes >= config.timeout_minutes:
            await self._handle_timeout(process, config, elapsed_minutes)
        elif elapsed_minutes >= config.warning_threshold_minutes:
            await self._handle_timeout_warning(process, config, elapsed_minutes)
    
    async def _handle_timeout(self, process, config: TimeoutConfig, elapsed_minutes: float):
        """Handle workflow timeout by triggering safety mechanism."""
        logger.warning(
            f"🚨 GUARDIAN TIMEOUT DETECTED: Workflow {process.workflow_name} (run_id: {process.run_id}) "
            f"exceeded timeout limit of {config.timeout_minutes} minutes "
            f"(elapsed: {elapsed_minutes:.1f} minutes)"
        )
        
        if not config.auto_kill_enabled:
            logger.info(f"🛡️ Auto-kill disabled for {process.workflow_name}, skipping termination")
            return
        
        try:
            # Use safety trigger system for coordinated kill
            await self.safety_triggers._trigger_safety_event(
                TriggerType.THRESHOLD_BREACH,
                TriggerSeverity.HIGH,
                f"Workflow timeout: {process.workflow_name} exceeded {config.timeout_minutes}min limit",
                {
                    "run_id": process.run_id,
                    "workflow_name": process.workflow_name,
                    "elapsed_minutes": elapsed_minutes,
                    "timeout_limit": config.timeout_minutes,
                    "trigger_source": "workflow_monitor"
                },
                rollback_required=False  # Workflow kill, not system rollback
            )
            
            # Execute kill using existing infrastructure
            kill_result = await self._auto_kill_process(process)
            
            if kill_result:
                logger.info(
                    f"✅ GUARDIAN auto-killed timed out workflow {process.workflow_name} "
                    f"(run_id: {process.run_id}) after {elapsed_minutes:.1f} minutes"
                )
                
                # Mark as terminated in database
                mark_process_terminated(process.run_id, "timeout_killed")
                
            else:
                logger.error(
                    f"❌ GUARDIAN failed to auto-kill timed out workflow {process.workflow_name} "
                    f"(run_id: {process.run_id})"
                )
                
        except Exception as e:
            logger.error(f"❌ Error in GUARDIAN timeout handling for {process.run_id}: {e}")
    
    async def _handle_timeout_warning(self, process, config: TimeoutConfig, elapsed_minutes: float):
        """Handle timeout warning (approaching timeout)."""
        remaining_minutes = config.timeout_minutes - elapsed_minutes
        
        logger.warning(
            f"⚠️ GUARDIAN TIMEOUT WARNING: Workflow {process.workflow_name} (run_id: {process.run_id}) "
            f"approaching timeout limit. {remaining_minutes:.1f} minutes remaining "
            f"(elapsed: {elapsed_minutes:.1f}/{config.timeout_minutes} minutes)"
        )
        
        # Trigger warning through safety system
        await self.safety_triggers._trigger_safety_event(
            TriggerType.THRESHOLD_BREACH,
            TriggerSeverity.MEDIUM,
            f"Workflow timeout warning: {process.workflow_name} approaching {config.timeout_minutes}min limit",
            {
                "run_id": process.run_id,
                "workflow_name": process.workflow_name,
                "elapsed_minutes": elapsed_minutes,
                "timeout_limit": config.timeout_minutes,
                "remaining_minutes": remaining_minutes,
                "trigger_source": "workflow_monitor_warning"
            },
            rollback_required=False
        )
    
    async def _auto_kill_process(self, process) -> bool:
        """Auto-kill a process using the existing kill infrastructure."""
        try:
            # Import kill executors dynamically to avoid circular imports
            from ..agents.claude_code.sdk_executor import ClaudeSDKExecutor
            from ..agents.claude_code.local_executor import LocalExecutor
            from ..agents.claude_code.cli_environment import CLIEnvironmentManager
            
            # Try SDK executor first
            env_manager = CLIEnvironmentManager()
            sdk_executor = ClaudeSDKExecutor(environment_manager=env_manager)
            kill_result = await sdk_executor.cancel_execution(process.run_id)
            
            if kill_result:
                return True
            
            # Try local executor as fallback
            local_executor = LocalExecutor()
            kill_result = await local_executor.cancel_execution(process.run_id)
            
            return kill_result
            
        except Exception as e:
            logger.error(f"❌ Error in GUARDIAN auto-kill process {process.run_id}: {e}")
            return False
    
    async def _check_stale_processes(self):
        """Check for stale processes (no heartbeat for 5+ minutes)."""
        stale_processes = get_stale_processes(max_age_minutes=5)
        
        for process in stale_processes:
            logger.warning(
                f"🔄 GUARDIAN STALE PROCESS DETECTED: {process.workflow_name} "
                f"(run_id: {process.run_id}) has no heartbeat for 5+ minutes"
            )
            
            try:
                # Check if process actually exists
                import os
                try:
                    os.kill(process.pid, 0)  # Signal 0 checks if process exists
                    # Process exists but no heartbeat - might be stuck
                    await self._handle_stale_process(process)
                except OSError:
                    # Process doesn't exist - clean up orphaned record
                    logger.info(f"🧹 GUARDIAN cleaning up orphaned process record: {process.run_id}")
                    mark_process_terminated(process.run_id, "orphaned")
                    
            except Exception as e:
                logger.error(f"❌ Error checking stale process {process.run_id}: {e}")
    
    async def _handle_stale_process(self, process):
        """Handle stale process (exists but no heartbeat)."""
        config = self.get_timeout_config(process.workflow_name)
        
        # Calculate time since last heartbeat
        now = get_timezone_aware_now()
        last_heartbeat = process.last_heartbeat or process.started_at or process.created_at
        stale_minutes = (now - last_heartbeat).total_seconds() / 60
        
        logger.warning(
            f"⚠️ GUARDIAN STALE PROCESS: {process.workflow_name} (run_id: {process.run_id}) "
            f"no heartbeat for {stale_minutes:.1f} minutes"
        )
        
        # If stale for too long, consider it stuck and kill
        if stale_minutes >= 10:  # 10 minutes without heartbeat = stuck
            logger.warning(f"🚨 GUARDIAN killing stuck process: {process.run_id}")
            
            # Trigger safety event for stale process kill
            await self.safety_triggers._trigger_safety_event(
                TriggerType.SYSTEM_HEALTH,
                TriggerSeverity.MEDIUM,
                f"Stale process kill: {process.workflow_name} stuck for {stale_minutes:.1f}min",
                {
                    "run_id": process.run_id,
                    "workflow_name": process.workflow_name,
                    "stale_minutes": stale_minutes,
                    "trigger_source": "stale_process_monitor"
                },
                rollback_required=False
            )
            
            kill_result = await self._auto_kill_process(process)
            if kill_result:
                mark_process_terminated(process.run_id, "stale_killed")
                logger.info(f"✅ GUARDIAN successfully killed stale process: {process.run_id}")
            else:
                logger.error(f"❌ GUARDIAN failed to kill stale process: {process.run_id}")
    
    async def _update_heartbeats(self):
        """Update heartbeats for active processes (if they have monitoring integration)."""
        running_count = len(get_running_processes())
        if running_count > 0:
            logger.debug(f"🛡️ GUARDIAN monitoring {running_count} running workflow processes")
    
    async def get_workflow_health_status(self) -> List[WorkflowHealthStatus]:
        """Get health status for all running workflows."""
        running_processes = get_running_processes()
        stale_processes = get_stale_processes(max_age_minutes=5)
        stale_run_ids = {p.run_id for p in stale_processes}
        
        health_statuses = []
        
        for process in running_processes:
            config = self.get_timeout_config(process.workflow_name)
            started_at = process.started_at or process.created_at
            elapsed_minutes = (get_timezone_aware_now() - started_at).total_seconds() / 60
            
            is_warning = elapsed_minutes >= config.warning_threshold_minutes
            is_timeout = elapsed_minutes >= config.timeout_minutes
            is_stale = process.run_id in stale_run_ids
            
            health_status = WorkflowHealthStatus(
                run_id=process.run_id,
                workflow_name=process.workflow_name,
                status=process.status,
                elapsed_minutes=round(elapsed_minutes, 1),
                timeout_limit_minutes=config.timeout_minutes,
                warning_threshold_minutes=config.warning_threshold_minutes,
                is_warning=is_warning,
                is_timeout=is_timeout,
                is_stale=is_stale,
                last_heartbeat=process.last_heartbeat
            )
            
            health_statuses.append(health_status)
        
        return health_statuses
    
    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status and statistics."""
        running_processes = get_running_processes()
        stale_processes = get_stale_processes(max_age_minutes=5)
        
        # Get safety trigger summary
        trigger_summary = self.safety_triggers.get_trigger_summary()
        
        # Calculate timeout warnings
        warning_processes = []
        for process in running_processes:
            config = self.get_timeout_config(process.workflow_name)
            started_at = process.started_at or process.created_at
            elapsed_minutes = (get_timezone_aware_now() - started_at).total_seconds() / 60
            
            if elapsed_minutes >= config.warning_threshold_minutes:
                warning_processes.append({
                    'run_id': process.run_id,
                    'workflow_name': process.workflow_name,
                    'elapsed_minutes': round(elapsed_minutes, 1),
                    'timeout_limit': config.timeout_minutes
                })
        
        return {
            'guardian_monitoring_active': self.monitoring_active,
            'monitor_interval_seconds': self.monitor_interval,
            'running_processes': len(running_processes),
            'stale_processes': len(stale_processes),
            'warning_processes': len(warning_processes),
            'safety_triggers': trigger_summary,
            'timeout_configs': {
                wf_type.value: {
                    'timeout_minutes': config.timeout_minutes,
                    'warning_threshold': config.warning_threshold_minutes,
                    'auto_kill_enabled': config.auto_kill_enabled
                }
                for wf_type, config in self.timeout_configs.items()
            },
            'warning_details': warning_processes,
            'stale_details': [
                {
                    'run_id': p.run_id,
                    'workflow_name': p.workflow_name,
                    'pid': p.pid,
                    'last_heartbeat': p.last_heartbeat.isoformat() if p.last_heartbeat else None
                }
                for p in stale_processes
            ]
        }
    
    async def register_workflow_startup(self, run_id: str, workflow_name: str):
        """Register a workflow startup for timeout monitoring."""
        try:
            config = self.get_timeout_config(workflow_name)
            
            logger.info(
                f"📋 GUARDIAN registered workflow for monitoring: {workflow_name} "
                f"(run_id: {run_id}, timeout: {config.timeout_minutes}min)"
            )
            
            # Update heartbeat to mark as active
            update_heartbeat(run_id)
            
        except Exception as e:
            logger.error(f"❌ Error registering workflow startup {run_id}: {e}")
    
    async def update_workflow_heartbeat(self, run_id: str):
        """Update heartbeat for an active workflow."""
        try:
            result = update_heartbeat(run_id)
            if result:
                logger.debug(f"💓 GUARDIAN updated heartbeat for workflow: {run_id}")
            else:
                logger.warning(f"⚠️ Failed to update heartbeat for workflow: {run_id}")
        except Exception as e:
            logger.error(f"❌ Error updating heartbeat for {run_id}: {e}")


# Global workflow monitor instance
_workflow_monitor: Optional[WorkflowMonitor] = None


def get_workflow_monitor() -> WorkflowMonitor:
    """Get the global workflow monitor instance."""
    global _workflow_monitor
    if _workflow_monitor is None:
        _workflow_monitor = WorkflowMonitor()
    return _workflow_monitor


async def start_workflow_monitoring():
    """Start global workflow monitoring."""
    monitor = get_workflow_monitor()
    await monitor.start_monitoring()


async def stop_workflow_monitoring():
    """Stop global workflow monitoring."""
    monitor = get_workflow_monitor()
    await monitor.stop_monitoring()


# Integration helpers for workflow startup
async def register_workflow_for_monitoring(run_id: str, workflow_name: str):
    """Register a workflow for GUARDIAN monitoring."""
    monitor = get_workflow_monitor()
    await monitor.register_workflow_startup(run_id, workflow_name)


async def update_workflow_heartbeat(run_id: str):
    """Update heartbeat for an active workflow."""
    monitor = get_workflow_monitor()
    await monitor.update_workflow_heartbeat(run_id)