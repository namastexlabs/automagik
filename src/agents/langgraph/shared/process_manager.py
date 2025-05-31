"""Process Management and Liveness Detection for LangGraph orchestration.

This module provides robust process monitoring for long-running Claude agents with
liveness detection, graceful shutdown, and orchestration state integration.
"""

import asyncio
import logging
import os
import psutil
import signal
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, Set, List
import weakref

logger = logging.getLogger(__name__)

class ProcessStatus(Enum):
    """Process status enumeration."""
    RUNNING = "running"
    HUNG = "hung"
    FAILED = "failed"
    STOPPED = "stopped"
    UNKNOWN = "unknown"
    TERMINATED = "terminated"

@dataclass
class ProcessInfo:
    """Information about a monitored process."""
    session_id: uuid.UUID
    pid: int
    started_at: datetime
    last_check: datetime
    status: ProcessStatus
    check_count: int = 0
    failure_count: int = 0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class ProcessManager:
    """Process monitoring system with liveness detection and graceful shutdown."""
    
    def __init__(self):
        """Initialize process manager."""
        self.monitored_processes: Dict[uuid.UUID, ProcessInfo] = {}
        self.monitoring_tasks: Dict[uuid.UUID, asyncio.Task] = {}
        self.default_check_interval = 30
        self.default_shutdown_timeout = 5
        self.max_failure_count = 3
        self._shutdown_event = asyncio.Event()
        
        # Callbacks for process state changes
        self.state_change_callbacks = []
        
        logger.info("Process manager initialized")
    
    async def start_monitoring(
        self,
        session_id: uuid.UUID,
        pid: int,
        check_interval: int = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Start monitoring a process with liveness detection.
        
        Args:
            session_id: Session UUID for the process
            pid: Process ID to monitor
            check_interval: Seconds between liveness checks
            metadata: Additional process metadata
            
        Returns:
            True if monitoring started successfully
        """
        try:
            if check_interval is None:
                check_interval = self.default_check_interval
            
            # Verify process exists
            if not await self._check_process_exists(pid):
                logger.error(f"Process {pid} does not exist, cannot start monitoring")
                return False
            
            # Create process info
            process_info = ProcessInfo(
                session_id=session_id,
                pid=pid,
                started_at=datetime.now(),
                last_check=datetime.now(),
                status=ProcessStatus.RUNNING,
                metadata=metadata or {}
            )
            
            self.monitored_processes[session_id] = process_info
            
            # Start monitoring task
            task = asyncio.create_task(
                self._monitor_process_loop(session_id, check_interval)
            )
            self.monitoring_tasks[session_id] = task
            
            logger.info(f"Started monitoring process {pid} for session {session_id}")
            await self._notify_state_change(session_id, ProcessStatus.RUNNING)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start monitoring process {pid}: {str(e)}")
            return False
    
    async def stop_monitoring(self, session_id: uuid.UUID) -> bool:
        """Stop monitoring a process.
        
        Args:
            session_id: Session UUID to stop monitoring
            
        Returns:
            True if monitoring stopped successfully
        """
        try:
            # Cancel monitoring task
            if session_id in self.monitoring_tasks:
                task = self.monitoring_tasks[session_id]
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                del self.monitoring_tasks[session_id]
            
            # Remove from monitored processes
            if session_id in self.monitored_processes:
                process_info = self.monitored_processes[session_id]
                logger.info(f"Stopped monitoring process {process_info.pid} for session {session_id}")
                del self.monitored_processes[session_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop monitoring session {session_id}: {str(e)}")
            return False
    
    async def stop_process(
        self,
        session_id: uuid.UUID,
        force: bool = False,
        timeout: int = None
    ) -> bool:
        """Stop a monitored process gracefully or forcefully.
        
        Args:
            session_id: Session UUID of process to stop
            force: Use SIGKILL instead of SIGTERM
            timeout: Timeout for graceful shutdown
            
        Returns:
            True if process stopped successfully
        """
        try:
            if session_id not in self.monitored_processes:
                logger.warning(f"Session {session_id} not found in monitored processes")
                return False
            
            process_info = self.monitored_processes[session_id]
            pid = process_info.pid
            
            if timeout is None:
                timeout = self.default_shutdown_timeout
            
            logger.info(f"Stopping process {pid} (force={force}, timeout={timeout})")
            
            # Check if process is still alive
            if not await self._check_process_exists(pid):
                logger.info(f"Process {pid} already terminated")
                process_info.status = ProcessStatus.STOPPED
                await self._notify_state_change(session_id, ProcessStatus.STOPPED)
                return True
            
            if force:
                # Immediate force kill
                await self._kill_process(pid, signal.SIGKILL)
            else:
                # Graceful shutdown with timeout
                success = await self._graceful_shutdown(pid, timeout)
                if not success:
                    logger.warning(f"Graceful shutdown failed for {pid}, using force")
                    await self._kill_process(pid, signal.SIGKILL)
            
            # Update status
            process_info.status = ProcessStatus.STOPPED
            await self._notify_state_change(session_id, ProcessStatus.STOPPED)
            
            # Stop monitoring
            await self.stop_monitoring(session_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop process for session {session_id}: {str(e)}")
            return False
    
    async def check_process_alive(self, pid: int) -> bool:
        """Check if a process is alive and responding.
        
        Args:
            pid: Process ID to check
            
        Returns:
            True if process is alive
        """
        return await self._check_process_exists(pid)
    
    async def get_process_status(self, session_id: uuid.UUID) -> Optional[ProcessStatus]:
        """Get the current status of a monitored process.
        
        Args:
            session_id: Session UUID
            
        Returns:
            ProcessStatus if found, None otherwise
        """
        if session_id in self.monitored_processes:
            return self.monitored_processes[session_id].status
        return None
    
    async def cleanup_orphaned_processes(self) -> int:
        """Clean up orphaned processes that are no longer needed.
        
        Returns:
            Number of processes cleaned up
        """
        cleaned_count = 0
        
        try:
            # Find claude processes
            claude_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'claude' or (
                        proc.info['cmdline'] and 
                        len(proc.info['cmdline']) > 0 and 
                        'claude' in proc.info['cmdline'][0]
                    ):
                        claude_processes.append(proc.info['pid'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Check which ones are monitored
            monitored_pids = {info.pid for info in self.monitored_processes.values()}
            orphaned_pids = set(claude_processes) - monitored_pids
            
            for pid in orphaned_pids:
                try:
                    logger.info(f"Cleaning up orphaned claude process {pid}")
                    await self._kill_process(pid, signal.SIGTERM)
                    cleaned_count += 1
                except Exception as e:
                    logger.warning(f"Failed to clean up process {pid}: {str(e)}")
            
            logger.info(f"Cleaned up {cleaned_count} orphaned processes")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error during orphan cleanup: {str(e)}")
            return cleaned_count
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """Get summary of all monitored processes.
        
        Returns:
            Dictionary with monitoring statistics
        """
        total_processes = len(self.monitored_processes)
        status_counts = {}
        
        for process_info in self.monitored_processes.values():
            status = process_info.status
            status_counts[status.value] = status_counts.get(status.value, 0) + 1
        
        return {
            "total_processes": total_processes,
            "status_counts": status_counts,
            "active_monitoring_tasks": len(self.monitoring_tasks),
            "processes": [
                {
                    "session_id": str(info.session_id),
                    "pid": info.pid,
                    "status": info.status.value,
                    "started_at": info.started_at.isoformat(),
                    "last_check": info.last_check.isoformat(),
                    "check_count": info.check_count,
                    "failure_count": info.failure_count
                }
                for info in self.monitored_processes.values()
            ]
        }
    
    def add_state_change_callback(self, callback):
        """Add callback for process state changes.
        
        Args:
            callback: Async function(session_id, new_status, process_info)
        """
        self.state_change_callbacks.append(callback)
    
    async def shutdown(self):
        """Shutdown the process manager and clean up all processes."""
        logger.info("Shutting down process manager")
        
        self._shutdown_event.set()
        
        # Cancel all monitoring tasks
        for task in self.monitoring_tasks.values():
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete
        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks.values(), return_exceptions=True)
        
        # Stop all monitored processes
        for session_id in list(self.monitored_processes.keys()):
            await self.stop_process(session_id, force=False)
        
        logger.info("Process manager shutdown complete")
    
    # Private methods
    
    async def _monitor_process_loop(self, session_id: uuid.UUID, check_interval: int):
        """Main monitoring loop for a process.
        
        Args:
            session_id: Session to monitor
            check_interval: Seconds between checks
        """
        try:
            while not self._shutdown_event.is_set():
                if session_id not in self.monitored_processes:
                    break
                
                process_info = self.monitored_processes[session_id]
                
                # Perform liveness check
                is_alive = await self._check_process_exists(process_info.pid)
                process_info.last_check = datetime.now()
                process_info.check_count += 1
                
                if is_alive:
                    # Process is alive
                    if process_info.status != ProcessStatus.RUNNING:
                        process_info.status = ProcessStatus.RUNNING
                        await self._notify_state_change(session_id, ProcessStatus.RUNNING)
                    
                    process_info.failure_count = 0
                else:
                    # Process is dead
                    process_info.failure_count += 1
                    logger.warning(
                        f"Process {process_info.pid} check failed "
                        f"(attempt {process_info.failure_count}/{self.max_failure_count})"
                    )
                    
                    if process_info.failure_count >= self.max_failure_count:
                        process_info.status = ProcessStatus.FAILED
                        await self._notify_state_change(session_id, ProcessStatus.FAILED)
                        logger.error(f"Process {process_info.pid} marked as FAILED")
                        break
                    else:
                        process_info.status = ProcessStatus.UNKNOWN
                
                # Wait for next check
                await asyncio.sleep(check_interval)
                
        except asyncio.CancelledError:
            logger.info(f"Monitoring cancelled for session {session_id}")
        except Exception as e:
            logger.error(f"Error in monitoring loop for session {session_id}: {str(e)}")
            if session_id in self.monitored_processes:
                self.monitored_processes[session_id].status = ProcessStatus.UNKNOWN
    
    async def _check_process_exists(self, pid: int) -> bool:
        """Check if a process exists and is responsive.
        
        Args:
            pid: Process ID to check
            
        Returns:
            True if process exists
        """
        try:
            # Check if PID exists
            process = psutil.Process(pid)
            
            # Check if it's actually a claude process
            cmdline = process.cmdline()
            if not cmdline or 'claude' not in cmdline[0]:
                return False
            
            # Basic responsiveness check
            status = process.status()
            if status == psutil.STATUS_ZOMBIE:
                return False
            
            return True
            
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
            return False
        except Exception as e:
            logger.warning(f"Error checking process {pid}: {str(e)}")
            return False
    
    async def _graceful_shutdown(self, pid: int, timeout: int) -> bool:
        """Attempt graceful shutdown of a process.
        
        Args:
            pid: Process ID to shutdown
            timeout: Timeout in seconds
            
        Returns:
            True if graceful shutdown succeeded
        """
        try:
            # Send SIGTERM
            await self._kill_process(pid, signal.SIGTERM)
            
            # Wait for process to exit
            start_time = datetime.now()
            while (datetime.now() - start_time).total_seconds() < timeout:
                if not await self._check_process_exists(pid):
                    return True
                await asyncio.sleep(0.5)
            
            return False
            
        except Exception as e:
            logger.error(f"Error during graceful shutdown of {pid}: {str(e)}")
            return False
    
    async def _kill_process(self, pid: int, sig: int):
        """Send signal to process.
        
        Args:
            pid: Process ID
            sig: Signal to send
        """
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            # Process already dead
            pass
        except Exception as e:
            logger.error(f"Failed to send signal {sig} to process {pid}: {str(e)}")
            raise
    
    async def _notify_state_change(self, session_id: uuid.UUID, new_status: ProcessStatus):
        """Notify callbacks of process state change.
        
        Args:
            session_id: Session that changed
            new_status: New process status
        """
        if session_id in self.monitored_processes:
            process_info = self.monitored_processes[session_id]
            
            for callback in self.state_change_callbacks:
                try:
                    await callback(session_id, new_status, process_info)
                except Exception as e:
                    logger.error(f"Error in state change callback: {str(e)}") 