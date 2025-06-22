"""
SDK Stream Processor for extracting rich real-time data from Claude Code SDK.

This module processes the streaming messages from the claude-code-sdk to extract
detailed execution metrics, progress tracking, and status information that
feeds the status endpoint with rich details.
"""

import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

# Add local SDK to path if available
local_sdk_path = Path(__file__).parent.parent.parent / "vendors" / "claude-code-sdk" / "src"
if local_sdk_path.exists():
    sys.path.insert(0, str(local_sdk_path))

from claude_code_sdk import (
    AssistantMessage, 
    UserMessage, 
    SystemMessage, 
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock
)

logger = logging.getLogger(__name__)


@dataclass
class SDKExecutionMetrics:
    """Comprehensive metrics extracted from SDK streaming data."""
    
    # Basic execution info
    session_id: Optional[str] = None
    total_turns: int = 0
    total_cost_usd: float = 0.0
    total_tokens: int = 0
    duration_ms: int = 0
    duration_api_ms: int = 0
    
    # Tool usage tracking
    tool_calls: int = 0
    tool_names_used: List[str] = field(default_factory=list)
    tool_usage_history: List[Dict[str, Any]] = field(default_factory=list)
    
    # Content tracking
    assistant_responses: List[str] = field(default_factory=list)
    user_messages: List[str] = field(default_factory=list)
    system_events: List[Dict[str, Any]] = field(default_factory=list)
    
    # Status tracking
    is_running: bool = False
    is_success: bool = False
    completion_type: str = "running"
    final_result: Optional[str] = None
    error_message: Optional[str] = None
    
    # Real-time progress
    current_phase: str = "initializing"
    phases_completed: List[str] = field(default_factory=list)
    last_activity: Optional[datetime] = None
    
    # Model and MCP info
    model: Optional[str] = None
    mcp_servers: List[str] = field(default_factory=list)


class SDKStreamProcessor:
    """Processes Claude Code SDK streaming messages for real-time metrics."""
    
    def __init__(self):
        """Initialize the stream processor."""
        self.metrics = SDKExecutionMetrics()
        self.start_time = time.time()
        self.current_turn = 0
        self.expecting_tool_result = False
        self.current_tool_use_id = None
        
    def process_message(self, message) -> Dict[str, Any]:
        """
        Process a streaming message from the SDK and update metrics.
        
        Args:
            message: Message object from claude-code-sdk
            
        Returns:
            Dict containing the processed event data
        """
        self.metrics.last_activity = datetime.utcnow()
        
        if isinstance(message, UserMessage):
            return self._process_user_message(message)
        elif isinstance(message, AssistantMessage):
            return self._process_assistant_message(message)
        elif isinstance(message, SystemMessage):
            return self._process_system_message(message)
        elif isinstance(message, ResultMessage):
            return self._process_result_message(message)
        else:
            logger.debug(f"Unknown message type: {type(message)}")
            return {"event_type": "unknown", "data": str(message)}
    
    def _process_user_message(self, message: UserMessage) -> Dict[str, Any]:
        """Process user message."""
        self.metrics.user_messages.append(message.content)
        
        return {
            "event_type": "user_message",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "content": message.content,
                "message_count": len(self.metrics.user_messages)
            }
        }
    
    def _process_assistant_message(self, message: AssistantMessage) -> Dict[str, Any]:
        """Process assistant message with content blocks."""
        events = []
        
        for block in message.content:
            if isinstance(block, TextBlock):
                # Track assistant text response
                self.metrics.assistant_responses.append(block.text)
                
                # Update progress based on content
                self._update_phase_from_content(block.text)
                
                events.append({
                    "event_type": "assistant_text",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "text": block.text,
                        "response_count": len(self.metrics.assistant_responses),
                        "current_phase": self.metrics.current_phase
                    }
                })
                
            elif isinstance(block, ToolUseBlock):
                # Track tool usage
                self.metrics.tool_calls += 1
                if block.name not in self.metrics.tool_names_used:
                    self.metrics.tool_names_used.append(block.name)
                
                tool_event = {
                    "tool_id": block.id,
                    "tool_name": block.name,
                    "input": block.input,
                    "timestamp": datetime.utcnow().isoformat()
                }
                self.metrics.tool_usage_history.append(tool_event)
                
                # Extract phases from TodoWrite tool usage
                if block.name == "TodoWrite":
                    self._extract_phases_from_todowrite(block.input)
                
                # Update phase for tool usage
                self.metrics.current_phase = f"using_{block.name.lower()}_tool"
                
                events.append({
                    "event_type": "tool_use",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "tool_id": block.id,
                        "tool_name": block.name,
                        "input": block.input,
                        "tool_calls_total": self.metrics.tool_calls,
                        "unique_tools": len(self.metrics.tool_names_used)
                    }
                })
                
                self.expecting_tool_result = True
                self.current_tool_use_id = block.id
                
            elif isinstance(block, ToolResultBlock):
                # Track tool result
                events.append({
                    "event_type": "tool_result",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "tool_use_id": block.tool_use_id,
                        "content": block.content,
                        "is_error": block.is_error,
                        "success": not block.is_error
                    }
                })
                
                self.expecting_tool_result = False
                self.current_tool_use_id = None
                
                # Update phase after tool completion
                if not block.is_error:
                    self.metrics.current_phase = "processing_tool_result"
                else:
                    self.metrics.current_phase = "handling_tool_error"
        
        # If multiple events, return the most significant one
        if events:
            return events[-1]  # Return the last (most recent) event
        
        return {
            "event_type": "assistant_message",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"content_blocks": len(message.content)}
        }
    
    def _process_system_message(self, message: SystemMessage) -> Dict[str, Any]:
        """Process system message."""
        system_event = {
            "subtype": message.subtype,
            "data": message.data,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.metrics.system_events.append(system_event)
        
        # Update metrics based on system message
        if message.subtype == "session_start":
            self.metrics.session_id = message.data.get("session_id")
            self.metrics.is_running = True
            self.metrics.current_phase = "session_started"
        elif message.subtype == "turn_start":
            self.current_turn += 1
            self.metrics.total_turns = self.current_turn
            self.metrics.current_phase = f"turn_{self.current_turn}"
        
        return {
            "event_type": "system_message",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "subtype": message.subtype,
                "system_data": message.data,
                "current_turn": self.current_turn
            }
        }
    
    def _process_result_message(self, message: ResultMessage) -> Dict[str, Any]:
        """Process result message with final metrics."""
        
        # Update final metrics
        self.metrics.total_cost_usd = message.total_cost_usd or 0.0
        self.metrics.duration_ms = message.duration_ms
        self.metrics.duration_api_ms = message.duration_api_ms
        self.metrics.total_turns = message.num_turns
        self.metrics.session_id = message.session_id
        self.metrics.final_result = message.result
        self.metrics.is_success = not message.is_error
        self.metrics.is_running = False
        
        # Extract token usage if available
        if message.usage:
            self.metrics.total_tokens = message.usage.get("total_tokens", 0)
        
        # Determine completion type and phase
        if message.is_error:
            self.metrics.completion_type = "failed"
            self.metrics.current_phase = "failed"
            self.metrics.error_message = message.result
        else:
            if message.subtype == "max_turns_reached":
                self.metrics.completion_type = "max_turns_reached"
            else:
                self.metrics.completion_type = "completed_successfully"
            self.metrics.current_phase = "completed"
        
        return {
            "event_type": "execution_complete",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {
                "success": self.metrics.is_success,
                "completion_type": self.metrics.completion_type,
                "total_cost_usd": self.metrics.total_cost_usd,
                "duration_ms": self.metrics.duration_ms,
                "total_turns": self.metrics.total_turns,
                "session_id": self.metrics.session_id,
                "result": self.metrics.final_result,
                "is_error": message.is_error
            }
        }
    
    def _update_phase_from_content(self, text: str):
        """Update execution phase based on assistant text content."""
        text_lower = text.lower()
        
        # Common phase detection patterns
        if any(word in text_lower for word in ["analyzing", "examining", "looking at"]):
            self.metrics.current_phase = "analysis"
            if "analysis" not in self.metrics.phases_completed:
                self.metrics.phases_completed.append("analysis")
                
        elif any(word in text_lower for word in ["planning", "will", "going to", "approach"]):
            self.metrics.current_phase = "planning"
            if "planning" not in self.metrics.phases_completed:
                self.metrics.phases_completed.append("planning")
                
        elif any(word in text_lower for word in ["implementing", "creating", "writing", "coding"]):
            self.metrics.current_phase = "implementation"
            if "implementation" not in self.metrics.phases_completed:
                self.metrics.phases_completed.append("implementation")
                
        elif any(word in text_lower for word in ["testing", "running test", "checking"]):
            self.metrics.current_phase = "testing"
            if "testing" not in self.metrics.phases_completed:
                self.metrics.phases_completed.append("testing")
                
        elif any(word in text_lower for word in ["completed", "finished", "done"]):
            self.metrics.current_phase = "completion"
            if "completion" not in self.metrics.phases_completed:
                self.metrics.phases_completed.append("completion")
        
        # Track phase progress (percentage calculation removed per user request)
    
    def _extract_phases_from_todowrite(self, tool_input: Dict[str, Any]):
        """Extract phase information from TodoWrite tool usage."""
        if not isinstance(tool_input, dict):
            return
            
        todos = tool_input.get("todos", [])
        if not isinstance(todos, list):
            return
        
        completed_phases = []
        current_phase = None
        
        for todo in todos:
            if not isinstance(todo, dict):
                continue
                
            content = todo.get("content", "")
            status = todo.get("status", "")
            
            if status == "completed" and content:
                # Clean and format phase name
                phase_name = content.strip()
                if phase_name and phase_name not in completed_phases:
                    completed_phases.append(phase_name)
            elif status == "in_progress" and content:
                # Set current active phase
                current_phase = content.strip()
        
        # Update metrics with extracted phase information
        if completed_phases:
            # Merge with existing phases, preserving order and avoiding duplicates
            for phase in completed_phases:
                if phase not in self.metrics.phases_completed:
                    self.metrics.phases_completed.append(phase)
        
        if current_phase:
            self.metrics.current_phase = current_phase
    
    def get_current_metrics(self) -> SDKExecutionMetrics:
        """Get current execution metrics."""
        return self.metrics
    
    def get_status_data(self) -> Dict[str, Any]:
        """Get formatted status data for the status endpoint."""
        elapsed_seconds = time.time() - self.start_time
        
        return {
            "run_id": "sdk_execution",  # This should be set externally
            "status": "completed" if not self.metrics.is_running else ("running" if self.metrics.total_turns > 0 else "pending"),
            "workflow_name": "unknown",  # This should be set externally
            "started_at": datetime.fromtimestamp(self.start_time).isoformat(),
            "completed_at": self.metrics.last_activity.isoformat() if not self.metrics.is_running and self.metrics.last_activity else None,
            "execution_time_seconds": elapsed_seconds if not self.metrics.is_running else None,
            
            "progress": {
                "turns": self.metrics.total_turns,
                "max_turns": None,  # Should be set externally
                "current_phase": self.metrics.current_phase,
                "phases_completed": self.metrics.phases_completed,
                "is_running": self.metrics.is_running
            },
            
            "metrics": {
                "cost_usd": self.metrics.total_cost_usd,
                "tokens": {
                    "total": self.metrics.total_tokens,
                    "input": 0,  # SDK doesn't provide breakdown yet
                    "output": 0,
                    "cache_created": 0,
                    "cache_read": 0,
                    "cache_efficiency": 0.0
                },
                "tools_used": self.metrics.tool_names_used,
                "tool_names_used": self.metrics.tool_names_used,  # Keep for backwards compatibility
                "api_duration_ms": self.metrics.duration_api_ms,
                "performance_score": self._calculate_performance_score()
            },
            
            "result": {
                "success": self.metrics.is_success,
                "completion_type": self.metrics.completion_type,
                "message": self._get_status_message(),
                "final_output": self.metrics.final_result,
                "files_created": [],  # TODO: Extract from tool usage
                "git_commits": []  # TODO: Extract from tool usage
            }
        }
    
    def _calculate_performance_score(self) -> float:
        """Calculate a performance score based on execution metrics."""
        score = 85.0  # Base score
        
        # Adjust based on tool usage efficiency
        if self.metrics.tool_calls > 0 and self.metrics.total_turns > 0:
            tools_per_turn = self.metrics.tool_calls / self.metrics.total_turns
            if tools_per_turn > 3:  # Too many tools per turn
                score -= 10
            elif tools_per_turn < 0.5:  # Too few tools (might be inefficient)
                score -= 5
        
        # Adjust based on completion
        if self.metrics.is_success:
            score += 5
        elif self.metrics.error_message:
            score -= 15
        
        return max(0.0, min(100.0, score))
    
    def _get_status_message(self) -> str:
        """Get a user-friendly status message."""
        if self.metrics.error_message:
            return f"❌ Execution failed: {self.metrics.error_message}"
        elif not self.metrics.is_running and self.metrics.is_success:
            return "✅ Workflow completed successfully"
        elif not self.metrics.is_running and self.metrics.completion_type == "max_turns_reached":
            return "⏰ Reached maximum turns - workflow stopped at turn limit"
        elif self.metrics.is_running:
            return f"🔄 Running - Turn {self.metrics.total_turns}, {len(self.metrics.tool_names_used)} tools used"
        else:
            return "⚠️ Workflow status unclear - check logs for details"