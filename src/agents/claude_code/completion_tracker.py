"""
Completion tracking system for Claude Code workflows.

This module provides functionality to track completion of background
Claude CLI executions and update session metadata accordingly.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from src.db.repository import session as session_repo
from .log_manager import get_log_manager
from .raw_stream_processor import RawStreamProcessor

logger = logging.getLogger(__name__)


class CompletionTracker:
    """Tracks completion of Claude Code workflows and updates session metadata."""
    
    _active_trackers: Dict[str, asyncio.Task] = {}
    
    @classmethod
    async def track_completion(
        cls,
        run_id: str,
        session_id: str,
        workflow_name: str,
        max_wait_time: int = 7200  # 2 hours default
    ):
        """
        Track completion of a Claude Code workflow and update session metadata.
        
        Args:
            run_id: Unique run identifier
            session_id: Database session ID to update
            workflow_name: Name of the workflow being executed
            max_wait_time: Maximum time to wait for completion (seconds)
        """
        logger.info(f"Starting completion tracking for run {run_id}")
        
        # Cancel any existing tracker for this run
        if run_id in cls._active_trackers:
            cls._active_trackers[run_id].cancel()
        
        # Start new tracking task
        task = asyncio.create_task(
            cls._track_execution_completion(run_id, session_id, workflow_name, max_wait_time)
        )
        cls._active_trackers[run_id] = task
        
        # Return task for optional awaiting
        return task
    
    @classmethod
    async def _track_execution_completion(
        cls,
        run_id: str, 
        session_id: str,
        workflow_name: str,
        max_wait_time: int
    ):
        """Internal method to track execution completion with real-time step updates."""
        try:
            log_manager = get_log_manager()
            start_time = datetime.utcnow()
            last_processed_entries = 0
            last_metrics_update = start_time
            
            # Track real-time progress every 5 seconds
            while True:
                await asyncio.sleep(5)
                
                # Check if execution has timed out
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                if elapsed > max_wait_time:
                    logger.warning(f"Completion tracking timed out for run {run_id}")
                    await cls._update_session_status(session_id, "timeout", {
                        "error": f"Execution timed out after {max_wait_time}s",
                        "completed_at": datetime.utcnow().isoformat(),
                        "last_updated": datetime.utcnow().isoformat()
                    })
                    break
                
                # Get latest logs
                log_entries = await log_manager.get_logs(run_id, follow=False)
                
                # Check for new activity (new log entries)
                if len(log_entries) > last_processed_entries:
                    new_entries = log_entries[last_processed_entries:]
                    last_processed_entries = len(log_entries)
                    
                    # Process new entries for real-time updates
                    await cls._process_realtime_updates(session_id, new_entries)
                
                # Update metrics every 30 seconds or when significant events occur
                time_since_last_update = (datetime.utcnow() - last_metrics_update).total_seconds()
                significant_events = any(
                    entry.get("event_type") in ["claude_response", "claude_result", "execution_complete", "process_complete"]
                    for entry in log_entries[max(0, len(log_entries) - 10):]  # Check last 10 entries
                )
                
                if time_since_last_update >= 30 or significant_events:
                    # Extract current metrics (partial or complete)
                    metrics = await cls._extract_final_metrics(run_id, log_entries)
                    
                    # Update session with current progress
                    await cls._update_session_status(session_id, "running", {
                        "last_updated": datetime.utcnow().isoformat(),
                        "current_cost_usd": metrics.total_cost_usd,
                        "current_tokens": metrics.total_tokens,
                        "current_turns": metrics.total_turns,
                        "current_tool_calls": metrics.tool_calls,
                        "tools_used_so_far": metrics.tool_names_used,
                        "elapsed_seconds": int(elapsed),
                        "claude_session_id": metrics.session_id or "pending",
                        "progress_indicator": f"Turn {metrics.total_turns}, {metrics.tool_calls} tools used"
                    })
                    
                    last_metrics_update = datetime.utcnow()
                    logger.debug(f"Updated real-time progress for run {run_id}: Turn {metrics.total_turns}, Cost ${metrics.total_cost_usd:.4f}")
                
                # Check for completion
                completion_found = any(
                    entry.get("event_type") in ["execution_complete", "process_complete"]
                    for entry in log_entries
                )
                
                if completion_found:
                    logger.info(f"Completion detected for run {run_id}, processing final metrics")
                    
                    # Extract final metrics
                    metrics = await cls._extract_final_metrics(run_id, log_entries)
                    
                    # Determine final status
                    final_status = "completed" if metrics.is_success else "failed"
                    
                    # Update session with final results
                    await cls._update_session_status(session_id, final_status, {
                        "completed_at": datetime.utcnow().isoformat(),
                        "last_updated": datetime.utcnow().isoformat(),
                        "total_cost_usd": metrics.total_cost_usd,
                        "total_tokens": metrics.total_tokens,
                        "total_turns": metrics.total_turns,
                        "tool_calls": metrics.tool_calls,
                        "tool_names_used": metrics.tool_names_used,
                        "duration_ms": metrics.duration_ms,
                        "elapsed_seconds": int(elapsed),
                        "claude_session_id": metrics.session_id,
                        "final_result": metrics.final_result[:500] if metrics.final_result else "",
                        "error_message": metrics.error_message,
                        "model_used": metrics.model,
                        "mcp_servers": metrics.mcp_servers,
                        "success": metrics.is_success
                    })
                    
                    logger.info(f"Successfully updated session {session_id} with final completion metrics")
                    break
                    
        except asyncio.CancelledError:
            logger.info(f"Completion tracking cancelled for run {run_id}")
        except Exception as e:
            logger.error(f"Error tracking completion for run {run_id}: {e}")
            # Update session with error status
            try:
                await cls._update_session_status(session_id, "failed", {
                    "error": str(e),
                    "completed_at": datetime.utcnow().isoformat()
                })
            except Exception as update_error:
                logger.error(f"Failed to update session with error status: {update_error}")
        finally:
            # Clean up tracker
            if run_id in cls._active_trackers:
                del cls._active_trackers[run_id]
    
    @classmethod
    async def _extract_final_metrics(cls, run_id: str, log_entries: list) -> Any:
        """Extract final metrics from log entries using raw stream processor."""
        processor = RawStreamProcessor()
        
        # Process all Claude stream events
        for entry in log_entries:
            event_type = entry.get("event_type", "")
            data = entry.get("data", {})
            
            # Process Claude CLI stream events (use parsed events only to avoid duplication)
            if event_type.startswith("claude_stream_") and event_type not in ["claude_stream_raw"]:
                if isinstance(data, dict):
                    # Process parsed JSON events only (not raw strings)
                    processor.process_event(data)
            
            # Also process legacy claude_output events
            elif event_type == "claude_output":
                if isinstance(data, dict) and "message" in data:
                    message = data["message"]
                    if isinstance(message, str) and message.strip().startswith("{"):
                        processor.process_line(message.strip())
        
        return processor.get_metrics()
    
    @classmethod
    async def _process_realtime_updates(cls, session_id: str, new_entries: list):
        """Process new log entries for real-time step updates."""
        significant_updates = {}
        
        for entry in new_entries:
            event_type = entry.get("event_type", "")
            data = entry.get("data", {})
            timestamp = entry.get("timestamp", "")
            
            # Track significant step events
            if event_type == "claude_response":
                response_text = data.get("response_text", "")
                step_summary = response_text[:100] + "..." if len(response_text) > 100 else response_text
                significant_updates["last_step"] = {
                    "type": "claude_response",
                    "summary": step_summary,
                    "timestamp": timestamp,
                    "response_length": data.get("response_length", 0)
                }
            
            elif event_type == "claude_stream_raw":
                # Check if this is a tool use event
                raw_json = data.get("message", "")
                if '"type":"assistant"' in raw_json and '"tool_use"' in raw_json:
                    try:
                        import json
                        stream_data = json.loads(raw_json)
                        message = stream_data.get("message", {})
                        content = message.get("content", [])
                        for item in content:
                            if item.get("type") == "tool_use":
                                tool_name = item.get("name", "unknown")
                                significant_updates["last_tool"] = {
                                    "type": "tool_use",
                                    "tool_name": tool_name,
                                    "timestamp": timestamp,
                                    "summary": f"Using {tool_name} tool"
                                }
                                break
                    except json.JSONDecodeError:
                        pass
            
            elif event_type == "session_established":
                claude_session_id = data.get("claude_session_id")
                if claude_session_id:
                    significant_updates["session_established"] = {
                        "type": "session_established",
                        "claude_session_id": claude_session_id,
                        "timestamp": timestamp,
                        "summary": f"Claude session established: {claude_session_id}"
                    }
        
        # Update session with any significant updates
        if significant_updates:
            await cls._update_session_status(session_id, "running", {
                "last_activity": datetime.utcnow().isoformat(),
                "recent_steps": significant_updates
            })
    
    @classmethod
    async def _update_session_status(cls, session_id: str, status: str, additional_metadata: Dict[str, Any]):
        """Update session metadata with completion status and metrics."""
        try:
            # Get current session
            session = session_repo.get_session(session_id)
            if not session:
                logger.error(f"Session {session_id} not found for status update")
                return
            
            # Update metadata
            metadata = session.metadata or {}
            metadata.update({
                "run_status": status,
                **additional_metadata
            })
            
            session.metadata = metadata
            session_repo.update_session(session)
            
            logger.info(f"Updated session {session_id} with status {status}")
            
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
    
    @classmethod
    def cancel_tracking(cls, run_id: str):
        """Cancel completion tracking for a specific run."""
        if run_id in cls._active_trackers:
            cls._active_trackers[run_id].cancel()
            del cls._active_trackers[run_id]
            logger.info(f"Cancelled completion tracking for run {run_id}")
    
    @classmethod
    async def cleanup_all(cls):
        """Cancel all active completion trackers."""
        for run_id, task in list(cls._active_trackers.items()):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        cls._active_trackers.clear()
        logger.info("Cancelled all completion trackers")