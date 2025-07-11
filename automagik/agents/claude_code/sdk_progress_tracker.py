"""SDK Progress Tracker for Claude Code execution.

This module handles real-time progress tracking and metrics collection.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from uuid import uuid4

logger = logging.getLogger(__name__)


class SDKProgressTracker:
    """Tracks execution progress and metrics for Claude Code workflows."""
    
    def __init__(self, run_id: str, workflow_name: str, max_turns: Optional[int] = None):
        self.run_id = run_id
        self.workflow_name = workflow_name
        self.max_turns = max_turns
        
        # Progress metrics
        self.turn_count = 0
        self.token_count = 0
        self.last_token_count = 0
        self.start_time = datetime.utcnow()
        self.last_update_time = datetime.utcnow()
        
        # Session tracking
        self.session_id = None
        self.actual_claude_session_id = None
        
        # Tracing context
        self.trace_id = None
        self.parent_span_id = None
        self.langwatch_provider = None
    
    def set_tracing_context(self, trace_id: str, parent_span_id: str, tracing_manager: Any) -> None:
        """Set tracing context for observability."""
        self.trace_id = trace_id
        self.parent_span_id = parent_span_id
        
        # Get LangWatch provider if available
        if tracing_manager and tracing_manager.observability:
            for provider in tracing_manager.observability.providers.values():
                if hasattr(provider, 'log_metadata'):
                    self.langwatch_provider = provider
                    break
    
    def track_turn(self, message_type: str) -> None:
        """Track a conversation turn."""
        if message_type == 'AssistantMessage':
            self.turn_count += 1
            logger.info(f"🔄 Turn {self.turn_count} - AssistantMessage received")
            
            # Log turn span if tracing is enabled
            if self.langwatch_provider and self.trace_id:
                self._log_turn_span()
    
    def update_tokens(self, usage_data: Dict[str, int]) -> None:
        """Update token count from usage data."""
        if 'total_tokens' in usage_data:
            self.token_count = usage_data['total_tokens']
            logger.info(f"📊 Total tokens: {self.token_count}")
    
    def set_session_id(self, session_id: str) -> None:
        """Set the actual Claude session ID."""
        self.actual_claude_session_id = session_id
        logger.info(f"SDK Executor: Captured REAL Claude session ID: {session_id}")
    
    def get_progress_metadata(self) -> Dict[str, Any]:
        """Get current progress metadata."""
        current_time = datetime.utcnow()
        duration_seconds = (current_time - self.start_time).total_seconds()
        
        metadata = {
            "current_turns": self.turn_count,
            "max_turns": self.max_turns,
            "total_tokens": self.token_count,
            "last_activity": current_time.isoformat(),
            "run_status": "running",
            "duration_seconds": duration_seconds,
            "workflow_name": self.workflow_name,
            "run_id": self.run_id
        }
        
        if self.actual_claude_session_id:
            metadata["claude_session_id"] = self.actual_claude_session_id
        
        return metadata
    
    async def update_database_progress(self) -> bool:
        """Update progress in database."""
        try:
            from ...db.models import WorkflowRunUpdate
            from ...db.repository.workflow_run import update_workflow_run_by_run_id
            
            # Build metadata with current progress
            progress_metadata = self.get_progress_metadata()
            
            # Update database with real-time progress
            progress_update = WorkflowRunUpdate(
                total_tokens=self.token_count,
                metadata=progress_metadata
            )
            
            update_success = update_workflow_run_by_run_id(self.run_id, progress_update)
            if update_success:
                logger.info(f"📈 Updated progress - Turns: {self.turn_count}, Tokens: {self.token_count}")
                self.last_update_time = datetime.utcnow()
                return True
            else:
                logger.warning("Failed to update progress in database")
                return False
                
        except Exception as progress_error:
            logger.error(f"Real-time progress update failed: {progress_error}")
            return False
    
    def _log_turn_span(self) -> None:
        """Log turn span for tracing."""
        turn_span_id = str(uuid4())
        
        # Log span start
        self.langwatch_provider.log_metadata({
            "trace_id": self.trace_id,
            "span_id": turn_span_id,
            "parent_span_id": self.parent_span_id,
            "event_type": "span_start",
            "name": f"claude_code.message.turn_{self.turn_count}",
            "attributes": {
                "turn_number": self.turn_count,
                "workflow_name": self.workflow_name,
                "message_type": "assistant"
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Log span end with token usage
        tokens_used = self.token_count - self.last_token_count
        self.langwatch_provider.log_metadata({
            "trace_id": self.trace_id,
            "span_id": turn_span_id,
            "parent_span_id": self.parent_span_id,
            "event_type": "span_end",
            "name": f"claude_code.message.turn_{self.turn_count}",
            "attributes": {
                "tokens_used": tokens_used
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
        self.last_token_count = self.token_count
    
    def should_update_progress(self, message_type: str) -> bool:
        """Check if progress should be updated for this message type."""
        return message_type in ['AssistantMessage', 'ResultMessage']
    
    def get_final_metrics(self) -> Dict[str, Any]:
        """Get final execution metrics."""
        end_time = datetime.utcnow()
        duration_seconds = (end_time - self.start_time).total_seconds()
        
        return {
            "total_turns": self.turn_count,
            "total_tokens": self.token_count,
            "duration_seconds": duration_seconds,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "workflow_name": self.workflow_name,
            "run_id": self.run_id,
            "claude_session_id": self.actual_claude_session_id
        }