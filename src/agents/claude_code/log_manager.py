"""Log management for Claude Code workflow executions.

This module provides centralized logging functionality for Claude CLI executions,
with real-time file streaming and unified log retrieval.

Features:
- Per-run log files with structured JSON entries
- Async file writing with thread-safe concurrent access
- Log streaming with follow support
- Execution metrics and summaries
- Automatic log directory creation
- Resource cleanup and maintenance
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, AsyncGenerator, List, Union
import aiofiles

logger = logging.getLogger(__name__)


class LogManager:
    """Manages log files for Claude Code workflow executions.

    Provides centralized log management with structured JSON entries,
    async file operations, and thread-safe concurrent access.
    """

    def __init__(self, logs_dir: str = "./logs"):
        """Initialize the log manager.

        Args:
            logs_dir: Directory to store log files (default: ./logs)
        """
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._file_locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

        logger.info(f"LogManager initialized with logs directory: {self.logs_dir}")

    def get_log_path(self, run_id: str, workflow_name: str = None, session_id: str = None) -> Path:
        """Get the log file path for a run ID.

        Args:
            run_id: Unique run identifier
            workflow_name: Name of the workflow (optional, for new naming convention)
            session_id: Claude session ID (optional, for new naming convention)

        Returns:
            Path to the log file in format: ./logs/workflowname_sessionid.log if both provided,
            otherwise ./logs/run_{run_id}.log
        """
        if workflow_name and session_id:
            return self.logs_dir / f"{workflow_name}_{session_id}.log"
        else:
            return self.logs_dir / f"run_{run_id}.log"

    async def _get_file_lock(self, run_id: str) -> asyncio.Lock:
        """Get or create a file-specific lock for thread-safe operations.

        Args:
            run_id: Unique run identifier

        Returns:
            Lock specific to this run_id
        """
        async with self._global_lock:
            if run_id not in self._file_locks:
                self._file_locks[run_id] = asyncio.Lock()
            return self._file_locks[run_id]

    async def log_event(self, run_id: str, event_type: str, data: Any, workflow_name: str = None, session_id: str = None) -> None:
        """Write a structured log event to the run's log file.

        Args:
            run_id: Unique run identifier
            event_type: Type of event (execution_init, session_established, etc.)
            data: Event data (can be string, dict, or any JSON-serializable type)
            workflow_name: Name of the workflow (optional, for proper log file naming)
            session_id: Claude session ID (optional, for proper log file naming)
        """
        file_lock = await self._get_file_lock(run_id)

        async with file_lock:
            log_path = self.get_log_path(run_id, workflow_name, session_id)

            # Create log entry in enhanced format
            log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "run_id": run_id,
                "event_type": event_type,
                "event_category": self._get_event_category(event_type),
                "data": data,
            }

            try:
                async with aiofiles.open(log_path, "a", encoding="utf-8") as f:
                    await f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                    await f.flush()

                # Use logger.debug instead of logger.info to prevent stdout contamination
                # Never use print() or write to stdout/stderr in log manager
                logger.debug(f"Logged event '{event_type}' for run {run_id}")

            except Exception as e:
                # Log errors to logger, never to stdout
                logger.error(f"Failed to write log entry for run {run_id}: {e}")
                # Don't raise - prevent log errors from affecting API responses
                # raise
    
    def _get_event_category(self, event_type: str) -> str:
        """Categorize event types for better log analysis.
        
        Args:
            event_type: The event type string
            
        Returns:
            Category name for grouping similar events
        """
        # Map event types to categories
        category_map = {
            "execution_init": "lifecycle",
            "command_debug": "debug",
            "process_start": "lifecycle",
            "session_established": "session",
            "response_event": "claude",
            "execution_complete": "lifecycle", 
            "process_complete": "lifecycle",
            "error": "error",
            "stderr_event": "error",
            "stderr_summary": "error",
            "timeout": "error"
        }
        
        return category_map.get(event_type, "other")

    async def get_logs(
        self, run_id: str, follow: bool = False
    ) -> Union[List[Dict[str, Any]], AsyncGenerator[Dict[str, Any], None]]:
        """Get logs for a specific run with optional streaming.

        Args:
            run_id: Unique run identifier
            follow: If True, stream new entries as they arrive

        Returns:
            List of log entries if follow=False, AsyncGenerator if follow=True
        """
        if not follow:
            # Return all logs as a list
            return await self._read_all_logs(run_id)
        else:
            # Return async generator for streaming
            return self._stream_logs(run_id)

    async def _read_all_logs(self, run_id: str) -> List[Dict[str, Any]]:
        """Read all log entries for a run.

        Args:
            run_id: Unique run identifier

        Returns:
            List of parsed log entries
        """
        log_path = self.get_log_path(run_id)

        if not log_path.exists():
            logger.info(f"No log file found for run {run_id}")
            return []

        try:
            file_lock = await self._get_file_lock(run_id)
            async with file_lock:
                async with aiofiles.open(log_path, "r", encoding="utf-8") as f:
                    content = await f.read()

            logs = []
            for line in content.strip().split("\n"):
                if line.strip():
                    try:
                        entry = json.loads(line)
                        logs.append(entry)
                    except json.JSONDecodeError as e:
                        logger.warning(f"Invalid JSON in log file {log_path}: {e}")
                        # Store as raw entry
                        logs.append(
                            {
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "run_id": run_id,
                                "event_type": "raw",
                                "data": {"raw_line": line},
                            }
                        )

            return logs

        except Exception as e:
            logger.error(f"Error reading logs for {run_id}: {e}")
            return []

    async def _stream_logs(self, run_id: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Stream log entries for a run as they are written.

        Args:
            run_id: Unique run identifier

        Yields:
            Log entries as they become available
        """
        log_path = self.get_log_path(run_id)

        # First, yield existing entries
        existing_logs = await self._read_all_logs(run_id)
        for entry in existing_logs:
            yield entry

        # Then follow the file for new entries
        if log_path.exists():
            try:
                last_position = log_path.stat().st_size

                while True:
                    await asyncio.sleep(0.1)  # Poll interval

                    current_size = log_path.stat().st_size if log_path.exists() else 0

                    if current_size > last_position:
                        # New content available
                        file_lock = await self._get_file_lock(run_id)
                        async with file_lock:
                            async with aiofiles.open(
                                log_path, "r", encoding="utf-8"
                            ) as f:
                                await f.seek(last_position)
                                new_content = await f.read()

                        # Parse new lines
                        for line in new_content.strip().split("\n"):
                            if line.strip():
                                try:
                                    entry = json.loads(line)
                                    yield entry
                                except json.JSONDecodeError as e:
                                    logger.warning(
                                        f"Invalid JSON in streaming log: {e}"
                                    )
                                    yield {
                                        "timestamp": datetime.now(
                                            timezone.utc
                                        ).isoformat(),
                                        "run_id": run_id,
                                        "event_type": "raw",
                                        "data": {"raw_line": line},
                                    }

                        last_position = current_size

            except Exception as e:
                logger.error(f"Error streaming logs for {run_id}: {e}")
                yield {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "run_id": run_id,
                    "event_type": "error",
                    "data": {"error": f"Streaming error: {str(e)}"},
                }

    async def get_log_summary(self, run_id: str) -> Dict[str, Any]:
        """Get execution metrics and summary for a specific run.

        Args:
            run_id: Unique run identifier

        Returns:
            Comprehensive log summary with execution metrics
        """
        log_path = self.get_log_path(run_id)

        if not log_path.exists():
            return {
                "run_id": run_id,
                "exists": False,
                "file_size_bytes": 0,
                "total_entries": 0,
                "start_time": None,
                "end_time": None,
                "duration_seconds": None,
                "event_types": {},
                "error_count": 0,
                "last_activity": None,
            }

        try:
            # Get file stats
            stat = log_path.stat()

            # Parse all log entries
            logs = await self._read_all_logs(run_id)

            # Calculate enhanced metrics
            event_types = {}
            event_categories = {}
            error_count = 0
            start_time = None
            end_time = None

            for entry in logs:
                event_type = entry.get("event_type", "unknown")
                event_category = entry.get("event_category", "other")
                
                event_types[event_type] = event_types.get(event_type, 0) + 1
                event_categories[event_category] = event_categories.get(event_category, 0) + 1

                if event_category == "error" or event_type in ["error", "stderr_event"]:
                    error_count += 1

                timestamp = entry.get("timestamp")
                if timestamp:
                    if start_time is None or timestamp < start_time:
                        start_time = timestamp
                    if end_time is None or timestamp > end_time:
                        end_time = timestamp

            # Calculate duration
            duration_seconds = None
            if start_time and end_time:
                try:
                    start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                    end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
                    duration_seconds = (end_dt - start_dt).total_seconds()
                except ValueError:
                    logger.warning(
                        "Could not parse timestamps for duration calculation"
                    )

            return {
                "run_id": run_id,
                "exists": True,
                "file_size_bytes": stat.st_size,
                "total_entries": len(logs),
                "start_time": start_time,
                "end_time": end_time,
                "duration_seconds": duration_seconds,
                "event_types": event_types,
                "event_categories": event_categories,
                "error_count": error_count,
                "last_activity": end_time,
                "file_path": str(log_path),
                "file_modified": datetime.fromtimestamp(
                    stat.st_mtime, timezone.utc
                ).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error getting log summary for {run_id}: {e}")
            return {
                "run_id": run_id,
                "exists": True,
                "error": str(e),
                "file_path": str(log_path),
            }

    def list_all_logs(self) -> List[Dict[str, Any]]:
        """List all available log files with metadata.

        Returns:
            List of log file information including run_id, size, and timestamps
        """
        try:
            log_files = []

            for log_path in self.logs_dir.glob("run_*.log"):
                try:
                    # Extract run_id from filename (remove "run_" prefix and ".log" suffix)
                    run_id = log_path.stem[4:]
                    stat = log_path.stat()

                    log_files.append(
                        {
                            "run_id": run_id,
                            "file_path": str(log_path),
                            "file_size_bytes": stat.st_size,
                            "created": datetime.fromtimestamp(
                                stat.st_ctime, timezone.utc
                            ).isoformat(),
                            "modified": datetime.fromtimestamp(
                                stat.st_mtime, timezone.utc
                            ).isoformat(),
                        }
                    )

                except Exception as e:
                    logger.warning(f"Error processing log file {log_path}: {e}")
                    continue

            # Sort by modification time (newest first)
            log_files.sort(key=lambda x: x["modified"], reverse=True)
            return log_files

        except Exception as e:
            logger.error(f"Error listing log files: {e}")
            return []

    async def cleanup_old_logs(self, max_age_days: int = 7) -> Dict[str, Any]:
        """Clean up old log files based on age.

        Args:
            max_age_days: Maximum age of log files to keep (default: 7 days)

        Returns:
            Cleanup summary with count of deleted files and freed space
        """
        try:
            cutoff_time = time.time() - (max_age_days * 24 * 60 * 60)
            deleted_count = 0
            freed_bytes = 0
            deleted_runs = []

            for log_path in self.logs_dir.glob("run_*.log"):
                try:
                    stat = log_path.stat()

                    if stat.st_mtime < cutoff_time:
                        # Extract run_id for reporting
                        run_id = log_path.stem[4:]
                        file_size = stat.st_size

                        # Clean up associated locks
                        async with self._global_lock:
                            if run_id in self._file_locks:
                                del self._file_locks[run_id]

                        # Delete the file
                        log_path.unlink()

                        deleted_count += 1
                        freed_bytes += file_size
                        deleted_runs.append(run_id)

                        logger.info(
                            f"Deleted old log file for run {run_id} ({file_size} bytes)"
                        )

                except Exception as e:
                    logger.warning(f"Error deleting log file {log_path}: {e}")
                    continue

            return {
                "deleted_count": deleted_count,
                "freed_bytes": freed_bytes,
                "deleted_runs": deleted_runs,
                "max_age_days": max_age_days,
                "cutoff_time": datetime.fromtimestamp(
                    cutoff_time, timezone.utc
                ).isoformat(),
            }

        except Exception as e:
            logger.error(f"Error cleaning up old logs: {e}")
            return {
                "deleted_count": 0,
                "freed_bytes": 0,
                "deleted_runs": [],
                "error": str(e),
            }

    async def close(self) -> None:
        """Clean up resources and close any open file handles.

        Should be called when shutting down the LogManager.
        """
        try:
            async with self._global_lock:
                # Clear all file locks
                self._file_locks.clear()
                logger.info("LogManager resources cleaned up")

        except Exception as e:
            logger.error(f"Error during LogManager cleanup: {e}")
    
    @asynccontextmanager
    async def get_log_writer(self, run_id: str, workflow_name: str = None, session_id: str = None):
        """Get a log writer function as a context manager.
        
        Args:
            run_id: Unique run identifier
            workflow_name: Name of the workflow (optional, for proper log file naming)
            session_id: Claude session ID (optional, for proper log file naming)
            
        Yields:
            Log writer function that accepts (message, event_type, metadata=None)
        """
        async def log_writer(message: str, event_type: str = "log", metadata: Optional[Dict[str, Any]] = None):
            """Write a log entry for the run.
            
            Args:
                message: Log message
                event_type: Type of log event
                metadata: Optional metadata dictionary
            """
            log_data = {"message": message}
            if metadata:
                # Sanitize metadata to ensure JSON serializability
                try:
                    # Test serialization and filter out large content
                    sanitized_metadata = {}
                    for key, value in metadata.items():
                        # Skip very large values to reduce log bloat
                        if isinstance(value, str) and len(value) > 2000:
                            sanitized_metadata[key] = f"<large_content:{len(value)}_chars>"
                        elif isinstance(value, list) and len(str(value)) > 2000:
                            sanitized_metadata[key] = f"<large_list:{len(value)}_items>"
                        else:
                            sanitized_metadata[key] = value
                    
                    # Test serialization
                    json.dumps(sanitized_metadata)
                    log_data.update(sanitized_metadata)
                except (TypeError, ValueError) as e:
                    # If metadata is not serializable, log the error and continue with just the message
                    logger.warning(f"Metadata not JSON serializable for event_type '{event_type}': {e}")
                    log_data["metadata_error"] = f"Non-serializable metadata: {type(metadata)}"
            await self.log_event(run_id, event_type, log_data, workflow_name, session_id)
        
        try:
            # Skip redundant init event - will be logged by execution_init
            yield log_writer
        finally:
            # Optional cleanup could go here
            pass

    def __del__(self):
        """Destructor to ensure cleanup."""
        # Note: Can't use async in __del__, so this is best effort
        if hasattr(self, "_file_locks"):
            self._file_locks.clear()


# Global log manager instance
_log_manager: Optional[LogManager] = None


def get_log_manager(logs_dir: str = "./logs") -> LogManager:
    """Get the global log manager instance.

    Args:
        logs_dir: Directory to store log files (only used on first call)

    Returns:
        LogManager instance
    """
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager(logs_dir=logs_dir)
        logger.info(f"Created global LogManager instance with logs_dir: {logs_dir}")
    return _log_manager


def reset_log_manager() -> None:
    """Reset the global log manager instance.

    Useful for testing or reconfiguration.
    """
    global _log_manager
    if _log_manager is not None:
        # Best effort cleanup (can't await in sync function)
        logger.info("Resetting global LogManager instance")
    _log_manager = None


# Convenience functions for common operations
async def log_workflow_init(
    run_id: str, workflow_name: str, config: Dict[str, Any]
) -> None:
    """Log workflow initialization.

    Args:
        run_id: Unique run identifier
        workflow_name: Name of the workflow being executed
        config: Workflow configuration
    """
    manager = get_log_manager()
    await manager.log_event(
        run_id,
        "init",
        {"workflow_name": workflow_name, "config": config, "status": "starting"},
    )


async def log_workflow_progress(run_id: str, step: str, details: Any) -> None:
    """Log workflow progress.

    Args:
        run_id: Unique run identifier
        step: Current workflow step
        details: Progress details
    """
    manager = get_log_manager()
    await manager.log_event(run_id, "progress", {"step": step, "details": details})


async def log_workflow_completion(
    run_id: str, result: Any, execution_time: float
) -> None:
    """Log workflow completion.

    Args:
        run_id: Unique run identifier
        result: Workflow result
        execution_time: Total execution time in seconds
    """
    manager = get_log_manager()
    await manager.log_event(
        run_id,
        "completion",
        {
            "result": result,
            "execution_time_seconds": execution_time,
            "status": "completed",
        },
    )


async def log_workflow_error(
    run_id: str, error: str, error_type: str = "execution_error"
) -> None:
    """Log workflow error.

    Args:
        run_id: Unique run identifier
        error: Error message or details
        error_type: Type of error
    """
    manager = get_log_manager()
    await manager.log_event(
        run_id, "error", {"error": error, "error_type": error_type, "status": "failed"}
    )
