"""Progress tracking for Claude Code workflows.

This module provides intelligent progress tracking and phase detection
for Claude workflow execution.
"""

import logging
from typing import Dict, List, Any, Optional, Set
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ProgressTracker:
    """Tracks workflow progress and detects execution phases."""
    
    def __init__(self):
        """Initialize progress tracker with optimized phase detection patterns."""
        # Use sets for O(1) lookups instead of lists with O(n) searches
        self.phase_patterns = {
            "initialization": {"TodoWrite", "initial", "setup"},
            "planning": {"TodoWrite", "TodoRead", "plan", "organize"},
            "analysis": {"LS", "Glob", "Read", "Grep", "search", "analyze"},
            "implementation": {"Write", "Edit", "MultiEdit", "create", "implement"},
            "testing": {"Bash", "test", "validate", "check"},
            "execution": {"Bash", "run", "execute"},
            "review": {"Read", "review", "check", "validate"},
            "completion": {"complete", "finish", "done", "summary"}
        }
        
        # Pre-compute tool categories for faster lookups
        self.edit_tools: Set[str] = {"Write", "Edit", "MultiEdit"}
        self.read_tools: Set[str] = {"Read", "LS", "Glob", "Grep"}
        self.tool_patterns: Set[str] = {
            "TodoWrite", "TodoRead", "LS", "Read", "Write", "Edit",
            "MultiEdit", "Bash", "Glob", "Grep", "Task"
        }
        
        # Phase order for efficient progression calculation
        self.phase_order = [
            "initialization", "planning", "analysis", "implementation",
            "testing", "review", "completion"
        ]
        
        # Cache for phase detection results
        self._phase_cache: Dict[str, str] = {}
    
    def calculate_progress(
        self,
        metadata: Dict[str, Any],
        log_entries: List[Dict],
        messages: List[Any]
    ) -> Dict[str, Any]:
        """Calculate comprehensive workflow progress.
        
        Args:
            metadata: Session metadata
            log_entries: Raw log entries
            messages: Assistant messages
            
        Returns:
            Progress information dictionary
        """
        try:
            # Get turn counts from metadata (prioritize current_turns for real-time tracking)
            current_turns = metadata.get("current_turns", metadata.get("total_turns", 0))
            
            # If metadata turns are 0, count from log entries for real-time tracking
            if current_turns == 0 and log_entries:
                assistant_messages = sum(1 for entry in log_entries 
                                       if entry.get("event_type") == "claude_stream_assistant")
                current_turns = max(current_turns, assistant_messages)
            max_turns = metadata.get("max_turns")  # No default, unlimited if not specified
            
            # Execution status - check completion indicators
            run_status = metadata.get("run_status", "").lower()
            completed_at = metadata.get("completed_at")
            is_running = run_status == "running" and not completed_at
            
            # Basic progress metrics
            # If workflow is completed, always show 100%
            if run_status in ["completed", "failed"] or completed_at:
                completion_percentage = 100.0
            else:
                completion_percentage = min(100.0, (current_turns / max_turns) * 100) if max_turns and max_turns > 0 else 0
            
            # Phase detection based on metadata and log entries
            current_phase = self._detect_current_phase(log_entries, current_turns, metadata)
            phases_completed = self._get_completed_phases(log_entries, current_phase, metadata)
            
            # Time estimation
            estimated_completion = self._estimate_completion(metadata, current_turns, max_turns)
            
            return {
                "turns": current_turns,
                "max_turns": max_turns,
                "completion_percentage": round(completion_percentage, 1),
                "current_phase": current_phase,
                "phases_completed": phases_completed,
                "is_running": is_running,
                "estimated_completion": estimated_completion
            }
            
        except Exception as e:
            logger.error(f"Error calculating progress: {e}")
            return {
                "turns": 0,
                "max_turns": None,  # Unlimited by default
                "completion_percentage": 0.0,
                "current_phase": "unknown",
                "phases_completed": [],
                "is_running": False,
                "estimated_completion": None
            }
    
    def _detect_current_phase(
        self,
        log_entries: List[Dict],
        current_turns: int,
        metadata: Dict[str, Any] = None
    ) -> str:
        """Detect current workflow phase based on recent activity.
        
        Args:
            log_entries: Recent log entries
            current_turns: Current turn count
            metadata: Session metadata with tool usage
            
        Returns:
            Current phase name
        """
        # Check if workflow is completed
        if metadata and metadata.get("completed_at"):
            return "completed"
        
        # Early phase detection based on turn count
        if current_turns <= 2:
            return "initialization"
        
        # Use metadata tools for more accurate phase detection
        if metadata:
            tools_used = metadata.get("tools_used_so_far", [])
            if tools_used:
                return self._phase_from_tools(tools_used)
        
        # Fallback to log analysis
        recent_tools = self._get_recent_tools(log_entries[-10:] if log_entries else [])
        recent_content = self._get_recent_content(log_entries[-10:] if log_entries else [])
        
        # Phase detection based on tool patterns - use set intersections for efficiency
        phase_scores = {}
        recent_tools_set = set(recent_tools)
        
        for phase, patterns in self.phase_patterns.items():
            score = 0
            
            # Tool-based scoring - O(1) set intersection instead of nested loops
            tool_matches = recent_tools_set & patterns
            score += len(tool_matches) * 2
            
            # Content-based scoring - only if we haven't already found strong matches
            if score == 0:
                recent_text = " ".join(recent_content).lower()
                recent_words = set(recent_text.split())
                pattern_matches = recent_words & patterns
                score += len(pattern_matches)
            
            phase_scores[phase] = score
        
        # Return phase with highest score
        if phase_scores:
            detected_phase = max(phase_scores, key=phase_scores.get)
            if phase_scores[detected_phase] > 0:
                return detected_phase
        
        # Fallback based on turn progression
        return self._get_default_phase_by_turns(current_turns)
    
    def _phase_from_tools(self, tools_used: List[str]) -> str:
        """Determine workflow phase based on tools used.
        
        Args:
            tools_used: List of tools used in the workflow
            
        Returns:
            Phase name based on tool patterns
        """
        # Convert to set for faster lookups
        tools_set = set(tools_used)
        
        # Score phases based on tools used - use set intersections
        phase_scores = {}
        for phase, patterns in self.phase_patterns.items():
            matches = tools_set & patterns
            phase_scores[phase] = len(matches)
        
        # Return phase with highest score
        if phase_scores:
            detected_phase = max(phase_scores, key=phase_scores.get)
            if phase_scores[detected_phase] > 0:
                return detected_phase
        
        # Fallback to implementation if any editing tools used
        if tools_set & self.edit_tools:
            return "implementation"
        
        # Fallback to analysis if any reading tools used
        if tools_set & self.read_tools:
            return "analysis"
        
        return "execution"
    
    def _get_recent_tools(self, log_entries: List[Dict]) -> List[str]:
        """Extract recent tool usage from log entries.
        
        Args:
            log_entries: Log entries to analyze
            
        Returns:
            List of recently used tools
        """
        tools = []
        
        for entry in log_entries:
            if isinstance(entry, dict):
                data = entry.get('data', {})
                
                if isinstance(data, dict):
                    # Direct tool name
                    tool_name = data.get('tool_name')
                    if tool_name:
                        tools.append(tool_name)
                    
                    # Tool usage in content - use pre-computed pattern set
                    content = str(data.get('content', ''))
                    if content:  # Only process non-empty content
                        # Use set intersection to find matching tools efficiently
                        content_words = set(content.split())
                        matching_tools = content_words & self.tool_patterns
                        tools.extend(matching_tools)
        
        return tools
    
    def _get_recent_content(self, log_entries: List[Dict]) -> List[str]:
        """Extract recent content from log entries.
        
        Args:
            log_entries: Log entries to analyze
            
        Returns:
            List of content strings
        """
        content_list = []
        
        for entry in log_entries:
            if isinstance(entry, dict):
                data = entry.get('data', {})
                
                if isinstance(data, dict):
                    content = data.get('content', '')
                    if isinstance(content, str) and content.strip():
                        content_list.append(content.strip())
        
        return content_list
    
    def _get_completed_phases(
        self,
        log_entries: List[Dict],
        current_phase: str,
        metadata: Dict[str, Any] = None
    ) -> List[str]:
        """Determine which phases have been completed.
        
        Args:
            log_entries: All log entries
            current_phase: Current active phase
            
        Returns:
            List of completed phase names
        """
        # Find current phase index using pre-computed phase order
        try:
            current_index = self.phase_order.index(current_phase)
            return self.phase_order[:current_index]
        except ValueError:
            # Current phase not in standard order
            return []
    
    def _get_default_phase_by_turns(self, turns: int) -> str:
        """Get default phase based on turn count.
        
        Args:
            turns: Current turn count
            
        Returns:
            Default phase name
        """
        if turns <= 3:
            return "initialization"
        elif turns <= 8:
            return "planning"
        elif turns <= 15:
            return "analysis"
        elif turns <= 25:
            return "implementation"
        else:
            return "execution"
    
    def _estimate_completion(
        self,
        metadata: Dict[str, Any],
        current_turns: int,
        max_turns: int
    ) -> Optional[str]:
        """Estimate workflow completion time.
        
        Args:
            metadata: Session metadata
            current_turns: Current turn count
            max_turns: Maximum turns allowed
            
        Returns:
            Estimated completion time string
        """
        try:
            # Check if we have start time
            started_at = metadata.get("started_at")
            if not started_at:
                return None
            
            # Parse start time
            if isinstance(started_at, str):
                start_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
            else:
                start_time = started_at
            
            # Calculate elapsed time
            now = datetime.now(start_time.tzinfo) if start_time.tzinfo else datetime.now()
            elapsed = now - start_time
            
            # Estimate based on current progress
            if current_turns > 0:
                avg_time_per_turn = elapsed.total_seconds() / current_turns
                remaining_turns = max(0, max_turns - current_turns)
                
                if remaining_turns > 0:
                    estimated_remaining = timedelta(seconds=avg_time_per_turn * remaining_turns)
                    completion_time = now + estimated_remaining
                    
                    # Format as relative time
                    total_remaining_minutes = estimated_remaining.total_seconds() / 60
                    
                    if total_remaining_minutes < 1:
                        return "< 1 minute"
                    elif total_remaining_minutes < 60:
                        return f"~{int(total_remaining_minutes)} minutes"
                    else:
                        hours = int(total_remaining_minutes / 60)
                        minutes = int(total_remaining_minutes % 60)
                        return f"~{hours}h {minutes}m"
            
            return None
            
        except Exception as e:
            logger.debug(f"Error estimating completion: {e}")
            return None
    
    def get_phase_summary(
        self,
        log_entries: List[Dict],
        current_phase: str
    ) -> Dict[str, Any]:
        """Get summary of workflow phases and transitions.
        
        Args:
            log_entries: All log entries
            current_phase: Current active phase
            
        Returns:
            Phase summary with timing and activities
        """
        try:
            phases_detected = []
            current_phase_info = None
            
            # Analyze phases throughout execution
            turn_phases = self._analyze_phase_progression(log_entries)
            
            # Group consecutive phases
            phase_groups = []
            current_group = None
            
            for turn, phase in turn_phases:
                if not current_group or current_group["phase"] != phase:
                    if current_group:
                        phase_groups.append(current_group)
                    
                    current_group = {
                        "phase": phase,
                        "start_turn": turn,
                        "end_turn": turn,
                        "tools_used": [],
                        "duration_estimate": None
                    }
                else:
                    current_group["end_turn"] = turn
            
            if current_group:
                phase_groups.append(current_group)
            
            return {
                "phases_detected": [group["phase"] for group in phase_groups],
                "current_phase": current_phase,
                "phase_breakdown": phase_groups,
                "total_phases": len(phase_groups)
            }
            
        except Exception as e:
            logger.error(f"Error generating phase summary: {e}")
            return {
                "phases_detected": [current_phase],
                "current_phase": current_phase,
                "phase_breakdown": [],
                "total_phases": 1
            }
    
    def _analyze_phase_progression(
        self,
        log_entries: List[Dict]
    ) -> List[tuple]:
        """Analyze phase progression throughout execution.
        
        Args:
            log_entries: All log entries
            
        Returns:
            List of (turn, phase) tuples
        """
        phases = []
        
        # Group log entries by turns (approximate)
        entries_per_turn = max(1, len(log_entries) // 30)  # Assume ~30 turns max
        
        for i in range(0, len(log_entries), entries_per_turn):
            turn_entries = log_entries[i:i + entries_per_turn]
            turn_number = (i // entries_per_turn) + 1
            
            phase = self._detect_current_phase(turn_entries, turn_number)
            phases.append((turn_number, phase))
        
        return phases