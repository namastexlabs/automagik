"""
Completion tracking system for Claude Code workflows.

This module provides functionality to track completion of background
Claude CLI executions and update session metadata accordingly.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any

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
                    await cls._update_session_status(session_id, "failed", {
                        "error": f"Execution timed out after {max_wait_time}s",
                        "timeout_reason": "max_wait_time_exceeded",
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
                
                # Update metrics every 10 seconds or when significant events occur
                time_since_last_update = (datetime.utcnow() - last_metrics_update).total_seconds()
                significant_events = any(
                    entry.get("event_type") in ["claude_stream_assistant", "claude_stream_raw", "claude_result", "execution_complete", "process_complete"]
                    for entry in log_entries[max(0, len(log_entries) - 5):]  # Check last 5 entries
                )
                
                if time_since_last_update >= 10 or significant_events or len(log_entries) > last_processed_entries:
                    # Extract current metrics (partial or complete)
                    metrics = await cls._extract_final_metrics(run_id, log_entries)
                    
                    # Check for real-time SDK executor progress
                    session = session_repo.get_session(uuid.UUID(session_id))
                    execution_results = session.metadata.get("execution_results") if session and session.metadata else None
                    
                    if execution_results:
                        # Update with real-time SDK data
                        await cls._update_session_status(session_id, "running", {
                            "last_updated": datetime.utcnow().isoformat(),
                            "current_cost_usd": execution_results.get("total_cost_usd", 0.0),
                            "current_tokens": execution_results.get("token_details", {}).get("total_tokens", 0),
                            "current_turns": execution_results.get("total_turns", 0),
                            "tools_used_so_far": execution_results.get("tools_used", []),
                            "elapsed_seconds": int(elapsed),
                            "progress_indicator": f"Turn {execution_results.get('total_turns', 0)}, {len(execution_results.get('tools_used', []))} tools used"
                        })
                    else:
                        # Basic progress update without detailed metrics
                        await cls._update_session_status(session_id, "running", {
                            "last_updated": datetime.utcnow().isoformat(),
                            "elapsed_seconds": int(elapsed)
                        })
                    
                    last_metrics_update = datetime.utcnow()
                    logger.debug(f"Updated real-time progress for run {run_id}: Turn {metrics.total_turns}, Cost ${metrics.total_cost_usd:.4f}")
                
                # Check for completion - now includes SDK completion events and session updates
                completion_found = any(
                    entry.get("event_type") in ["execution_complete", "process_complete", "claude_result"]
                    for entry in log_entries
                )
                
                # Also check if session metadata indicates completion
                if not completion_found:
                    try:
                        from src.db.repository import session as session_repo
                        sessions = session_repo.list_sessions()
                        for session in sessions:
                            if (session.metadata and 
                                session.metadata.get("run_id") == run_id and
                                session.metadata.get("run_status") in ["completed", "failed"]):
                                completion_found = True
                                logger.info(f"Detected completion via session metadata for run {run_id}")
                                break
                    except Exception as e:
                        logger.debug(f"Could not check session metadata: {e}")
                
                if completion_found:
                    logger.info(f"Completion detected for run {run_id}, processing final metrics")
                    
                    # Check for SDK executor results in session metadata first
                    session = session_repo.get_session(uuid.UUID(session_id))
                    execution_results = session.metadata.get("execution_results") if session and session.metadata else None
                    
                    if execution_results:
                        # Use SDK executor results directly - this is the accurate source
                        final_status = "completed" if execution_results.get("success", False) else "failed"
                        
                        # Extract comprehensive SDK data
                        token_details = execution_results.get("token_details", {})
                        
                        await cls._update_session_status(session_id, final_status, {
                            "completed_at": datetime.utcnow().isoformat(),
                            "last_updated": datetime.utcnow().isoformat(),
                            "total_cost_usd": execution_results.get("total_cost_usd", 0.0),
                            "total_tokens": token_details.get("total_tokens", 0),
                            "input_tokens": token_details.get("input_tokens", 0),
                            "output_tokens": token_details.get("output_tokens", 0),
                            "cache_created": token_details.get("cache_created", 0),
                            "cache_read": token_details.get("cache_read", 0),
                            "total_turns": execution_results.get("total_turns", 0),
                            "tools_used": execution_results.get("tools_used", execution_results.get("tool_names_used", [])),
                            "tool_names_used": execution_results.get("tool_names_used", execution_results.get("tools_used", [])),
                            "duration_ms": execution_results.get("execution_time", 0) * 1000,
                            "elapsed_seconds": int(elapsed),
                            "final_result": execution_results.get("result", ""),
                            "success": execution_results.get("success", False)
                        })
                        logger.info(f"Updated session {session_id} with SDK executor results")
                    else:
                        # Fallback to basic completion without detailed metrics
                        logger.warning(f"No SDK executor results found for run {run_id}, using basic completion")
                        await cls._update_session_status(session_id, "completed", {
                            "completed_at": datetime.utcnow().isoformat(),
                            "last_updated": datetime.utcnow().isoformat(),
                            "elapsed_seconds": int(elapsed),
                            "success": True
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
    def _store_sdk_executor_results(cls, session_id: str, execution_results: dict):
        """Store SDK executor results in session metadata for real-time access."""
        try:
            session_uuid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
            session = session_repo.get_session(session_uuid)
            if session:
                metadata = session.metadata or {}
                metadata["execution_results"] = execution_results
                metadata["last_updated"] = datetime.utcnow().isoformat()
                session.metadata = metadata
                session_repo.update_session(session)
                logger.info(f"Stored SDK executor results in session {session_id}")
        except Exception as e:
            logger.error(f"Failed to store SDK executor results: {e}")
    
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
            # Get current session (convert string to UUID)
            session_uuid = uuid.UUID(session_id) if isinstance(session_id, str) else session_id
            session = session_repo.get_session(session_uuid)
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